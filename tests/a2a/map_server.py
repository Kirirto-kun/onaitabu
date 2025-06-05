import os
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, Message, MessageSendParams, Task, Role, Part, TextPart
from a2a.server.request_handlers.request_handler import RequestHandler
from a2a.server.apps import A2AStarletteApplication
import uvicorn
import asyncio
from map import llm_agent, InMemorySessionService, Runner, parse_prompt, geocode_location, search_places

# ADK constants (дублируем для удобства)
APP_NAME = "onaitabu_map"
USER_ID = "user_map"
SESSION_ID = "map_session_1"

async def map_logic(query: str) -> str:
    session_service = InMemorySessionService()
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    runner = Runner(agent=llm_agent, app_name=APP_NAME, session_service=session_service)
    place_type, location, radius = await parse_prompt(query, runner)
    if not place_type or not location or not radius:
        return "Could not extract place type, location, or radius from the prompt."
    lat, lng = geocode_location(location)
    places = search_places(lat, lng, place_type, radius)
    if not places:
        return f"No places found for '{place_type}' near '{location}'."
    # Формируем краткий текстовый ответ
    lines = []
    for i, place in enumerate(places[:5], 1):
        name = place.get('name')
        address = place.get('vicinity')
        rating = place.get('rating', 'N/A')
        lines.append(f"{i}. {name} (Rating: {rating}) - {address}")
    return f"Top {place_type.title()} near {location} (radius: {radius}m):\n" + "\n".join(lines)

class MapHandler(RequestHandler):
    async def on_message_send(self, params: MessageSendParams, context=None):
        user_message = params.message.parts[0].root.text
        result = await map_logic(user_message)
        return Message(
            messageId="1",
            role=Role.agent,
            parts=[Part(root=TextPart(text=result))],
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
    name="MapAgent",
    description="Поиск по картам и местам",
    version="1.0",
    url="http://localhost:8002",
    capabilities=AgentCapabilities(),
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    skills=[
        AgentSkill(
            id="find_place",
            name="Find Place",
            description="Находит места по описанию и адресу",
            tags=["map"]
        )
    ]
)

handler = MapHandler()
app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler).build()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002) 