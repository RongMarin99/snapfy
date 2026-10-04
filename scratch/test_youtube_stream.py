import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from scratch.test_youtube_plugin import YouTubePlugin

async def main():
    plugin = YouTubePlugin()
    print("Scraping Channel Shorts:")
    data = await plugin.scrape_series("https://www.youtube.com/@Google/shorts")
    print(f"Title: {data['title'].encode('ascii', 'ignore').decode('ascii')}, Episodes: {len(data['episodes'])}")
    if data['episodes']:
        first_ep = data['episodes'][0]
        safe_title = first_ep['title'].encode('ascii', 'ignore').decode('ascii')
        print("First Ep Title:", safe_title)
        print("First Ep URL:", first_ep['url'])
        stream = await plugin.resolve_stream(first_ep['url'])
        print("Resolved stream media_type:", stream['media_type'])
        print("Resolved stream URL sample:", stream['stream_url'][:100])

if __name__ == "__main__":
    asyncio.run(main())
