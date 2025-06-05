import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    # Create an instance of AsyncWebCrawler
    async with AsyncWebCrawler() as crawler:
        # Run the crawler on a URL
        result = await crawler.arun(url="https://yandex.ru/maps/org/coffee_boom/39554143272/")

        # Print the extracted content
        print(result.markdown)

# Run the async main function
asyncio.run(main()) 
