"""Tests for orchestrator routing — no LLM calls, no graph compile."""
from unittest.mock import patch

# Stub out heavy imports before importing orchestrator module.
with patch("anthropic.Anthropic"):
    from agents import orchestrator


def test_runnable_tasks_no_deps():
    plan = {
        "tasks": [
            {"id": "t1", "agent": "coder", "task": "x", "depends_on": []},
            {"id": "t2", "agent": "tester", "task": "y", "depends_on": []},
        ]
    }
    out = orchestrator.runnable_tasks(plan, set())
    ids = {t["id"] for t in out}
    assert ids == {"t1", "t2"}


def test_runnable_tasks_with_deps():
    plan = {
        "tasks": [
            {"id": "t1", "agent": "coder", "task": "x", "depends_on": []},
            {"id": "t2", "agent": "tester", "task": "y", "depends_on": ["t1"]},
        ]
    }
    # First wave: only t1
    assert [t["id"] for t in orchestrator.runnable_tasks(plan, set())] == ["t1"]
    # After t1 completes: t2 unblocked
    assert [t["id"] for t in orchestrator.runnable_tasks(plan, {"t1"})] == ["t2"]
    # All done
    assert orchestrator.runnable_tasks(plan, {"t1", "t2"}) == []


def test_runnable_tasks_diamond():
    plan = {
        "tasks": [
            {"id": "a", "agent": "coder", "task": "", "depends_on": []},
            {"id": "b", "agent": "coder", "task": "", "depends_on": ["a"]},
            {"id": "c", "agent": "coder", "task": "", "depends_on": ["a"]},
            {"id": "d", "agent": "tester", "task": "", "depends_on": ["b", "c"]},
        ]
    }
    assert [t["id"] for t in orchestrator.runnable_tasks(plan, set())] == ["a"]
    wave2 = [t["id"] for t in orchestrator.runnable_tasks(plan, {"a"})]
    assert set(wave2) == {"b", "c"}
    # d blocked until both b and c done
    assert [t["id"] for t in orchestrator.runnable_tasks(plan, {"a", "b"})] == ["c"]
    assert [t["id"] for t in orchestrator.runnable_tasks(plan, {"a", "b", "c"})] == ["d"]


def test_dispatch_clarification_routes_to_end():
    state = {"_plan": {"needs_clarification": True}, "_completed_tasks": []}
    from langgraph.graph import END
    assert orchestrator.dispatch(state) == END


def test_dispatch_no_tasks_routes_to_end():
    from langgraph.graph import END
    state = {"_plan": {"tasks": []}, "_completed_tasks": []}
    assert orchestrator.dispatch(state) == END


def test_dispatch_all_done_routes_to_synthesize():
    plan = {"tasks": [{"id": "t1", "agent": "coder", "task": "x", "depends_on": []}]}
    state = {"_plan": plan, "_completed_tasks": ["t1"]}
    assert orchestrator.dispatch(state) == "synthesize"


def test_dispatch_dispatches_wave():
    plan = {
        "tasks": [
            {"id": "t1", "agent": "coder", "task": "code", "depends_on": []},
            {"id": "t2", "agent": "tester", "task": "test", "depends_on": ["t1"]},
        ]
    }
    state = {"_plan": plan, "_completed_tasks": []}
    sends = orchestrator.dispatch(state)
    assert isinstance(sends, list)
    assert len(sends) == 1
    assert sends[0].node == "coder_node"
    assert sends[0].arg["_current_task_id"] == "t1"
    assert sends[0].arg["_current_task"] == "code"


def test_dispatch_deadlock_routes_to_synthesize():
    """Cyclic deps — no runnable tasks but not all done."""
    plan = {
        "tasks": [
            {"id": "t1", "agent": "coder", "task": "x", "depends_on": ["t2"]},
            {"id": "t2", "agent": "coder", "task": "y", "depends_on": ["t1"]},
        ]
    }
    state = {"_plan": plan, "_completed_tasks": []}
    assert orchestrator.dispatch(state) == "synthesize"
