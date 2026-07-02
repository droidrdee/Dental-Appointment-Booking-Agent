import argparse
import asyncio
import uuid
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx
from app.main import app


def build_payload(call_id: str, tool_id: str, name: str, value: str) -> dict:
    return {
        "message": {
            "type": "tool-calls",
            "call": {
                "id": call_id,
                "customer": {"number": "+911234567890"},
            },
            "toolCallList": [
                {
                    "id": tool_id,
                    "name": name,
                    "arguments": {"value": value},
                }
            ],
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate a VAPI booking call.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--call-id", default=f"call_{uuid.uuid4().hex[:10]}")
    args = parser.parse_args()

    steps = [
        ("tool_1", "collect_patient_name", "Asha Patel"),
        ("tool_2", "collect_service", "root canal"),
        ("tool_3", "collect_datetime", "tomorrow at 3pm"),
        ("tool_4", "confirm_and_book", "yes"),
    ]

    async def run() -> None:
        if args.base_url in {"http://127.0.0.1:8000", "http://localhost:8000"}:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
                timeout=15,
            ) as client:
                await _run_steps(client, steps, args.call_id)
            return

        async with httpx.AsyncClient(base_url=args.base_url, timeout=15) as client:
            await _run_steps(client, steps, args.call_id)

    asyncio.run(run())


async def _run_steps(
    client: httpx.AsyncClient,
    steps: list[tuple[str, str, str]],
    call_id: str,
) -> None:
    for tool_id, name, value in steps:
        response = await client.post(
            "/webhook/vapi",
            json=build_payload(call_id, tool_id, name, value),
        )
        print(f"{name}: {response.status_code} {response.text}")
        response.raise_for_status()


if __name__ == "__main__":
    main()
