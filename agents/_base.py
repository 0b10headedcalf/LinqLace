from anthropic import Anthropic
from state import AgentState, TaskResult
from tools import execute_tool

client = Anthropic()

MAX_ITERATIONS = 20


def run_agent(
    state: AgentState,
    task: str,
    *,
    name: str,
    system_prompt: str,
    tools: list,
    model: str = "claude-sonnet-4-6",
) -> TaskResult:
    """Shared agentic loop: call model, execute tool_use blocks, repeat until end_turn."""
    messages = [{"role": "user", "content": task}]

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")),
                f"{name} completed with no summary.",
            )
            return TaskResult(agent=name, summary=final_text, success=True)

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"  [{name}] {block.name}({block.input})")
            result = execute_tool(
                name=block.name,
                inputs=block.input,
                local_path=state["local_path"],
                github_token=state["github_token"],
            )
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": result}
            )
        messages.append({"role": "user", "content": tool_results})

    return TaskResult(
        agent=name,
        summary=f"{name} hit {MAX_ITERATIONS}-iteration cap without finishing.",
        success=False,
    )
