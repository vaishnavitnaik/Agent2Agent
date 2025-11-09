# # # file_writer_agent.py

# # import os
# # import uvicorn
# # from starlette.responses import JSONResponse
# # from starlette.routing import Route

# # from a2a.server.agent_execution import AgentExecutor, RequestContext
# # from a2a.server.events import EventQueue
# # from a2a.server.apps import A2AStarletteApplication
# # from a2a.server.request_handlers import DefaultRequestHandler
# # from a2a.server.tasks import InMemoryTaskStore
# # from a2a.types import (
# #     AgentCard, AgentCapabilities, AgentSkill,
# #     TaskStatusUpdateEvent, TaskStatus
# # )
# # from a2a.utils import new_agent_text_message


# # OUTPUT_FILE = "output.txt"


# # class WriterExecutor(AgentExecutor):

# #     async def execute(self, context: RequestContext, queue: EventQueue):

# #         text = context.message.parts[0].text
# #         task_id = context.task_id
# #         context_id = context.context_id

# #         # ✅ Write text to a file
# #         with open(OUTPUT_FILE, "w") as f:
# #             f.write(text)

# #         await queue.enqueue_event(
# #             new_agent_text_message(f"✅ Written to output.txt: {text}")
# #         )

# #         # ✅ Mark task completed
# #         await queue.enqueue_event(
# #             TaskStatusUpdateEvent(
# #                 taskId=task_id,
# #                 contextId=context_id,
# #                 status=TaskStatus(
# #                     state="completed",
# #                     message=new_agent_text_message("File write complete")
# #                 ),
# #                 final=True
# #             )
# #         )

# #     async def cancel(self, context: RequestContext, queue: EventQueue):
# #         await queue.enqueue_event(new_agent_text_message("Task cancelled"))


# # async def health(request):
# #     return JSONResponse({"ok": True})


# # def create_app(port):
# #     skill = AgentSkill(
# #         id="write_file",
# #         name="Write Result to File",
# #         description="Writes incoming text to output.txt",
# #         tags=["file"]
# #     )

# #     card = AgentCard(
# #         name="File Writer Agent",
# #         description="Receives text & writes it to a file",
# #         version="1.0",
# #         url=f"http://localhost:{port}/",
# #         capabilities=AgentCapabilities(streaming=True),

# #         # ✅ REQUIRED
# #         defaultInputModes=["text/plain"],
# #         defaultOutputModes=["text/plain"],

# #         skills=[skill],
# #     )

# #     handler = DefaultRequestHandler(WriterExecutor(), InMemoryTaskStore())
# #     app = A2AStarletteApplication(card, handler).build()
# #     app.router.routes.append(Route("/health", health))
# #     return app


# # if __name__ == "__main__":
# #     port = int(os.getenv("WRITER_AGENT_PORT", 5002))
# #     uvicorn.run(create_app(port), host="0.0.0.0", port=port)


# # file_writer_agent.py
# import os
# import uvicorn
# import asyncio
# from starlette.responses import JSONResponse
# from starlette.routing import Route

# from a2a.server.agent_execution import AgentExecutor, RequestContext
# from a2a.server.events import EventQueue
# from a2a.server.apps import A2AStarletteApplication
# from a2a.server.request_handlers import DefaultRequestHandler
# from a2a.server.tasks import InMemoryTaskStore
# from a2a.types import AgentCard, AgentCapabilities, AgentSkill
# from a2a.utils import new_agent_text_message

# OUTPUT_FILE = "output.txt"
# PORT = int(os.getenv("WRITER_AGENT_PORT", 5002))


# class WriterExecutor(AgentExecutor):

#     async def execute(self, context: RequestContext, queue: EventQueue):
#         await asyncio.sleep(0)

#         text = context.message.parts[0].text or ""

#         with open(OUTPUT_FILE, "w") as f:
#             f.write(text)

#         await queue.enqueue_event(
#             new_agent_text_message(f"✅ File written: {text}")
#         )

#     async def cancel(self, context, queue):
#         await queue.enqueue_event(new_agent_text_message("Cancelled"))


# async def health(request):
#     return JSONResponse({"ok": True})


# def create_app():
#     skill = AgentSkill(
#         id="write_file",
#         name="File Writer",
#         description="Writes text to a file"
#     )

#     card = AgentCard(
#         name="File Writer Agent",
#         description="Writes incoming text to a file",
#         version="1.0.0",
#         url=f"http://localhost:{PORT}/",
#         capabilities=AgentCapabilities(streaming=True),
#         defaultInputModes=["text/plain"],
#         defaultOutputModes=["text/plain"],
#         skills=[skill],
#     )

#     handler = DefaultRequestHandler(WriterExecutor(), InMemoryTaskStore())

#     app = A2AStarletteApplication(card, handler).build()
#     app.router.routes.append(Route("/health", health))

#     return app


# if __name__ == "__main__":
#     uvicorn.run(create_app(), host="0.0.0.0", port=PORT, log_level="info")


# file_writer_agent.py

import os
import uvicorn
from starlette.responses import JSONResponse
from starlette.routing import Route

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from a2a.types import (
    AgentCard,
    AgentSkill,
    AgentCapabilities,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_agent_text_message

OUTPUT_FILE = "output.txt"


# ✅ Universal safe extractor for A2A v0.3.0
def extract_text(context: RequestContext) -> str:
    if not context.message or not context.message.parts:
        return ""

    for p in context.message.parts:
        if hasattr(p, "root") and hasattr(p.root, "text"):
            return p.root.text

    return ""


class WriterExecutor(AgentExecutor):

    async def execute(self, context: RequestContext, queue: EventQueue):

        text = extract_text(context)
        task_id = context.task_id
        context_id = context.context_id

        # === STAGE 1: SUBMITTED ===
        await queue.enqueue_event(TaskStatusUpdateEvent(
            taskId=task_id,
            contextId=context_id,
            status=TaskStatus(
                state="submitted",
                message=new_agent_text_message("Writer: task received")
            ),
            final=False
        ))

        # No input case
        if not text:
            text = "ERROR: No text provided"

        # === STAGE 2: WORKING ===
        await queue.enqueue_event(TaskStatusUpdateEvent(
            taskId=task_id,
            contextId=context_id,
            status=TaskStatus(
                state="working",
                message=new_agent_text_message(f"Writing: {text}")
            ),
            final=False
        ))

        # ✅ Write to file
        with open(OUTPUT_FILE, "a") as f:
            f.write(text + "\n")

        # ✅ Send user-facing message
        await queue.enqueue_event(new_agent_text_message(f"WROTE: {text}"))

        # === STAGE 3: COMPLETED ===
        await queue.enqueue_event(TaskStatusUpdateEvent(
            taskId=task_id,
            contextId=context_id,
            status=TaskStatus(
                state="completed",
                message=new_agent_text_message("Writer: done")
            ),
            final=True
        ))

    async def cancel(self, context: RequestContext, queue: EventQueue):
        await queue.enqueue_event(new_agent_text_message("Writer task cancelled"))


async def health(request):
    return JSONResponse({"status": "healthy", "agent": "File Writer Agent"})


def create_app(port: int):

    skill = AgentSkill(
        id="write_file",
        name="File Writer",
        description="Writes incoming text to output.txt",
        tags=["file", "writer"]
    )

    card = AgentCard(
        name="File Writer Agent",
        description="Writes text to output.txt",
        version="2.0.0",
        url=f"http://localhost:{port}/",
        protocolVersion="0.3.0",
        preferredTransport="JSONRPC",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )

    handler = DefaultRequestHandler(
        agent_executor=WriterExecutor(),
        task_store=InMemoryTaskStore()
    )

    app = A2AStarletteApplication(card, handler).build()

    # Additional health endpoint
    app.router.routes.append(Route("/health", health))

    return app


if __name__ == "__main__":
    port = int(os.getenv("WRITER_AGENT_PORT", 5002))

    print("="*70)
    print(f"📝 File Writer Agent Starting on Port {port}")
    print("="*70)
    print(f"AgentCard:   http://localhost:{port}/.well-known/agent.json")
    print(f"A2A Endpoint http://localhost:{port}/")
    print(f"Health:      http://localhost:{port}/health")
    print("="*70)

    uvicorn.run(create_app(port), host="0.0.0.0", port=port, log_level="info")
