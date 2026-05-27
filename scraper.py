#!/usr/bin/env python3
"""
Eqwal News Scraper
Fetches the latest articles from eqwalgroup.com/news and writes feed.json
Run manually or via GitHub Actions on a schedule.
"""

import json
import re
import urllib.request
import urllib.error
from html.parser import HTMLParser

NEWS_URL = "https://eqwalgroup.com/news/"
OUTPUT_FILE = "feed.json"
MAX_ARTICLES = 12  # Keep the most recent 12 for cycling

# Fallback images by category (Unsplash, free to use)
CATEGORY_IMAGES = {
    "Acquisition": [
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=900&q=80",
        "https://images.unsplash.com/photo-1485546246426-74dc88dec4d9?w=900&q=80",
        "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=900&q=80",
        "https://images.unsplash.com/photo-1467269204594-9661b134dd2b?w=900&q=80",
    ],
    "Foundation": [
        "https://images.unsplash.com/photo-1594708767771-a5fc04dc3767?w=900&q=80",
        "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?w=900&q=80",
    ],
    "Training": [
        "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=900&q=80",
        "https://images.unsplash.com/photo-1551076805-e1869033e561?w=900&q=80",
    ],
    "News": [
        "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=900&q=80",
        "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=900&q=80",
    ],
}

# Map Eqwal tag names to display labels and image categories
TAG_MAP = {
    "eqwal foundation": ("Foundation", "Foundation"),
    "eqwal education":  ("Training",   "Training"),
    "eqwal impact":     ("Foundation", "Foundation"),
    "patient stories":  ("News",       "News"),
    "features technology": ("Technology", "News"),
    "eqwal":            ("News",       "News"),
}

def classify(raw_tags):
    """Return (display_tag, image_category) from raw tag strings."""
    for t in raw_tags:
        key = t.strip().lower()
        if key in TAG_MAP:
            return TAG_MAP[key]
    # Heuristic: if title contains acquisition keywords
    return ("Acquisition", "Acquisition")

def pick_image(category, index):
    pool = CATEGORY_IMAGES.get(category, CATEGORY_IMAGES["News"])
    return pool[index % len(pool)]

def fetch_html(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; EqwalNewsScraper/1.0)"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")

class NewsParser(HTMLParser):
    """Parse the Eqwal news page and extract article links + titles."""

    def __init__(self):
        super().__init__()
        self.articles = []
        self._in_article = False
        self._current = {}
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href", "")
        # Each article is a link under /news/ with a unique slug
        if tag == "a" and href.startswith("/news/") and href != "/news/" and len(href) > 7:
            self._in_article = True
            self._current = {
                "url": "https://eqwalgroup.com" + href,
                "slug": href.strip("/").split("/")[-1],
                "raw_text": []
            }

    def handle_data(self, data):
        if self._in_article:
            text = data.strip()
            if text:
                self._current["raw_text"].append(text)

    def handle_endtag(self, tag):
        if self._in_article and tag == "a":
            self._in_article = False
            raw = self._current.get("raw_text", [])
            # Filter: skip nav links and very short strings
            content = [t for t in raw if len(t) > 8 and "Read article" not in t]
            if content:
                title = content[0]
                summary = content[1] if len(content) > 1 else ""
                slug = self._current["slug"]
                # Skip duplicate slugs
                known = [a["slug"] for a in self.articles]
                if slug not in known:
                    self.articles.append({
                        "slug": slug,
                        "url": self._current["url"],
                        "title": title,
                        "summary": summary,
                    })
            self._current = {}

def infer_tag(title, summary):
    """Guess a display tag from the article text."""
    text = (title + " " + summary).lower()
    if any(w in text for w in ["acqui", "integrat", "joins eqwal", "join eqwal", "merger"]):
        return ("Acquisition", "Acquisition")
    if any(w in text for w in ["foundation", "humanitarian", "mission", "charity", "solidaire"]):
        return ("Foundation", "Foundation")
    if any(w in text for w in ["training", "education", "motion", "programme", "program"]):
        return ("Training", "Training")
    if any(w in text for w in ["director", "manager", "appoint", "welcome", "talent", "team"]):
        return ("People", "News")
    return ("News", "News")

def build_feed():
    print(f"Fetching {NEWS_URL} ...")
    html = fetch_html(NEWS_URL)

    parser = NewsParser()
    parser.feed(html)
    raw_articles = parser.articles[:MAX_ARTICLES]
    print(f"Found {len(raw_articles)} articles")

    feed = []
    for i, art in enumerate(raw_articles):
        tag_label, img_cat = infer_tag(art["title"], art["summary"])
        feed.append({
            "title":   art["title"],
            "summary": art["summary"] if art["summary"] else art["title"],
            "tag":     tag_label,
            "url":     art["url"],
            "img":     pick_image(img_cat, i),
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)

    print(f"Written {len(feed)} articles to {OUTPUT_FILE}")
    for a in feed:
        print(f"  [{a['tag']}] {a['title']}")

if __name__ == "__main__":
    build_feed()
