import os
import requests
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import asyncio
import json
from pydantic import BaseModel, Field
# Load API key from .env
load_dotenv()
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

if not API_KEY:
    raise ValueError("GOOGLE_MAPS_API_KEY not found in .env file.")

# ADK constants
APP_NAME = "onaitabu_map"
USER_ID = "user_map"
SESSION_ID = "map_session_1"
class PlaceType(BaseModel):
    place_type: str = Field(..., description="The type of place to search for")
    location: str = Field(..., description="The location to search for the place")
    radius: int = Field(..., description="The radius of the search in meters")



# Initialize Gemini LLM agent (ensure Gemini API key is set up as per ADK docs)
llm_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="place_extractor_agent",
    description="Extracts place type and location from user queries about places.",
    instruction="""You are an assistant that extracts structured information from user queries about places.\nGiven a prompt like 'best cafes near Satpaev University', extract the place(with full information, including specific information about the place) type and location(formatted as a full address).""",
    output_schema=PlaceType
)

# Step 1: Geocode the location to get lat/lng
def geocode_location(location):
    url = f'https://maps.googleapis.com/maps/api/geocode/json'
    params = {'address': location, 'key': API_KEY}
    resp = requests.get(url, params=params)
    data = resp.json()
    if data['status'] == 'OK':
        loc = data['results'][0]['geometry']['location']
        return loc['lat'], loc['lng']
    else:
        raise ValueError(f"Could not geocode location: {location}")

# Step 2: Search for places nearby
def search_places(lat, lng, place_type, radius):
    url = f'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
    params = {
        'location': f'{lat},{lng}',
        'radius': radius,  # meters
        'keyword': place_type,
        'key': API_KEY,
        'rankby': 'prominence',
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    if data['status'] == 'OK':
        return data['results']
    else:
        raise ValueError(f"Places API error: {data['status']}")

# Step 3: Format and print results
def print_places(places):
    for i, place in enumerate(places[:5], 1):
        print(place)
        name = place.get('name')
        address = place.get('vicinity')
        rating = place.get('rating', 'N/A')
        print(f"{i}. {name} (Rating: {rating}) - {address}")

async def parse_prompt(prompt, runner):
    """
    Use Gemini LLM agent to extract place_type, location, and radius from the prompt.
    """
    content = types.Content(role='user', parts=[types.Part(text=prompt)])
    events = runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)
    for event in events:
        if event.is_final_response():
            result = event.content.parts[0].text.strip()
            if not result:
                print("LLM returned an empty response.")
                return None, None, None
            try:
                parsed = PlaceType.parse_raw(result)
                return parsed.place_type, parsed.location, parsed.radius
            except Exception as e:
                print("Could not parse LLM output as PlaceType. Raw output:")
                print(result)
                return None, None, None
    print("No final response from agent.")
    return None, None, None

async def main():
    session_service = InMemorySessionService()
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    runner = Runner(agent=llm_agent, app_name=APP_NAME, session_service=session_service)

    prompt = input("Enter your prompt (e.g. 'best cafes near Satpaev University'): ")
    place_type, location, radius = await parse_prompt(prompt, runner)
    print(place_type, location, radius)
    if not place_type or not location or not radius:
        print("Could not extract place type, location, or radius from the prompt.")
        return
    lat, lng = geocode_location(location)
    places = search_places(lat, lng, place_type, radius)
    print(f"\nTop {place_type.title()} near {location} (radius: {radius}m):")
    print_places(places)

if __name__ == "__main__":
    asyncio.run(main())
