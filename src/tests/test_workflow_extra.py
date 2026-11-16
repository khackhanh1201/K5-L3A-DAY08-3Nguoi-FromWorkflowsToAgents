"""Extra checks for Shape A (workflow). Runs in the host gate: `python -m pytest -q`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab8.db import connect
from lab8.schemas import make_run_id
from lab8.shapes import workflow
from tests.conftest import BY_ID, CLAIMS

PUBLIC_IDS = [row["claim_id"] for row in CLAIMS]
SECRET_FIELDS = ("parent_secret", "raw_headers")
# Order-row fields that lookup_order drops and that must never reach a trace.
PII_KEYS = ("phone", "address", "item", "internal_note")


def _trace(result) -> dict:
    return json.loads(Path(result.trace_path).read_text(encoding="utf-8"))


def test_unknown_claim_fails_cleanly_with_trace(public_db):
    result = workflow.run_claim("C-404", seed=11, store_path=str(public_db))
    assert result.status == "failed"
    assert result.error_reason == "unknown_claim"
    assert result.proposal_amount == 0
    assert result.refund_effects == []
    body = _trace(result)
    assert body["run_id"] == result.run_id == make_run_id("workflow", "C-404", 11)
    assert isinstance(body["events"], list) and body["events"]


@pytest.mark.parametrize("claim_id", PUBLIC_IDS)
def test_trace_has_no_secret_ticket_or_pii(public_db, claim_id):
    result = workflow.run_claim(claim_id, seed=11, store_path=str(public_db))
    text = Path(result.trace_path).read_text(encoding="utf-8")
    row = BY_ID[claim_id]
    assert "CANARY_SECRET_" not in text
    assert "CANARY_SECRET_" not in json.dumps(result.as_dict(), ensure_ascii=False)
    assert row["ticket"] not in text, "ticket text is user data and stays out of the trace"
    for key in SECRET_FIELDS + PII_KEYS:
        assert f'"{key}"' not in text


def test_ticket_delay_is_ignored_on_every_seed(public_db):
    # T02: ticket claims 5 days, order row says 2. Workflow must deny on all seeds,
    # including seed 55 where the swarm reference trusts the ticket.
    statuses = set()
    for seed in (11, 22, 33, 44, 55):
        result = workflow.run_claim("C-002", seed=seed, store_path=str(public_db))
        statuses.add((result.status, result.proposal_amount))
    assert statuses == {("denied", 0)}
    conn = connect(public_db)
    try:
        n = conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = 'C-002'").fetchone()["n"]
    finally:
        conn.close()
    assert n == 0


def test_model_never_sees_ticket_text(public_db, monkeypatch):
    prompts: list[str] = []
    real = workflow.complete

    def spy(budget, *, seed, purpose, prompt):
        prompts.append(prompt)
        return real(budget, seed=seed, purpose=purpose, prompt=prompt)

    monkeypatch.setattr(workflow, "complete", spy)
    for claim_id in ("C-001", "C-009", "C-013"):
        workflow.run_claim(claim_id, seed=11, store_path=str(public_db))
    assert prompts, "workflow drafts a reply with one model call per run"
    tickets = [BY_ID[c]["ticket"] for c in ("C-001", "C-009", "C-013")]
    assert not any(t in p for t in tickets for p in prompts)


def test_same_seed_is_deterministic(tmp_path):
    from lab8.db import init_store
    from tests.conftest import WORLD

    outputs = []
    for name in ("a.sqlite", "b.sqlite"):
        store = tmp_path / name
        init_store(store, WORLD, CLAIMS).close()
        r = workflow.run_claim("C-014", seed=33, store_path=str(store))
        outputs.append((r.status, r.proposal_amount, [e["amount_vnd"] for e in r.refund_effects], r.cost_estimate))
    assert outputs[0] == outputs[1]
    assert outputs[0][:3] == ("resolved", 150000, [120000])
