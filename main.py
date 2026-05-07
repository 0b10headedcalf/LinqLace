# main.py
import os
from linq import send_message
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks
from dotenv import load_dotenv
from agents.orchestrator import run_orchestrator

load_dotenv()


def _allowed_numbers() -> set[str]:
    raw = os.getenv("ALLOWED_NUMBERS", "")
    return {n.strip() for n in raw.split(",") if n.strip()}


@asynccontextmanager
async def lifespan(app: FastAPI):
    required = [
        "ANTHROPIC_API_KEY",
        "LINQ_API_KEY",
        "LINQ_PHONE_NUMBER",
        "ALLOWED_NUMBERS",
        "GITHUB_TOKEN",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing environment variables: {missing}")
    if not _allowed_numbers():
        raise RuntimeError("ALLOWED_NUMBERS must contain at least one phone number")
    print("✓ All environment variables present")
    yield


app = FastAPI(lifespan=lifespan)


async def handle_message(phone_number: str, text: str) -> None:
    """
    Runs in the background after the webhook returns 200.
    This is the entire application flow in one place.
    """
    try:
        await send_message(phone_number, "⏳ Working...")

        reply = await run_orchestrator(phone_number, text)

        await send_message(phone_number, reply)

    except Exception as e:
        # Log full error internally, send generic reply to avoid leaking secrets/internals
        print(f"Error handling message from {phone_number}: {e!r}")
        await send_message(phone_number, "Something went wrong on my end.")


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    body = await request.json()

    if body.get("event_type") != "message.received":
        return {"status": "ignored"}

    data = body.get("data", {})
    phone_number = data.get("sender_handle", {}).get("handle")
    parts = data.get("parts") or [{}]
    text = parts[0].get("value", "")

    if phone_number not in _allowed_numbers():
        print(f"Rejected message from non-allowlisted number: {phone_number}")
        return {"status": "ignored"}

    print(f"Message from {phone_number}: {text}")

    if phone_number and text:
        background_tasks.add_task(handle_message, phone_number, text)

    return {"status": "ok"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
