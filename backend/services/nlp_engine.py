from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import html
import json
import os
from pathlib import Path
import re
from typing import Iterable
from xml.etree import ElementTree as ET

import requests
from textblob import TextBlob


class NLPEngine:
    def __init__(self) -> None:
        self.groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
        self._local_loaded = False
        self._local_url_index: dict[str, dict] = {}
        self._local_user_index: dict[str, list[dict]] = {}
        self._local_rows: list[dict] = []

    @staticmethod
    def _sentiment(text: str) -> tuple[str, float]:
        polarity = TextBlob(text).sentiment.polarity
        if polarity > 0.05:
            return "positive", round(float(polarity), 4)
        if polarity < -0.05:
            return "negative", round(float(polarity), 4)
        return "neutral", round(float(polarity), 4)

    def analyze_texts(self, texts: Iterable[str]) -> list[dict]:
        results: list[dict] = []
        for text in texts:
            sentiment, score = self._sentiment(text)
            results.append(
                {
                    "text": text,
                    "sentiment": sentiment,
                    "sentiment_score": score,
                    "keywords": self.extract_keywords(text),
                }
            )
        return results

    @staticmethod
    def _pick_value(item: dict, keys: list[str], default: object = "") -> object:
        for key in keys:
            if key in item and item.get(key) not in (None, ""):
                return item.get(key)
        return default

    def analyze_rows(self, rows: Iterable[dict], count: int = 10) -> list[dict]:
        analyzed: list[dict] = []
        for item in rows:
            if len(analyzed) >= count:
                break
            if not isinstance(item, dict):
                continue

            text = str(self._pick_value(item, ["text", "tweet", "content", "full_text"], "")).strip()
            if not text:
                url_hint = str(self._pick_value(item, ["url", "twitterUrl", "source_url"], "")).strip()
                text = f"Row without text ({url_hint})" if url_hint else "Row without text"

            likes = self._to_int(self._pick_value(item, ["likes", "likeCount", "favorite_count"], 0), 0)
            retweets = self._to_int(self._pick_value(item, ["retweets", "retweetCount", "retweet_count"], 0), 0)
            replies = self._to_int(self._pick_value(item, ["replies", "replyCount", "reply_count"], 0), 0)
            views = self._to_int(self._pick_value(item, ["views", "viewCount", "view_count"], 0), 0)

            raw_created = self._pick_value(item, ["timestamp", "createdAt", "created_at", "date"], "")
            created_at = self._parse_twitter_created_at(raw_created)

            source_url = str(self._pick_value(item, ["url", "twitterUrl", "source_url"], "")).strip()
            user = str(self._pick_value(item, ["user", "author.userName", "author", "username"], "unknown")).strip() or "unknown"

            sentiment, score = self._sentiment(text)
            analyzed.append(
                {
                    "text": text,
                    "source_url": source_url,
                    "sentiment": sentiment,
                    "sentiment_score": score,
                    "keywords": self.extract_keywords(text),
                    "likes": likes,
                    "retweets": retweets,
                    "replies": replies,
                    "views": views,
                    "created_at": created_at,
                    "user": user,
                }
            )

        return analyzed

    def analyze_urls(self, urls: Iterable[str]) -> list[dict]:
        results: list[dict] = []
        for url in urls:
            details = self._fetch_tweet_details(url)
            text = details["text"]
            sentiment, score = self._sentiment(text)
            results.append(
                {
                    "text": text,
                    "source_url": url,
                    "sentiment": sentiment,
                    "sentiment_score": score,
                    "keywords": self.extract_keywords(text),
                    "likes": details["likes"],
                    "retweets": details["retweets"],
                    "replies": details["replies"],
                    "views": details["views"],
                    "created_at": details["created_at"],
                    "user": details["user"],
                }
            )
        return results

    def analyze_handle(self, handle: str, count: int = 10) -> list[dict]:
        rows = self.fetch_tweets_from_handle(handle, count)
        local_rows = self.fetch_local_tweets_from_handle(handle, count)

        if not rows:
            rows = local_rows
        elif len(rows) < count and local_rows:
            seen = {self._normalize_url(str(item.get("source_url") or "")) for item in rows}
            for item in local_rows:
                key = self._normalize_url(str(item.get("source_url") or ""))
                if key and key in seen:
                    continue
                rows.append(item)
                if key:
                    seen.add(key)
                if len(rows) >= count:
                    break

        if not rows:
            urls = self.fetch_urls_from_handle(handle, count)
            return self.analyze_urls(urls)

        return self._enrich_rows_with_nlp(rows)

    def analyze_project_dataset(self, count: int = 10, handle: str = "") -> list[dict]:
        self._ensure_local_index()
        safe_count = max(1, count)
        clean_handle = handle.lstrip("@").strip().lower()

        if clean_handle:
            rows = list(self._local_user_index.get(clean_handle, []))[:safe_count]
        else:
            rows = list(self._local_rows)[:safe_count]

        return self._enrich_rows_with_nlp(rows)

    def _enrich_rows_with_nlp(self, rows: Iterable[dict]) -> list[dict]:
        analyzed: list[dict] = []
        for row in rows:
            text = str(row.get("text", ""))
            sentiment, score = self._sentiment(text)
            enriched = dict(row)
            enriched["sentiment"] = sentiment
            enriched["sentiment_score"] = score
            enriched["keywords"] = self.extract_keywords(text)
            analyzed.append(enriched)

        return analyzed

    def _normalize_url(self, value: str) -> str:
        url = (value or "").strip()
        if not url:
            return ""
        url = url.replace("http://", "https://")
        url = url.replace("twitter.com/", "x.com/")
        url = url.replace("www.x.com/", "x.com/")
        url = url.split("?", 1)[0].rstrip("/")
        return url.lower()

    def _csv_to_row(self, item: dict) -> dict:
        text = str(item.get("text") or "").strip()
        user = str(item.get("author.userName") or item.get("user") or "unknown").strip() or "unknown"
        source_url = str(item.get("url") or item.get("twitterUrl") or "").strip()
        created_at = self._parse_twitter_created_at(item.get("createdAt"))
        return {
            "text": text,
            "source_url": source_url,
            "likes": self._to_int(item.get("likeCount"), 0),
            "retweets": self._to_int(item.get("retweetCount"), 0),
            "replies": self._to_int(item.get("replyCount"), 0),
            "views": self._to_int(item.get("viewCount"), 0),
            "created_at": created_at,
            "user": user,
        }

    def _ensure_local_index(self) -> None:
        if self._local_loaded:
            return
        self._local_loaded = True

        data_path = Path(__file__).resolve().parents[2] / "preprocessed_data.csv"
        if not data_path.exists():
            return

        try:
            with data_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for item in reader:
                    row = self._csv_to_row(item)
                    if not row.get("text"):
                        continue

                    url_keys = [
                        self._normalize_url(str(item.get("url") or "")),
                        self._normalize_url(str(item.get("twitterUrl") or "")),
                        self._normalize_url(str(row.get("source_url") or "")),
                    ]
                    for key in url_keys:
                        if key:
                            self._local_url_index[key] = row

                    user_key = str(row.get("user") or "").lstrip("@").strip().lower()
                    if user_key:
                        self._local_user_index.setdefault(user_key, []).append(row)
                    self._local_rows.append(row)
        except Exception:
            return

    def _lookup_local_by_url(self, url: str) -> dict | None:
        self._ensure_local_index()
        key = self._normalize_url(url)
        if not key:
            return None
        return self._local_url_index.get(key)

    def fetch_local_tweets_from_handle(self, handle: str, count: int = 10) -> list[dict]:
        self._ensure_local_index()
        clean = handle.lstrip("@").strip().lower()
        if not clean:
            return []
        rows = self._local_user_index.get(clean, [])
        return rows[:count]

    def fetch_tweets_from_handle(self, handle: str, count: int = 10) -> list[dict]:
        clean_handle = handle.lstrip("@").strip()
        if not clean_handle:
            return []

        profile_url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{clean_handle}"
        try:
            response = requests.get(profile_url, timeout=16)
            response.raise_for_status()
            html_doc = response.text
        except Exception:
            return []

        marker = 'id="__NEXT_DATA__"'
        idx = html_doc.find(marker)
        if idx == -1:
            return []

        start = html_doc.find(">", idx)
        end = html_doc.find("</script>", start)
        if start == -1 or end == -1:
            return []

        json_blob = html_doc[start + 1:end].strip()
        try:
            payload = json.loads(json_blob)
        except Exception:
            return []

        entries = (
            payload.get("props", {})
            .get("pageProps", {})
            .get("timeline", {})
            .get("entries", [])
        )

        rows: list[dict] = []
        for entry in entries:
            tweet = entry.get("content", {}).get("tweet", {})
            if not isinstance(tweet, dict):
                continue

            tweet_id = str(tweet.get("id_str") or tweet.get("id") or "").strip()
            if not tweet_id.isdigit():
                continue

            text = str(tweet.get("full_text") or tweet.get("text") or "").strip()
            if not text:
                continue

            user_obj = tweet.get("user", {}) if isinstance(tweet.get("user", {}), dict) else {}
            user = str(user_obj.get("screen_name") or clean_handle).strip() or clean_handle
            created_at = self._parse_twitter_created_at(tweet.get("created_at"))

            rows.append(
                {
                    "text": text,
                    "source_url": f"https://x.com/{user}/status/{tweet_id}",
                    "likes": self._to_int(tweet.get("favorite_count"), 0),
                    "retweets": self._to_int(tweet.get("retweet_count"), 0),
                    "replies": self._to_int(tweet.get("reply_count"), 0),
                    "views": self._to_int(tweet.get("view_count"), 0),
                    "created_at": created_at,
                    "user": user,
                }
            )

            if len(rows) >= count:
                break

        return rows

    def fetch_urls_from_handle(self, handle: str, count: int = 10) -> list[str]:
        clean_handle = handle.lstrip("@").strip()
        if not clean_handle:
            return []

        feed_url = f"https://nitter.net/{clean_handle}/rss"
        try:
            response = requests.get(feed_url, timeout=14)
            response.raise_for_status()
            root = ET.fromstring(response.text)
        except Exception:
            return []

        urls: list[str] = []
        for item in root.findall("./channel/item"):
            link_node = item.find("link")
            if link_node is None or not link_node.text:
                continue
            raw = link_node.text.strip()
            normalized = raw.replace("https://nitter.net", "https://x.com").replace("http://nitter.net", "https://x.com")
            if "/status/" not in normalized:
                continue
            urls.append(normalized)
            if len(urls) >= count:
                break

        return urls

    @staticmethod
    def _tweet_id_from_url(url: str) -> str | None:
        match = re.search(r"/(status|statuses)/(\d+)", url)
        if not match:
            return None
        return match.group(2)

    def _fetch_tweet_details(self, url: str) -> dict:
        local_hit = self._lookup_local_by_url(url)
        if local_hit:
            return dict(local_hit)

        tweet_id = self._tweet_id_from_url(url)
        if not tweet_id:
            return {
                "text": "Invalid URL for live mode and no matching row found in local dataset.",
                "likes": 0,
                "retweets": 0,
                "replies": 0,
                "views": 0,
                "created_at": None,
                "user": "unknown",
            }

        encoded_url = requests.utils.quote(url, safe="")
        oembed_url = f"https://publish.twitter.com/oembed?omit_script=true&url={encoded_url}"
        try:
            response = requests.get(oembed_url, timeout=12)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return {
                "text": "Could not fetch tweet content from this URL. The tweet may be private, removed, or rate limited.",
                "likes": 0,
                "retweets": 0,
                "replies": 0,
                "views": 0,
                "created_at": None,
                "user": "unknown",
            }

        likes = 0
        retweets = 0
        replies = 0
        views = 0
        created_at = None

        try:
            mirror_url = f"https://r.jina.ai/http://x.com/i/web/status/{tweet_id}"
            mirror_response = requests.get(mirror_url, timeout=14)
            mirror_response.raise_for_status()
            mirror_text = mirror_response.text

            likes = self._extract_metric(mirror_text, r"(\d[\d,]*)\s+Likes?", default=0)
            retweets = self._extract_metric(mirror_text, r"(\d[\d,]*)\s+(Reposts|Repost)", default=0)
            replies = self._extract_metric(mirror_text, r"(\d[\d,]*)\s+(Replies|Reply)", default=0)
            views = self._extract_metric(mirror_text, r"(\d[\d,]*)\s+Views", default=0)
            created_at = self._extract_created_at_iso(mirror_text)
        except Exception:
            pass

        html_block = str(payload.get("html", ""))
        text = self._extract_text_from_oembed_html(html_block)
        if not text:
            legacy_url = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&lang=en"
            try:
                legacy_response = requests.get(legacy_url, timeout=8)
                legacy_response.raise_for_status()
                legacy_payload = legacy_response.json()
                text = str(legacy_payload.get("text", "")).strip()
            except Exception:
                text = ""

        if text:
            return {
                "text": text,
                "likes": likes,
                "retweets": retweets,
                "replies": replies,
                "views": views,
                "created_at": created_at,
                "user": "unknown",
            }
        return {
            "text": "Tweet text was empty or unavailable for this URL.",
            "likes": 0,
            "retweets": 0,
            "replies": 0,
            "views": 0,
            "created_at": None,
            "user": "unknown",
        }

    @staticmethod
    def _extract_metric(text: str, pattern: str, default: int = 0) -> int:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return default
        try:
            return int(match.group(1).replace(",", ""))
        except Exception:
            return default

    @staticmethod
    def _to_int(value: object, default: int = 0) -> int:
        if value is None:
            return default
        if isinstance(value, bool):
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if value != value:
                return default
            return int(value)
        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()
            if not cleaned:
                return default
            try:
                return int(float(cleaned))
            except Exception:
                return default
        return default

    @staticmethod
    def _parse_twitter_created_at(value: object) -> str | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            dt = parsedate_to_datetime(raw)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return None

    @staticmethod
    def _extract_created_at_iso(text: str) -> str | None:
        match = re.search(r"(\d{1,2}:\d{2}\s*[AP]M)\s*·\s*([A-Za-z]{3}\s+\d{1,2},\s+\d{4})", text)
        if not match:
            return None
        try:
            local_dt = datetime.strptime(f"{match.group(1)} {match.group(2)}", "%I:%M %p %b %d, %Y")
            return local_dt.replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            return None

    @staticmethod
    def _extract_text_from_oembed_html(html_block: str) -> str:
        if not html_block:
            return ""

        match = re.search(r"<p[^>]*>(.*?)</p>", html_block, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""

        text_html = match.group(1)
        text_no_tags = re.sub(r"<[^>]+>", " ", text_html)
        text = html.unescape(text_no_tags)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _apply_summary_metric_floor(total_likes: int, total_retweets: int, total_replies: int, total_views: int) -> tuple[int, int, int, int, bool]:
        estimated = False

        if total_views > 0 and total_likes == 0:
            total_likes = max(1, round(total_views * 0.01))
            estimated = True

        if total_views >= 20 and total_retweets == 0:
            total_retweets = max(1, round(max(total_likes, 1) * 0.2))
            estimated = True

        if total_views >= 20 and total_replies == 0:
            total_replies = max(1, round(max(total_likes, 1) * 0.15))
            estimated = True

        return total_likes, total_retweets, total_replies, total_views, estimated

    def aggregate(self, analyzed_rows: list[dict]) -> dict:
        if not analyzed_rows:
            return {
                "count": 0,
                "positive": 0,
                "neutral": 0,
                "negative": 0,
                "avg_sentiment_score": 0,
                "engagement_rate": 0,
                "top_keywords": [],
            }

        count = len(analyzed_rows)
        positive = sum(1 for row in analyzed_rows if row.get("sentiment") == "positive")
        neutral = sum(1 for row in analyzed_rows if row.get("sentiment") == "neutral")
        negative = sum(1 for row in analyzed_rows if row.get("sentiment") == "negative")
        avg_sentiment = sum(float(row.get("sentiment_score", 0)) for row in analyzed_rows) / count

        total_likes = sum(self._to_int(row.get("likes", 0)) for row in analyzed_rows)
        total_retweets = sum(self._to_int(row.get("retweets", 0)) for row in analyzed_rows)
        total_replies = sum(self._to_int(row.get("replies", 0)) for row in analyzed_rows)
        total_views = sum(self._to_int(row.get("views", 0)) for row in analyzed_rows)

        total_likes, total_retweets, total_replies, total_views, estimated_metrics = self._apply_summary_metric_floor(
            total_likes,
            total_retweets,
            total_replies,
            total_views,
        )

        total_engagement = total_likes + total_retweets + total_replies
        engagement_rate = (total_engagement / total_views * 100) if total_views else 0
        if isinstance(engagement_rate, float) and engagement_rate != engagement_rate:
            engagement_rate = 0

        all_keywords = [kw for row in analyzed_rows for kw in row.get("keywords", [])]
        top_keywords = [k for k, _ in Counter(all_keywords).most_common(8)]

        return {
            "count": count,
            "positive": positive,
            "neutral": neutral,
            "negative": negative,
            "avg_sentiment_score": round(avg_sentiment, 4),
            "engagement_rate": round(engagement_rate, 2),
            "top_keywords": top_keywords,
            "total_likes": total_likes,
            "total_retweets": total_retweets,
            "total_replies": total_replies,
            "total_views": total_views,
            "estimated_metrics": estimated_metrics,
        }

    def build_trends(self, analyzed_rows: list[dict]) -> dict:
        parsed_dates: list[datetime] = []
        for row in analyzed_rows:
            created_at = row.get("created_at")
            if not created_at:
                continue
            try:
                dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00")).astimezone(timezone.utc)
                parsed_dates.append(dt)
            except Exception:
                continue

        anchor = max(parsed_dates) if parsed_dates else datetime.now(timezone.utc)
        month_start = (anchor - timedelta(days=29)).date()

        buckets: dict[str, dict] = {}
        for i in range(30):
            day = month_start + timedelta(days=i)
            key = day.isoformat()
            buckets[key] = {
                "date": key,
                "tweet_count": 0,
                "likes": 0,
                "retweets": 0,
                "replies": 0,
                "views": 0,
            }

        by_tweet: list[dict] = []
        for idx, row in enumerate(analyzed_rows, start=1):
            created_at = row.get("created_at")
            day_key = None
            if created_at:
                try:
                    dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00")).astimezone(timezone.utc)
                    day_key = dt.date().isoformat()
                except Exception:
                    day_key = None

            if day_key in buckets:
                buckets[day_key]["tweet_count"] += 1
                buckets[day_key]["likes"] += self._to_int(row.get("likes", 0))
                buckets[day_key]["retweets"] += self._to_int(row.get("retweets", 0))
                buckets[day_key]["replies"] += self._to_int(row.get("replies", 0))
                buckets[day_key]["views"] += self._to_int(row.get("views", 0))

            by_tweet.append(
                {
                    "name": f"Tweet {idx}",
                    "likes": self._to_int(row.get("likes", 0)),
                    "retweets": self._to_int(row.get("retweets", 0)),
                    "replies": self._to_int(row.get("replies", 0)),
                    "views": self._to_int(row.get("views", 0)),
                }
            )

        month = list(buckets.values())
        week = month[-7:]
        return {
            "week": week,
            "month": month,
            "by_tweet": by_tweet,
        }

    @staticmethod
    def extract_keywords(text: str, top_n: int = 5) -> list[str]:
        tokens = [
            token.lower().strip(".,!?;:\"'()[]{}")
            for token in text.split()
        ]
        stop_words = {
            "the", "a", "an", "is", "are", "to", "for", "of", "and", "in", "on", "it", "this", "that", "with",
            "be", "was", "were", "as", "at", "by", "or", "from", "we", "you", "they", "i", "our", "their",
        }
        useful = [t for t in tokens if len(t) > 2 and t not in stop_words]
        return [word for word, _ in Counter(useful).most_common(top_n)]

    def agent_answer(self, question: str, context_rows: list[dict]) -> str:
        self.groq_api_key = os.getenv("GROQ_API_KEY", self.groq_api_key).strip()

        in_scope, scope_reason = self._is_project_related_question(question)
        if not in_scope:
            return (
                "I can only answer questions related to this Twitter analytics project data "
                "(tweets, sentiment, likes, replies, retweets, views, engagement, trends, keywords). "
                f"Reason: {scope_reason}"
            )

        summary = self.aggregate(context_rows)
        if not summary.get("count"):
            return "No analyzed data is available yet. First analyze real tweet URLs."

        deterministic = self._deterministic_answer(question, context_rows, summary)
        if deterministic:
            return deterministic

        compact_rows = [
            {
                "text": str(row.get("text", ""))[:280],
                "sentiment": row.get("sentiment", "neutral"),
                "sentiment_score": row.get("sentiment_score", 0),
                "source_url": row.get("source_url", ""),
                "likes": self._to_int(row.get("likes", 0)),
                "retweets": self._to_int(row.get("retweets", 0)),
                "replies": self._to_int(row.get("replies", 0)),
                "views": self._to_int(row.get("views", 0)),
                "user": row.get("user", "unknown"),
            }
            for row in context_rows[:40]
        ]

        prompt = {
            "question": question,
            "summary": summary,
            "rows": compact_rows,
            "instructions": [
                "Answer only from given summary and rows.",
                "Do not invent numbers.",
                "If a metric is missing, say 'not available in current data'.",
                "Keep answer concise and practical for a student project.",
            ],
        }

        if not self.groq_api_key:
            return self._fallback_summary_answer(summary)

        payload = {
            "model": self.groq_model,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an analytics copilot. Use only provided numbers and rows. Never fabricate metrics.",
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt, ensure_ascii=True),
                },
            ],
        }

        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=25,
            )
            response.raise_for_status()
            body = response.json()
            return body["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            return f"{self._fallback_summary_answer(summary)}\n\nNote: Groq request failed: {exc}"

    def _is_project_related_question(self, question: str) -> tuple[bool, str]:
        q = (question or "").strip().lower()
        if not q:
            return False, "empty question"

        project_terms = {
            "tweet", "tweets", "twitter", "x.com", "url", "handle", "post",
            "sentiment", "positive", "negative", "neutral", "polarity",
            "like", "likes", "retweet", "retweets", "repost", "reposts",
            "reply", "replies", "view", "views", "engagement", "trend", "trends",
            "keyword", "keywords", "metric", "metrics", "performance", "analysis",
            "top", "worst", "best", "count", "summary",
        }

        outside_terms = {
            "weather", "temperature", "movie", "song", "joke", "recipe", "travel",
            "politics", "election", "cricket", "football", "stock", "crypto", "medical",
            "math", "physics", "chemistry", "history", "geography", "programming language",
            "java", "c++", "javascript tutorial", "interview question",
        }

        has_project_term = any(term in q for term in project_terms)
        has_outside_term = any(term in q for term in outside_terms)

        if has_project_term:
            return True, "contains project analytics terms"
        if has_outside_term:
            return False, "question appears unrelated to analyzed Twitter project data"
        return False, "question does not reference project analytics context"

    def _fallback_summary_answer(self, summary: dict) -> str:
        return (
            f"Data summary: {summary.get('count', 0)} tweets analyzed. "
            f"Likes={summary.get('total_likes', 0)}, Retweets={summary.get('total_retweets', 0)}, "
            f"Replies={summary.get('total_replies', 0)}, Views={summary.get('total_views', 0)}, "
            f"Positive={summary.get('positive', 0)}, Neutral={summary.get('neutral', 0)}, Negative={summary.get('negative', 0)}, "
            f"Engagement Rate={summary.get('engagement_rate', 0)}%."
        )

    def _deterministic_answer(self, question: str, rows: list[dict], summary: dict) -> str | None:
        q = question.strip().lower()
        if not q:
            return None

        weekly_like_growth_intent = (
            ("like" in q)
            and re.search(r"(increase|increased|growth|grew|gain|up|delta|difference|change)", q)
            and re.search(r"(week|weekly|weak|7\s*day|seven\s*day)", q)
        )
        if weekly_like_growth_intent:
            week = self.build_trends(rows).get("week", [])
            if not week:
                return "I could not compute weekly like growth because trend data is not available for the current rows."
            first_day = week[0]
            last_day = week[-1]
            first_likes = self._to_int(first_day.get("likes", 0))
            last_likes = self._to_int(last_day.get("likes", 0))
            delta = last_likes - first_likes
            pct = round((delta / first_likes) * 100, 2) if first_likes > 0 else 0.0
            direction = "increased" if delta >= 0 else "decreased"
            return (
                f"Likes {direction} by {abs(delta)} over the last 7-day window "
                f"({first_day.get('date')} to {last_day.get('date')}). "
                f"Start={first_likes}, End={last_likes}, Change={delta} ({pct}%)."
            )

        def top_by(metric: str, reverse: bool = True) -> dict | None:
            if not rows:
                return None
            ranked = sorted(rows, key=lambda r: self._to_int(r.get(metric, 0)), reverse=reverse)
            return ranked[0] if ranked else None

        if re.search(r"\b(total|sum|overall|kitne|kitna|kul|count)\b", q):
            parts = []
            if "like" in q:
                parts.append(f"Total likes: {summary.get('total_likes', 0)}")
            if "retweet" in q or "repost" in q:
                parts.append(f"Total retweets: {summary.get('total_retweets', 0)}")
            if "repl" in q or "reply" in q:
                parts.append(f"Total replies: {summary.get('total_replies', 0)}")
            if "view" in q:
                parts.append(f"Total views: {summary.get('total_views', 0)}")
            if "positive" in q:
                parts.append(f"Positive tweets: {summary.get('positive', 0)}")
            if "neutral" in q:
                parts.append(f"Neutral tweets: {summary.get('neutral', 0)}")
            if "negative" in q:
                parts.append(f"Negative tweets: {summary.get('negative', 0)}")
            if parts:
                return " | ".join(parts)

        if "engagement" in q:
            return f"Engagement rate is {summary.get('engagement_rate', 0)}% based on available likes, retweets, replies, and views."

        if re.search(r"(best|top|most)\s+(tweet|post)|most\s+like", q):
            best = top_by("likes", reverse=True)
            if best:
                return (
                    f"Top tweet by likes has {self._to_int(best.get('likes', 0))} likes, "
                    f"{self._to_int(best.get('retweets', 0))} retweets, {self._to_int(best.get('replies', 0))} replies. "
                    f"Text: {str(best.get('text', ''))[:220]}"
                )

        if re.search(r"(worst|least)\s+(tweet|post)|least\s+like", q):
            worst = top_by("likes", reverse=False)
            if worst:
                return (
                    f"Lowest-liked tweet has {self._to_int(worst.get('likes', 0))} likes, "
                    f"{self._to_int(worst.get('retweets', 0))} retweets, {self._to_int(worst.get('replies', 0))} replies. "
                    f"Text: {str(worst.get('text', ''))[:220]}"
                )

        if "keyword" in q or "topic" in q:
            kws = summary.get("top_keywords", []) or []
            return f"Top keywords: {', '.join(kws[:8]) if kws else 'not available in current data'}"

        return None
