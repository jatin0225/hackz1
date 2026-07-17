"""RSS feed catalogue."""

RSS_FEEDS = [
    ("Reuters", "https://feeds.reuters.com/reuters/topNews", "https://reuters.com"),
    ("BBC", "https://feeds.bbci.co.uk/news/rss.xml", "https://bbc.com"),
    ("Bloomberg", "https://feeds.bloomberg.com/markets/news.rss", "https://bloomberg.com"),
    ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html", "https://cnbc.com"),
    ("The Guardian", "https://www.theguardian.com/world/rss", "https://theguardian.com"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "https://aljazeera.com"),
    ("NPR", "https://feeds.npr.org/1001/rss.xml", "https://npr.org"),
    ("Fox News", "https://moxie.foxnews.com/google-publisher/latest.xml", "https://foxnews.com"),
    ("The Hindu", "https://www.thehindu.com/news/national/feeder/default.rss", "https://thehindu.com"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms", "https://timesofindia.com"),
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
