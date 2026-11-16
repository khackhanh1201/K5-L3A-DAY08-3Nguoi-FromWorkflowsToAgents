"""Shape C — an orchestrator delegates scoped, read-only investigation."""

from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import get_claim_view, tool_cost
from lab8.trace import Trace


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


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
) -> RunResult:
    shape = "orchestrator"
    budget = Budget()
    run_id = make_run_id(shape, claim_id, seed)
    trace = Trace(run_id)

    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)
    if not claim.get("found"):
        trace.add("error", {"reason": "unknown_claim"})
        return finish(
            conn,
            shape=shape,
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="unknown_claim",
        )

    if not claim.get("order_id"):
        complete(budget, seed=seed, purpose="orchestrator", prompt="missing_order_id")
        trace.add("decision", {"status": "needs_info"})
        return finish(
            conn,
            shape=shape,
            claim_id=claim_id,
            seed=seed,
            status="needs_info",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="missing_order_id",
        )

    handoff = make_handoff(
        request_id=f"REQ-{claim_id}",
        claim_id=claim_id,
        task="verify_order_and_calculate_compensation",
        facts={},
        allowed_tools=[
            "lookup_order",
            "lookup_policy",
            "lookup_refund_history",
            "compute_compensation",
        ],
    )
    complete(
        budget,
        seed=seed,
        purpose="orchestrator",
        prompt=f"delegate {handoff['task']} for {handoff['claim_id']}",
    )
    trace.add("handoff", safe_dump(handoff))

    investigation = run_readonly_investigators(
        conn,
        budget,
        handoff,
        principal_id=claim["principal_id"],
    )
    tools = investigation["tools"]
    order_view = tools.get("lookup_order") or {}
    trace.add(
        "investigator",
        {
            "visible": bool(order_view.get("visible")),
            "reason": order_view.get("reason"),
        },
    )

    if not order_view.get("visible"):
        complete(
            budget,
            seed=seed,
            purpose="draft",
            prompt=f"escalated:{order_view.get('reason')}",
        )
        return finish(
            conn,
            shape=shape,
            claim_id=claim_id,
            seed=seed,
            status="escalated",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=order_view.get("reason"),
        )

    quote = tools.get("compute_compensation")
    if not isinstance(quote, dict) or "amount_vnd" not in quote:
        trace.add("error", {"reason": "missing_compensation_quote"})
        return finish(
            conn,
            shape=shape,
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="missing_compensation_quote",
        )

    proposal = int(quote["amount_vnd"])
    trace.add("quote", safe_dump(quote))
    complete(
        budget,
        seed=seed,
        purpose="investigator",
        prompt=f"quote={proposal}; reason={quote.get('reason', '')}",
    )
    if proposal <= 0:
        complete(budget, seed=seed, purpose="draft", prompt="denied")
        return finish(
            conn,
            shape=shape,
            claim_id=claim_id,
            seed=seed,
            status="denied",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=quote.get("reason"),
        )

    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        complete(budget, seed=seed, purpose="draft", prompt=status)
        return finish(
            conn,
            shape=shape,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=outcome["reason"],
        )

    complete(budget, seed=seed, purpose="draft", prompt="resolved")
    return finish(
        conn,
        shape=shape,
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )
