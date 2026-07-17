"""RSS feed catalogue. Multiple category feeds per publisher for richer coverage per ingest."""

RSS_FEEDS = [
    # BBC — top + world + business + tech
    ("BBC", "https://feeds.bbci.co.uk/news/rss.xml", "https://bbc.com"),
    ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml", "https://bbc.com"),
    ("BBC", "https://feeds.bbci.co.uk/news/business/rss.xml", "https://bbc.com"),
    ("BBC", "https://feeds.bbci.co.uk/news/technology/rss.xml", "https://bbc.com"),
    # Guardian — world + US + business + tech
    ("The Guardian", "https://www.theguardian.com/world/rss", "https://theguardian.com"),
    ("The Guardian", "https://www.theguardian.com/us-news/rss", "https://theguardian.com"),
    ("The Guardian", "https://www.theguardian.com/business/rss", "https://theguardian.com"),
    ("The Guardian", "https://www.theguardian.com/technology/rss", "https://theguardian.com"),
    # CNBC — top + business + tech
    ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html", "https://cnbc.com"),
    ("CNBC", "https://www.cnbc.com/id/10001147/device/rss/rss.html", "https://cnbc.com"),
    ("CNBC", "https://www.cnbc.com/id/19854910/device/rss/rss.html", "https://cnbc.com"),
    # Fox
    ("Fox News", "https://moxie.foxnews.com/google-publisher/latest.xml", "https://foxnews.com"),
    ("Fox News", "https://moxie.foxnews.com/google-publisher/politics.xml", "https://foxnews.com"),
    ("Fox News", "https://moxie.foxnews.com/google-publisher/world.xml", "https://foxnews.com"),
    # Al Jazeera
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "https://aljazeera.com"),
    # NPR — main + business
    ("NPR", "https://feeds.npr.org/1001/rss.xml", "https://npr.org"),
    ("NPR", "https://feeds.npr.org/1006/rss.xml", "https://npr.org"),
    # Reuters (may be flaky in some networks)
    ("Reuters", "https://feeds.reuters.com/reuters/topNews", "https://reuters.com"),
    ("Reuters", "https://feeds.reuters.com/reuters/businessNews", "https://reuters.com"),
    # Bloomberg (often blocks scrapers but keep it)
    ("Bloomberg", "https://feeds.bloomberg.com/markets/news.rss", "https://bloomberg.com"),
    # The Hindu — national + world + business
    ("The Hindu", "https://www.thehindu.com/news/national/feeder/default.rss", "https://thehindu.com"),
    ("The Hindu", "https://www.thehindu.com/news/international/feeder/default.rss", "https://thehindu.com"),
    ("The Hindu", "https://www.thehindu.com/business/feeder/default.rss", "https://thehindu.com"),
    # Times of India — top + world + business + tech
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms", "https://timesofindia.com"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/296589291.cms", "https://timesofindia.com"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/1898055.cms", "https://timesofindia.com"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/66949542.cms", "https://timesofindia.com"),
]

FRAME_LABELS = [
    "economic_impact",
    "political_conflict",
    "human_interest",
    "environmental",
    "public_health",
    "tech_innovation",
    "national_security",
    "corporate_profit",
    "social_justice",
    "legal_regulatory",
]
