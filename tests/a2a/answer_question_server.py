import os
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, Message, MessageSendParams, Task, Role, Part, TextPart
from a2a.server.request_handlers.request_handler import RequestHandler
from a2a.server.apps import A2AStarletteApplication
import uvicorn
from question_answer import AppAgentDeps, setup_vector_store, build_agent
import asyncio

# Инициализация агента один раз при старте сервера
_deps = AppAgentDeps()
_deps = setup_vector_store(_deps)
_agent = build_agent(_deps.vector_store_id)

async def answer_question_logic(query: str) -> str:
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _agent.run_sync, query)
    answer = result.output.answer
    source = result.output.source
    return f"{answer}\n(Источник: {source})"

class AnswerQuestionHandler(RequestHandler):
    async def on_message_send(self, params: MessageSendParams, context=None):
        user_message = params.message.parts[0].root.text
        answer = await answer_question_logic(user_message)
        return Message(
            messageId="1",
            role=Role.agent,
            parts=[Part(root=TextPart(text=answer))],
            kind="message"
        )
    async def on_get_task(self, params, context=None):
        return None
    async def on_cancel_task(self, params, context=None):
        return None
    async def on_message_send_stream(self, params, context=None):
        return
    async def on_set_task_push_notification_config(self, params, context=None):
        return None
    async def on_get_task_push_notification_config(self, params, context=None):
        return None
    async def on_resubscribe_to_task(self, params, context=None):
        return

agent_card = AgentCard(
    name="AnswerQuestionAgent",
    description="Отвечает на вопросы по PDF",
    version="1.0",
    url="http://localhost:8001",
    capabilities=AgentCapabilities(),
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    skills=[
        AgentSkill(
            id="answer_question",
            name="Answer Question",
            description="Отвечает на вопросы по PDF",
            tags=["qa"]
        )
    ]
)

handler = AnswerQuestionHandler()
app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler).build()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001) 