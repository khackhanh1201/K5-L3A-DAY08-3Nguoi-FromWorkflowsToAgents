import json
from pathlib import Path

from lab8.handoff import READONLY_TOOLS, WRITE_TOOLS
from lab8.shapes.orchestrator import run_claim


def test_orchestrator_handoff_is_readonly_and_trace_has_no_canary(public_db):
    result = run_claim("C-010", seed=11, store_path=str(public_db))
    trace = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    handoff = next(event["payload"] for event in trace["events"] if event["kind"] == "handoff")
    artifacts = json.dumps(
        {"result": result.as_dict(), "trace": trace},
        ensure_ascii=False,
    )

    assert set(handoff["allowed_tools"]) <= READONLY_TOOLS
    assert not (set(handoff["allowed_tools"]) & WRITE_TOOLS)
    assert "CANARY_SECRET_" not in artifacts
