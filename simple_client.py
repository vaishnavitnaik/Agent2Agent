import asyncio
import httpx
import json
import uuid


def pretty(obj):
    """Pretty-print a JSON object."""
    print(json.dumps(obj, indent=2))


async def fetch_agent_card(base):
    url = f"{base}.well-known/agent.json"
    print(f"\n🔍 Fetching {url}")

    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        card = resp.json()
        pretty(card)
        return card


async def stream_to_agent(base_url, text):
    """Send text to an agent using message/stream and print all A2A events."""
    task_id = str(uuid.uuid4())
    context_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "message/stream",
        "params": {
            "message": {
                "role": "user",
                "messageId": message_id,
                "parts": [
                    {"kind": "text", "text": text}
                ]
            },
            "taskId": task_id,
            "contextId": context_id
        }
    }

    print("\n📤 REQUEST:")
    pretty(payload)

    result_value = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream(
            "POST",
            base_url,
            json=payload,
            headers={"Accept": "application/x-ndjson"},
        ) as resp:

            resp.raise_for_status()

            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                raw = line[6:].strip()

                try:
                    event = json.loads(raw)
                except:
                    continue

                # ✅ EXACT A2A full JSON print
                pretty(event)

                result = event.get("result", {})
                kind = result.get("kind")

                # ----------------------------------------------------------------------
                # ✅ Extract human-readable TEXT properly from BOTH A2A message formats
                # ----------------------------------------------------------------------
                if kind == "message":

                    # ✅ Format A (your calculator emits this)
                    if "parts" in result:
                        for p in result["parts"]:
                            if p["kind"] == "text":
                                result_value = p["text"]
                        continue

                    # ✅ Format B (strict A2A spec)
                    msg = result.get("message", {})
                    if "parts" in msg:
                        for p in msg["parts"]:
                            if p["kind"] == "text":
                                result_value = p["text"]
                        continue

                # ----------------------------------------------------------------------
                # ✅ Artifact-update (some agents use this instead of message)
                # ----------------------------------------------------------------------
                if kind == "artifact-update":
                    artifact = result.get("artifact", {})
                    for p in artifact.get("parts", []):
                        if p["kind"] == "text":
                            # If this is plain text (not JSON artifact), capture it
                            try:
                                json.loads(p["text"])  # skip JSON artifacts
                            except:
                                if result_value is None:
                                    result_value = p["text"]

                # ----------------------------------------------------------------------
                # Ignore status-update for value extraction
                # ----------------------------------------------------------------------

    return result_value


async def main():
    calc = "http://localhost:5001/"
    writer = "http://localhost:5002/"

    # Fetch both agent cards
    await fetch_agent_card(calc)
    await fetch_agent_card(writer)

    # ------------------- Calculator -------------------
    print("\n➡️ Sending to Calculator")
    result = await stream_to_agent(calc, "10 + 20 * 3")

    print("\n✅ Calculator produced:", result)

    # ------------------- Writer -------------------
    print("\n➡️ Sending result to Writer")
    await stream_to_agent(writer, result)

    print("\n✅ Finished. Written to output.txt")


if __name__ == "__main__":
    asyncio.run(main())
