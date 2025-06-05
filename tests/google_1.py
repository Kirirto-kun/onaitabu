import asyncio
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types
import logging

# Configure logging for more detailed output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

APP_NAME = "onaitabu"
USER_ID = "user1234"
SESSION_ID = "1234"

root_agent = Agent(
    name="basic_search_agent",
    model="gemini-2.0-flash",
    description="Agent to answer questions using Google Search.",
    instruction="I can answer your questions by searching the internet. Just ask me anything!",
    tools=[google_search]
)

# Session and Runner
session_service = InMemorySessionService()

async def setup_session():
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)

runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

# Retry Mechanism
async def get_session(session_service, app_name, user_id, session_id, max_retries=5, delay=0.1):
    """
    Attempts to retrieve a session, retrying if it's not found.
    """
    for attempt in range(max_retries):
        try:
            session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
            if session is not None:
                logging.info(f"Session retrieved successfully on attempt {attempt + 1}")
                return session
            else:
                raise ValueError(f"Session not found: {session_id}")
        except ValueError as e:
            logging.warning(f"Session not found on attempt {attempt + 1}: {e}")
            await asyncio.sleep(delay)
    logging.error("Failed to retrieve session after multiple retries.")
    return None

# Agent Interaction with Retry
async def call_agent(query):
    """
    Helper function to call the agent with session retrieval retry.
    """
    session = await get_session(session_service, APP_NAME, USER_ID, SESSION_ID)
    if session is None:
        logging.error("Aborting call_agent due to session retrieval failure.")
        return

    content = types.Content(role='user', parts=[types.Part(text=query)])
    try:
        events = runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

        for event in events:
            if event.is_final_response():
                final_response = event.content.parts[0].text
                print("Agent Response: ", final_response)
    except Exception as e:
        logging.exception(f"Error during runner.run: {e}")


# Run the asynchronous function
async def main():
    await setup_session()
    await call_agent("отправь всю информацию о Chef and Sweets (Rating: 4.6) - Adi Sharipova, Almaty")

if __name__ == "__main__":
    asyncio.run(main())
