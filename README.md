# Linqlace

An agentic software engineering assistant that lives in your iMessage. Text it a task, get working code back.

## What it does

linqlace is a FastAPI webhook server that receives messages via the [Linq](https://linqapp.com) iMessage API, delegates work to a team of Claude-powered agents, and texts you back with results.

Your agent team:

- **Orchestrator** — plans tasks, coordinates the team, and synthesizes results
- **Coder** — reads, writes, and edits code in a local git repo
- **Tester** — writes and runs tests with pytest

## Architecture

```
iMessage → Linq API → /webhook (FastAPI)
                           ↓
                    Orchestrator (LangGraph)
                           ↓
              ┌────────────┴────────────┐
              ↓                         ↓
           Coder                     Tester
              ↓                         ↓
    ┌───────────────────────────────────────┐
    │  Tools: read/write files, shell, git  │
    └───────────────────────────────────────┘
              ↓
          Synthesize
              ↓
         iMessage reply
```

- **LangGraph** orchestrates the agent workflow with per-phone-number persistent state
- **SQLite** stores conversation memory across sessions
- **Claude** powers all agents
- Local workspace in `projects/` (git repos are auto-initialized)
- GitHub integration for cloning repos and opening PRs

## Quick start

### Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended)

### Install

```bash
git clone <repo>
cd linqlace
uv sync
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API access |
| `LINQ_API_KEY` | Linq iMessage API key |
| `LINQ_PHONE_NUMBER` | Your bot's Linq phone number |
| `LINQ_WEBHOOK_SECRET` | Webhook signature verification |
| `ALLOWED_NUMBERS` | Comma-separated allowlist of sender phone numbers |
| `GITHUB_TOKEN` | For cloning private repos and opening PRs |
| `WORKSPACE` | Local directory for projects (default: `projects`) |
| `NGROK_TOKEN` | (optional) For local tunneling |

### Run

```bash
uv run fastapi dev main.py
```

Expose the webhook with ngrok:

```bash
ngrok http 8000
```

Then set your Linq webhook URL to `https://<your-ngrok>.ngrok.io/webhook`.

## Usage

Text your bot a request:

> "scaffold a fastapi todo app with sqlite"

> "add user auth to my spotify-vote project"

> "write tests for the auth module"

The orchestrator plans the work, dispatches agents, and texts you back a summary.

## Project structure

```
.
├── main.py                 # FastAPI app + webhook handler
├── linq.py                 # Linq iMessage API client
├── state.py                # LangGraph state schema
├── memory.py               # SQLite checkpointer
├── agents/
│   ├── orchestrator.py     # Planning + synthesis graph
│   ├── coder.py            # Code-writing agent
│   ├── tester.py           # Test-writing agent
│   └── _base.py            # Shared agentic loop
└── tools/
    ├── file_tools.py       # read_file, write_file, list_files
    ├── shell_tools.py      # run_command (whitelist-restricted)
    ├── git_tools.py        # clone_repo, push_and_open_pr
    └── __init__.py         # Tool routing
```

## Safety

- File operations are sandboxed to the workspace directory (path traversal protection)
- Shell commands are restricted to a safe whitelist (git, pytest, python, pip, etc.)
- Phone number allowlist prevents unauthorized access
- Error messages sent to users never leak internals or secrets

## License

MIT
