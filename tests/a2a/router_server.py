import os
import requests
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, Message, MessageSendParams, Task, Role, Part, TextPart
from a2a.server.request_handlers.request_handler import RequestHandler
from a2a.server.apps import A2AStarletteApplication
import uvicorn

# Адреса backend-агентов
ANSWER_QUESTION_URL = os.getenv("ANSWER_QUESTION_URL", "http://localhost:8001")
MAP_URL = os.getenv("MAP_URL", "http://localhost:8002")

# Классификатор: map или qa
MAP_KEYWORDS = ["карта", "place", "address", "где находится", "найти на карте", "location", "координаты"]
def classify_query(query: str) -> str:
    if any(k in query.lower() for k in MAP_KEYWORDS):
        return "map"
    return "qa"

def call_backend(url: str, query: str) -> str:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "messageId": "1",
                "role": "user",
                "parts": [{"kind": "text", "text": query}]
            },
            "configuration": {"acceptedOutputModes": ["text/plain"]}
        }
    }
    resp = requests.post(url + "/", json=payload)
    resp.raise_for_status()
    data = resp.json()
    # Если ошибка — вернуть её как текст
    if "error" in data:
        return f"Ошибка backend-агента: {data['error'].get('message', str(data['error']))}"
    try:
        parts = data["result"]["parts"]
        # parts может быть dict или объект, пробуем оба варианта
        part = parts[0]
        if isinstance(part, dict):
            return part.get("text", str(part))
        elif hasattr(part, "text"):
            return part.text
        elif hasattr(part, "root") and hasattr(part.root, "text"):
            return part.root.text
        else:
            return str(part)
    except Exception as e:
        return f"Ошибка парсинга ответа backend-агента: {e}"

class RouterHandler(RequestHandler):
    async def on_message_send(self, params: MessageSendParams, context=None):
        user_message = params.message.parts[0].root.text
        target = classify_query(user_message)
        if target == "map":
            answer = call_backend(MAP_URL, user_message)
        else:
            answer = call_backend(ANSWER_QUESTION_URL, user_message)
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
    name="RouterAgent",
    description="Роутер для Q&A и Map агентов",
    version="1.0",
    url="http://localhost:8000",
    capabilities=AgentCapabilities(),
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    skills=[
        AgentSkill(
            id="route_query",
            name="Route Query",
            description="Роутит запросы между Q&A и Map агентами",
            tags=["router"]
        )
    ]
)

handler = RouterHandler()
app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler).build()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 