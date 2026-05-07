# linq.py
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

LINQ_BASE = "https://api.linqapp.com/api/partner/v3"
LINQ_PHONE = os.getenv("LINQ_PHONE_NUMBER")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('LINQ_API_KEY')}",
        "Content-Type": "application/json",
    }


async def send_message(to: str, text: str) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LINQ_BASE}/chats",
            headers=_headers(),
            json={
                "from": LINQ_PHONE,
                "to": [to],
                "message": {"parts": [{"type": "text", "value": text}]},
            },
        )
        response.raise_for_status()
