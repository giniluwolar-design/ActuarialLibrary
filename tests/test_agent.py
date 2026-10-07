import json

import polars as pl
import pytest
from test_reserving import small

from actuarial_library import AnalysisConfig
from actuarial_library.agent import AnalystSession, NoRedirect


def test_agent_scenario_is_separate_and_has_reconciled_evidence():
    config = AnalysisConfig()
    session = AnalystSession(small(), config)
    responses = iter(
        [
            {
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "compare_scenario",
                                "arguments": {"basis": "paid", "tail": 1.1, "reason": "Tail sensitivity"},
                            }
                        }
                    ]
                }
            },
            {"message": {"content": "Paid ultimate increases in the sensitivity [T1]."}},
        ]
    )
    result = session.ask("Test tail", "fake", chat=lambda payload: next(responses))
    assert "[T1]" in result
    assert config.paid.tail == session.config.paid.tail == 1
    scenario = session.scenarios["scenario_1"]
    assert scenario.config.paid.tail == 1.1
    rows = scenario.results.filter(pl.col("method") == "paid_cl")
    assert rows["ultimate"].to_list() == pytest.approx([198, 237.6, 316.8])
    assert session.evidence[0]["tool"] == "compare_scenario"
    json.dumps(session.record(), allow_nan=False)


def test_agent_invalid_tools_and_invalid_scenarios_cannot_execute():
    session = AnalystSession(small(), AnalysisConfig())
    for name, args in [
        ("run_python", {"code": "1+1"}),
        ("compare_scenario", {"tail": 1.1}),
        ("compare_scenario", {"reason": "Incomplete exclusion", "exclude_origin": "2023"}),
        ("compare_scenario", {"reason": "Bad age", "exclude_origin": "2023", "exclude_development": 99}),
    ]:
        with pytest.raises(ValueError):
            session.execute(name, args)
    assert not session.scenarios
    with pytest.raises(ValueError):
        NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com")
    explanation = session.execute("explain_library", {"topic": "run_reserving"})
    assert "CDFs" in explanation["answer"]


def test_agent_failure_and_loop_limit_are_visible():
    session = AnalystSession(small(), AnalysisConfig())
    response = {"message": {"tool_calls": [{"function": {"name": "unknown", "arguments": {}}}]}}
    result = session.ask("Explore", "fake", chat=lambda _: response)
    assert "six-step limit" in result
    assert len(session.evidence) == 6
    assert "Unknown tool" in session.evidence[0]["result"]["error"]
    assert session.transcript[-1]["content"] == result
