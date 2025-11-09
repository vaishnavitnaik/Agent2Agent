import os
import json
import asyncio
import uvicorn

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    TaskStatus,
    TaskStatusUpdateEvent,
    Message
)
from a2a.utils import new_agent_text_message
from starlette.routing import Route
from starlette.responses import JSONResponse


# ✅ Universal extractor (A2A v0.3.0)
def extract_text(context: RequestContext) -> str:
    if context.message and context.message.parts:
        for part in context.message.parts:
            if hasattr(part, "root") and hasattr(part.root, "text"):
                return part.root.text
    return ""

import uuid
class CalculatorExecutor(AgentExecutor):

    async def execute(self, context: RequestContext, queue: EventQueue):
        expr = extract_text(context)
        task_id = context.task_id
        context_id = context.context_id

        # === submitted ===
        await queue.enqueue_event(TaskStatusUpdateEvent(
            taskId=task_id,
            contextId=context_id,
            status=TaskStatus(
                state="submitted",
                message=new_agent_text_message("Task received")
            ),
            final=False
        ))

        # === working ===
        await queue.enqueue_event(TaskStatusUpdateEvent(
            taskId=task_id,
            contextId=context_id,
            status=TaskStatus(
                state="working",
                message=new_agent_text_message("Evaluating expression...")
            ),
            final=False
        ))

        # Evaluate
        try:
            value = eval(expr)
            result_text = str(value)
            valid = True
        except Exception:
            value = None
            result_text = "ERROR"
            valid = False

        # Artifact #1: text
        await queue.enqueue_event(
            Message(
                role="agent",
                messageId=str(uuid.uuid4()),
                parts=[{"kind": "text", "text": result_text}]
            )
        )

        # Artifact #2: JSON
        structured = {
            "expression": expr,
            "result": value,
            "valid": valid
        }

        await queue.enqueue_event(
            Message(
                role="agent",
                messageId=str(uuid.uuid4()),
                parts=[{"kind": "text", "text": json.dumps(structured)}]
            )
        )

        # completed
        await queue.enqueue_event(TaskStatusUpdateEvent(
            taskId=task_id,
            contextId=context_id,
            status=TaskStatus(
                state="completed",
                message=new_agent_text_message("Calculation complete")
            ),
            final=True
        ))

    async def cancel(self, context: RequestContext, queue: EventQueue):
        await queue.enqueue_event(
            new_agent_text_message("Calculation cancelled")
        )


async def health(request):
    return JSONResponse({"status": "healthy", "agent": "Calculator"})


def create_app(port):

    skill = AgentSkill(
        id="calc",
        name="Calculator",
        description="Evaluates arithmetic expressions",
        tags=["math"]
    )

    card = AgentCard(
        name="Calculator Agent",
        description="Evaluates arithmetic expressions",
        version="1.0.0",
        url=f"http://localhost:{port}/",
        protocolVersion="0.3.0",
        preferredTransport="JSONRPC",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )

    handler = DefaultRequestHandler(
        agent_executor=CalculatorExecutor(),
        task_store=InMemoryTaskStore()
    )

    app = A2AStarletteApplication(card, handler).build()

    app.router.routes.append(Route("/health", health))

    return app


if __name__ == "__main__":
    port = int(os.getenv("CALCULATOR_AGENT_PORT", 5001))

    print("=" * 70)
    print(f"➗ Calculator Agent on : {port}")
    print("=" * 70)
    print(f"AgentCard:  http://localhost:{port}/.well-known/agent.json")
    print(f"Stream:     http://localhost:{port}/")
    print(f"Health:     http://localhost:{port}/health")
    print("=" * 70)

    uvicorn.run(create_app(port), host="0.0.0.0", port=port, log_level="info")
