import operator
from typing import TypedDict, Annotated


class TaskResult(TypedDict):
    agent: str
    summary: str
    success: bool


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    phone_number: str

    github_token: str | None
    active_repo: str | None
    local_path: str | None
    working_branch: str | None

    current_task: str | None
    task_results: Annotated[list[TaskResult], operator.add]

    _plan: dict | None
    _current_task: str | None
    _current_task_id: str | None
    _completed_tasks: Annotated[list[str], operator.add]
