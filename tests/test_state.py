from state import AgentState, TaskResult


def test_task_result_keys():
    r: TaskResult = {"agent": "coder", "summary": "done", "success": True}
    assert r["agent"] == "coder"


def test_agent_state_keys():
    keys = AgentState.__annotations__.keys()
    for required in [
        "messages",
        "phone_number",
        "github_token",
        "active_repo",
        "local_path",
        "task_results",
        "_plan",
        "_current_task",
        "_current_task_id",
        "_completed_tasks",
    ]:
        assert required in keys
