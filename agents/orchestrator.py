# agents/orchestrator.py
import os
import asyncio
import subprocess
from anthropic import Anthropic
from langgraph.graph import StateGraph, END
from langgraph.constants import Send
from state import AgentState
from memory import checkpointer
from agents import run_coder, run_tester

client = Anthropic()

WORKSPACE = os.path.abspath(os.getenv("WORKSPACE", "projects"))

SYSTEM_PROMPT = """You are an orchestrator for a team of specialist software engineering agents.
You receive requests from a developer via iMessage and coordinate your team to fulfill them.

Your team:
- coder: writes and edits code
- tester: writes and runs tests

You MUST always call the create_plan tool. Never respond with plain text or code.
Delegate all actual work to your team — do not write code or run commands yourself.

For project_dir: infer a short slug from the request (e.g. "spotify-vote", "todo-app"). Only set needs_clarification=true if the request is so vague you genuinely cannot proceed at all."""

SYNTHESIZE_PROMPT = """You are an orchestrator summarizing completed agent work for a developer via iMessage.
Rules:
- 1-3 sentences max
- No code, no file contents, no diffs, no markdown
- Say what was done and whether it succeeded, nothing else
- Example: "Scaffolded the project with FastAPI and a basic auth module. All tests pass."
"""
PLAN_TOOL = {
    "name": "create_plan",
    "description": "Create a task plan delegating work to specialist agents.",
    "input_schema": {
        "type": "object",
        "properties": {
            "needs_clarification": {
                "type": "boolean",
                "description": "True if you need to ask the user something before proceeding.",
            },
            "clarification": {
                "type": "string",
                "description": "The question to ask the user. Required when needs_clarification is true.",
            },
            "project_dir": {
                "type": "string",
                "description": (
                    "Directory name for the project under the workspace (e.g. 'spotify-vote'). "
                    "Use the existing project if one is already in context."
                ),
            },
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "agent": {
                            "type": "string",
                            "enum": ["coder", "tester"],
                        },
                        "task": {"type": "string"},
                        "depends_on": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["agent", "task", "depends_on"],
                },
            },
        },
        "required": ["needs_clarification", "tasks"],
    },
}

# ── Step 1: plan ───────────────────────────────────────────────────────────


def plan(state: AgentState) -> dict:
    messages = state["messages"]

    # Append current project to the last user message so Claude has context
    if state.get("local_path"):
        last = messages[-1]
        messages = messages[:-1] + [
            {
                "role": last["role"],
                "content": f"{last['content']}\n\nCurrent project: {state['local_path']}",
            }
        ]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[PLAN_TOOL],
        tool_choice={"type": "tool", "name": "create_plan"},
        messages=messages,
    )

    tool_block = next(
        (b for b in response.content if hasattr(b, "type") and b.type == "tool_use"),
        None,
    )
    if not tool_block:
        raw = next(
            (b.text for b in response.content if hasattr(b, "text")),
            "I'm not sure how to help with that.",
        )
        return {"messages": [{"role": "assistant", "content": raw}], "task_results": []}

    plan_data = tool_block.input
    print(f"[plan] {plan_data}")

    # Return the clarification question as the message so it's ready to send
    if plan_data.get("needs_clarification"):
        question = plan_data.get("clarification", "Which project should I work on?")
        return {
            "messages": [{"role": "assistant", "content": question}],
            "_plan": plan_data,
        }

    return {
        "messages": [{"role": "assistant", "content": ""}],
        "_plan": plan_data,
    }


# ── Step 2: setup ──────────────────────────────────────────────────────────
# Ensure local_path exists on disk before agents run.


def setup(state: AgentState) -> dict:
    plan_data = state.get("_plan", {})
    project_dir = plan_data.get("project_dir", "")

    if not project_dir:
        return {}

    local_path = os.path.join(WORKSPACE, project_dir)
    os.makedirs(local_path, exist_ok=True)

    # Init git repo if not already one
    if not os.path.exists(os.path.join(local_path, ".git")):
        subprocess.run(["git", "init"], cwd=local_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "init"],
            cwd=local_path,
            capture_output=True,
            env={
                **os.environ,
                "GIT_AUTHOR_NAME": "linqlace",
                "GIT_AUTHOR_EMAIL": "bot@linqlace",
                "GIT_COMMITTER_NAME": "linqlace",
                "GIT_COMMITTER_EMAIL": "bot@linqlace",
            },
        )

    print(f"[setup] local_path={local_path}")
    return {"local_path": local_path}


# ── Agent nodes ────────────────────────────────────────────────────────────


def coder_node(state: AgentState) -> dict:
    result = run_coder(state, state.get("_current_task", ""))
    return {"task_results": [result]}


def tester_node(state: AgentState) -> dict:
    result = run_tester(state, state.get("_current_task", ""))
    return {"task_results": [result]}


# ── Step 3: synthesize ─────────────────────────────────────────────────────


def synthesize(state: AgentState) -> dict:
    results_summary = "\n".join(
        f"{r['agent'].upper()}: {'✓' if r['success'] else '✗'} {r['summary'][:300]}"
        for r in state.get("task_results", [])
    )

    last_user = next(
        (m["content"] for m in reversed(state["messages"]) if m.get("role") == "user"),
        "",
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYNTHESIZE_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"User asked: {last_user}\n\n"
                    f"Project: {state.get('local_path', 'unknown')}\n\n"
                    f"Agent results:\n{results_summary}"
                ),
            }
        ],
    )

    final_text = next((b.text for b in response.content if hasattr(b, "text")), "Done.")
    return {
        "messages": [{"role": "assistant", "content": final_text}],
        "task_results": [],
    }


# ── Routing ────────────────────────────────────────────────────────────────


def after_plan(state: AgentState):
    plan_data = state.get("_plan") or {}
    print(f"[after_plan] {plan_data}")

    if plan_data.get("needs_clarification") and not state.get("local_path"):
        return END

    tasks = plan_data.get("tasks", [])
    first_wave = [t for t in tasks if not t.get("depends_on")]
    if not first_wave:
        return END

    print(f"[after_plan] dispatching {[t['agent'] for t in first_wave]}")
    return [
        Send(f"{task['agent']}_node", {**state, "_current_task": task["task"]})
        for task in first_wave
    ]


# ── Graph assembly ─────────────────────────────────────────────────────────


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("plan", plan)
    graph.add_node("setup", setup)
    graph.add_node("coder_node", coder_node)
    graph.add_node("tester_node", tester_node)
    graph.add_node("synthesize", synthesize)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "setup")
    graph.add_conditional_edges("setup", after_plan)

    for node in ["coder_node", "tester_node"]:
        graph.add_edge(node, "synthesize")

    graph.add_edge("synthesize", END)

    return graph.compile(checkpointer=checkpointer)


agent = build_graph()

# ── Public entry point ─────────────────────────────────────────────────────


async def run_orchestrator(phone_number: str, user_message: str) -> str:
    config = {"configurable": {"thread_id": phone_number}}

    # operator.add reducer means we only pass the *new* user message;
    # the checkpointer-restored history is appended to automatically.
    initial_state = {
        "messages": [{"role": "user", "content": user_message}],
        "phone_number": phone_number,
        "task_results": [],
        "github_token": os.getenv("GITHUB_TOKEN"),
        "current_task": user_message,
        "_plan": None,
    }

    # Run sync invoke in a thread so we don't block the event loop
    final_state = await asyncio.to_thread(agent.invoke, initial_state, config)

    for msg in reversed(final_state["messages"]):
        if msg.get("role") == "assistant":
            content = msg["content"]
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return next((b.text for b in content if hasattr(b, "text")), "Done.")
    return "Done."
