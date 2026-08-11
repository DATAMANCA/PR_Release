import feedparser
import requests

USER_AGENT = "newswire-watch/1.0 (contact: malithdisala@gmail.com)"

# All free, publicly accessible RSS/Atom feeds. No API keys required.
# Note: PRNewswire/GlobeNewswire feeds only expose their most recent ~20 items each -
# on a busy news day that window can turn over in well under 10 minutes, so polling
# needs to run frequently (every few minutes) to avoid missing releases entirely.
SOURCES = [
    {
        "name": "PRNewswire - All News",
        "url": "https://www.prnewswire.com/rss/news-releases-list.rss",
    },
    {
        "name": "PRNewswire - Financial Services",
        "url": "https://www.prnewswire.com/rss/financial-services-latest-news/financial-services-latest-news-list.rss",
    },
    {
        "name": "PRNewswire - Health",
        "url": "https://www.prnewswire.com/rss/health-latest-news/health-latest-news-list.rss",
    },
    {
        "name": "PRNewswire - Biotechnology",
        "url": "https://www.prnewswire.com/rss/biotechnology-latest-news/biotechnology-latest-news-list.rss",
    },
    {
        "name": "PRNewswire - Computer & Electronics",
        "url": "https://www.prnewswire.com/rss/computer-electronics-latest-news/computer-electronics-latest-news-list.rss",
    },
    {
        "name": "PRNewswire - Consumer Technology",
        "url": "https://www.prnewswire.com/rss/consumer-technology-latest-news/consumer-technology-latest-news-list.rss",
    },
    {
        "name": "GlobeNewswire - Public Companies",
        "url": "https://www.globenewswire.com/RssFeed/orgclass/1/feedTitle/GlobeNewswire%20-%20News%20by%20Public%20Companies",
    },
    {
        "name": "SEC EDGAR - 8-K Filings (material events)",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&company=&dateb=&owner=include&count=100&output=atom",
    },
]


def fetch_all():
    """Fetch every source feed and return a flat list of normalized entries."""
    items = []
    for src in SOURCES:
        try:
            resp = requests.get(src["url"], headers={"User-Agent": USER_AGENT}, timeout=30)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            if not parsed.entries:
                print(f"[warn] {src['name']} returned 0 entries (transient/empty response)")
            for entry in parsed.entries:
                item_id = entry.get("id") or entry.get("link")
                if not item_id:
                    continue
                items.append(
                    {
                        "source": src["name"],
                        "id": item_id,
                        "title": entry.get("title", "").strip(),
                        "summary": entry.get("summary", ""),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", entry.get("updated", "")),
                    }
                )
        except Exception as e:
            print(f"[warn] failed to fetch {src['name']}: {e}")
    return items
