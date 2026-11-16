"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.

Ranh giới code / model trong shape này
--------------------------------------
* Model (MockLLM, gọi qua `complete`) chỉ "suy nghĩ" ở mỗi bước ReAct và soạn
  câu trả lời. Mỗi lần decide() là một model call được tính vào Budget.
* decide() chỉ được chọn tool trong `_ALLOWED_TOOLS` (đều là tool đọc). Nếu nó
  chọn tool khác, `run_react`/`dispatch` ném `ToolRejected` và shape trả `failed`.
* Ticket là dữ liệu: decide() không đọc số ngày trễ hay mã đơn trong ticket.
  Mã đơn lấy từ `get_claim_view`, số liệu đơn từ `lookup_order`, tiền từ
  `compute_compensation` (chỉ dùng policy `is_current` và `effective_date <= as_of`).
* Sau vòng lặp, code của shape (không phải model) gọi `durability.issue_refund`
  với **quote đầy đủ**; host tự kiểm approval, trần theo đơn và idempotency.
* Trace chỉ ghi field đã qua allowlist; không bao giờ ghi ticket, claim row,
  order row thô, principal_id hay parent context.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import ToolRejected, run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.trace import Trace

SHAPE = "single"
MAX_STEPS = 8

# Tool đọc mà agent được phép chọn. Không có issue_refund / append_audit.
_ALLOWED_TOOLS = (
    "get_claim_view",
    "lookup_order",
    "lookup_refund_history",
    "compute_compensation",
)

# Field được phép ghi vào trace cho từng loại kết quả tool.
_ORDER_TRACE_FIELDS = ("order_id", "status", "delay_days", "shipping_fee_vnd", "paid_vnd", "damage_verified", "carrier")
_QUOTE_TRACE_FIELDS = ("amount_vnd", "reason", "clause_ids", "parts")


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id(SHAPE, claim_id, seed))
    trace.add("shape", {"shape": SHAPE, "max_steps": MAX_STEPS, "allowed_tools": list(_ALLOWED_TOOLS)})

    agent = _Agent(claim_id=claim_id, seed=seed, budget=budget, trace=trace)
    try:
        loop = run_react(
            conn,
            budget,
            observation={"claim": {"claim_id": claim_id}},
            decide=agent.decide,
            max_steps=MAX_STEPS,
            worker=True,
        )
    except ToolRejected as exc:
        trace.add("error", {"reason": "tool_rejected", "detail": str(exc)})
        return _done(conn, claim_id, seed, budget, trace, "failed", 0, "tool_rejected")

    final = dict(loop["final"])
    trace.add("react_stop", {"stopped": loop["stopped"], "steps": agent.steps, "final": _safe_final(final)})
    status = final.get("status", "failed")

    if status != "propose":
        # needs_info / escalated / denied / failed (unknown claim, step cap): không ghi ledger.
        _draft(budget, seed, status)
        return _done(conn, claim_id, seed, budget, trace, status, 0, final.get("error_reason"))

    # Agent đề xuất quote > 0. Từ đây chỉ có code chạy, model không chạm vào tiền.
    proposal = int(agent.quote["amount_vnd"])
    trace.add("host_call", {"tool": "durability.issue_refund", "proposed_vnd": proposal})
    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    trace.add("host_result", {"ok": outcome["ok"], "reason": outcome["reason"], "conflict": outcome["conflict"]})
    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        _draft(budget, seed, status)
        return _done(conn, claim_id, seed, budget, trace, status, proposal, outcome["reason"])

    _draft(budget, seed, "resolved")
    return _done(conn, claim_id, seed, budget, trace, "resolved", proposal, None)


class _Agent:
    """Một agent ReAct duy nhất. Giữ bộ nhớ làm việc giữa các bước.

    `run_react` chỉ đưa lại kết quả tool gần nhất, nên agent tự nhớ claim view,
    order view, refund history và quote. Bộ nhớ này nằm trong RAM, không ghi
    nguyên vào trace.
    """

    def __init__(self, *, claim_id: str, seed: int, budget: Budget, trace: Trace) -> None:
        self.claim_id = claim_id
        self.seed = seed
        self.budget = budget
        self.trace = trace
        self.steps = 0
        self.claim: dict[str, Any] | None = None
        self.order_view: dict[str, Any] | None = None
        self.history: dict[str, Any] | None = None
        self.quote: dict[str, Any] | None = None
        self._pending: str | None = None

    # ---- ReAct step -------------------------------------------------------
    def decide(self, seen: dict[str, Any]) -> dict[str, Any]:
        self.steps += 1
        if self._pending is not None:
            self._observe(self._pending, seen.get("last_result") or {})
            self._pending = None

        # "Thought": một model call mỗi bước. Prompt chỉ chứa trạng thái có cấu trúc,
        # không chứa ticket, nên chữ trong ticket không thể điều khiển agent.
        complete(self.budget, seed=self.seed, purpose="react", prompt=self._state_summary())

        action = self._policy()
        if "tool" in action:
            if action["tool"] not in _ALLOWED_TOOLS:
                raise ToolRejected(f"single agent may not call {action['tool']}")
            self._pending = action["tool"]
            self.trace.add("react_step", {"step": self.steps, "action": action["tool"]})
        else:
            self.trace.add("react_step", {"step": self.steps, "action": "final", "status": action["final"]["status"]})
        return action

    def _policy(self) -> dict[str, Any]:
        """Chọn bước tiếp theo chỉ từ dữ liệu có cấu trúc đã đọc."""
        if self.claim is None:
            return {"tool": "get_claim_view", "args": {"claim_id": self.claim_id}}
        if not self.claim.get("found"):
            return {"final": {"status": "failed", "error_reason": "unknown_claim"}}
        order_id = self.claim.get("order_id")
        if not order_id:
            # Không lấy mã đơn từ câu chữ trong ticket.
            return {"final": {"status": "needs_info", "error_reason": "missing_order_id"}}
        principal_id = self.claim["principal_id"]
        if self.order_view is None:
            return {"tool": "lookup_order", "args": {"order_id": order_id, "principal_id": principal_id}}
        if not self.order_view.get("visible"):
            return {"final": {"status": "escalated", "error_reason": self.order_view.get("reason")}}
        if self.history is None:
            return {"tool": "lookup_refund_history", "args": {"order_id": order_id, "principal_id": principal_id}}
        if self.quote is None:
            # Quote từ order row (DB), không từ số ngày trễ khách tự ghi.
            return {"tool": "compute_compensation", "args": {"order": dict(self.order_view["order"])}}
        amount = int(self.quote.get("amount_vnd") or 0)
        if amount <= 0:
            return {"final": {"status": "denied", "error_reason": self.quote.get("reason")}}
        # Vẫn đề xuất quote đầy đủ kể cả khi history cho thấy đơn đã hoàn: host phải
        # là bên từ chối để có audit policy_denied (T13) hoặc chỉ trả phần chênh (T14).
        return {"final": {"status": "propose", "amount_vnd": amount}}

    def _observe(self, tool: str, result: dict[str, Any]) -> None:
        if tool == "get_claim_view":
            self.claim = result
            self.trace.add("observe", {
                "tool": tool,
                "found": bool(result.get("found")),
                "has_order_id": bool(result.get("order_id")),
            })
        elif tool == "lookup_order":
            self.order_view = result
            payload: dict[str, Any] = {"tool": tool, "visible": bool(result.get("visible")), "reason": result.get("reason")}
            if result.get("visible"):
                order = result.get("order") or {}
                payload["order"] = {k: order.get(k) for k in _ORDER_TRACE_FIELDS}
            self.trace.add("observe", payload)
        elif tool == "lookup_refund_history":
            self.history = result
            self.trace.add("observe", {
                "tool": tool,
                "visible": bool(result.get("visible")),
                "refund_count": int(result.get("refund_count") or 0),
                "refunded_vnd": int(result.get("refunded_vnd") or 0),
            })
        elif tool == "compute_compensation":
            self.quote = result
            self.trace.add("observe", {"tool": tool, **{k: result.get(k) for k in _QUOTE_TRACE_FIELDS}})

    def _state_summary(self) -> str:
        parts = [f"claim={self.claim_id}", f"step={self.steps}"]
        if self.claim is not None:
            parts.append(f"claim_found={bool(self.claim.get('found'))}")
            parts.append(f"has_order={bool(self.claim.get('order_id'))}")
        if self.order_view is not None:
            parts.append(f"order_visible={bool(self.order_view.get('visible'))}")
        if self.history is not None:
            parts.append(f"refunded_vnd={int(self.history.get('refunded_vnd') or 0)}")
        if self.quote is not None:
            parts.append(f"quote={int(self.quote.get('amount_vnd') or 0)}")
        return " ".join(parts)


def _draft(budget: Budget, seed: int, status: str) -> None:
    """Model chỉ soạn chữ trả lời; nội dung không ghi vào trace."""
    complete(budget, seed=seed, purpose="draft", prompt=status)


def _safe_final(final: dict[str, Any]) -> dict[str, Any]:
    return {k: final[k] for k in ("status", "error_reason", "amount_vnd") if k in final}


def _done(
    conn: sqlite3.Connection,
    claim_id: str,
    seed: int,
    budget: Budget,
    trace: Trace,
    status: str,
    proposal: int,
    error_reason: str | None,
) -> RunResult:
    return finish(
        conn,
        shape=SHAPE,
        claim_id=claim_id,
        seed=seed,
        status=status,
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=error_reason,
    )
