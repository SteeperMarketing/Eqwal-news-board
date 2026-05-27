#!/usr/bin/env python3
"""
Eqwal News Scraper
Fetches the latest articles from eqwalgroup.com/news and writes:
  - feed.json     (used by the display board)
  - feed.rss.xml  (standard RSS feed for TrilbyTV and other readers)
"""

import json
import urllib.request
from html.parser import HTMLParser
from datetime import datetime, timezone

NEWS_URL   = "https://eqwalgroup.com/news/"
JSON_FILE  = "feed.json"
RSS_FILE   = "feed.rss.xml"
MAX_ARTICLES = 12
FEED_TITLE   = "Eqwal Group News"
FEED_LINK    = "https://eqwalgroup.com/news/"
FEED_DESC    = "Latest news from Eqwal Group"

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
    def __init__(self):
        super().__init__()
        self.articles   = []
        self._in_link   = False
        self._current   = {}

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href", "")
        if tag == "a" and href.startswith("/news/") and href != "/news/" and len(href) > 7:
            self._in_link = True
            self._current = {
                "url":      "https://eqwalgroup.com" + href,
                "slug":     href.strip("/").split("/")[-1],
                "raw_text": []
            }

    def handle_data(self, data):
        if self._in_link:
            text = data.strip()
            if text:
                self._current["raw_text"].append(text)

    def handle_endtag(self, tag):
        if self._in_link and tag == "a":
            self._in_link = False
            raw = self._current.get("raw_text", [])
            content = [t for t in raw if len(t) > 8 and "Read article" not in t and "All articles" not in t and t != "All articles"]
            if content:
                title   = content[0]
                summary = content[1] if len(content) > 1 else title
                slug    = self._current["slug"]
                known   = [a["slug"] for a in self.articles]
                if slug not in known:
                    self.articles.append({
                        "slug":    slug,
                        "url":     self._current["url"],
                        "title":   title,
                        "summary": summary,
                    })
            self._current = {}

def infer_tag(title, summary):
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

def xml_escape(text):
    return (text
        .replace("&",  "&amp;")
        .replace("<",  "&lt;")
        .replace(">",  "&gt;")
        .replace('"',  "&quot;")
        .replace("'",  "&apos;"))

def build_rss(articles):
    now_rfc = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">',
        '  <channel>',
        f'    <title>{xml_escape(FEED_TITLE)}</title>',
        f'    <link>{FEED_LINK}</link>',
        f'    <description>{xml_escape(FEED_DESC)}</description>',
        f'    <lastBuildDate>{now_rfc}</lastBuildDate>',
        '    <language>en</language>',
    ]
    for art in articles:
        lines += [
            '    <item>',
            f'      <title>{xml_escape(art["title"])}</title>',
            f'      <link>{xml_escape(art["url"])}</link>',
            f'      <description>{xml_escape(art["summary"])}</description>',
            f'      <guid isPermaLink="true">{xml_escape(art["url"])}</guid>',
            f'      <category>{xml_escape(art["tag"])}</category>',
            f'      <media:content url="{xml_escape(art["img"])}" medium="image"/>',
            '    </item>',
        ]
    lines += ['  </channel>', '</rss>']
    return "\n".join(lines)

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
            "summary": art["summary"],
            "tag":     tag_label,
            "url":     art["url"],
            "img":     pick_image(img_cat, i),
        })

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)
    print(f"Written {len(feed)} articles to {JSON_FILE}")

    rss = build_rss(feed)
    with open(RSS_FILE, "w", encoding="utf-8") as f:
        f.write(rss)
    print(f"Written RSS feed to {RSS_FILE}")

    for a in feed:
        print(f"  [{a['tag']}] {a['title']}")

if __name__ == "__main__":
    build_feed()
