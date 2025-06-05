import http.client
import json
import os
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv('SERPER_API_KEY')
SERPER_API_HOST = 'google.serper.dev'
SERPER_API_PATH = '/search'


def search_serper(query):
    conn = http.client.HTTPSConnection(SERPER_API_HOST)
    payload = json.dumps({
        "q": query
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    conn.request("POST", SERPER_API_PATH, payload, headers)
    res = conn.getresponse()
    data = res.read()
    conn.close()
    return data.decode("utf-8")


def main():
    query = input("Enter your search query: ")
    result = search_serper(query)
    print(result)


if __name__ == "__main__":
    main() 