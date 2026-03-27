from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .nlp_engine import NLPEngine


@dataclass
class ToolResult:
    name: str
    output: dict[str, Any]


class AgenticEngine:
    """Simple tool-using analytics agent for tweet analysis context."""

    def __init__(self, nlp_engine: NLPEngine) -> None:
        self.engine = nlp_engine

    def run(self, question: str, rows: list[dict]) -> dict[str, Any]:
        clean_question = (question or "").strip()
        if not clean_question:
            return {
                "answer": "Question is empty. Please ask a specific analytics question.",
                "plan": [],
                "steps": [],
                "confidence": "low",
            }

        summary = self.engine.aggregate(rows)
        if not summary.get("count"):
            return {
                "answer": "No analyzed rows available yet. First analyze URLs/handle, then ask the agent.",
                "plan": ["check_data"],
                "steps": [
                    {
                        "step": "check_data",
                        "status": "completed",
                        "observation": "Input row count is 0.",
                    }
                ],
                "confidence": "low",
            }

        plan = self._build_plan(clean_question)
        tool_results: list[ToolResult] = []
        step_trace: list[dict[str, str]] = []

        for step in plan:
            result = self._execute_step(step, rows)
            tool_results.append(result)
            step_trace.append(
                {
                    "step": step,
                    "status": "completed",
                    "observation": self._short_observation(result),
                }
            )

        answer = self._compose_answer(clean_question, tool_results)
        confidence = self._estimate_confidence(plan, rows)

        return {
            "answer": answer,
            "plan": plan,
            "steps": step_trace,
            "confidence": confidence,
            "tools": [
                {
                    "name": item.name,
                    "output": item.output,
                }
                for item in tool_results
            ],
        }

    def _build_plan(self, question: str) -> list[str]:
        q = question.lower()
        plan: list[str] = ["summary_snapshot"]

        if any(word in q for word in ["sentiment", "positive", "negative", "neutral"]):
            plan.append("sentiment_breakdown")
        if any(word in q for word in ["trend", "week", "monthly", "growth", "change"]):
            plan.append("trend_scan")
        if any(word in q for word in ["keyword", "topic", "theme"]):
            plan.append("keyword_scan")
        if any(word in q for word in ["best", "worst", "top", "perform", "engagement", "likes", "retweet", "views", "reply"]):
            plan.append("top_posts")

        if len(plan) == 1:
            plan.extend(["sentiment_breakdown", "top_posts"])

        return plan

    def _execute_step(self, step: str, rows: list[dict]) -> ToolResult:
        if step == "summary_snapshot":
            return ToolResult(step, self.engine.aggregate(rows))
        if step == "sentiment_breakdown":
            summary = self.engine.aggregate(rows)
            return ToolResult(
                step,
                {
                    "positive": summary.get("positive", 0),
                    "neutral": summary.get("neutral", 0),
                    "negative": summary.get("negative", 0),
                    "avg_sentiment_score": summary.get("avg_sentiment_score", 0),
                },
            )
        if step == "trend_scan":
            trends = self.engine.build_trends(rows)
            week = trends.get("week", [])
            if not week:
                return ToolResult(step, {"message": "Trend data not available"})
            return ToolResult(
                step,
                {
                    "first_day": week[0],
                    "last_day": week[-1],
                    "delta_likes": int(week[-1].get("likes", 0)) - int(week[0].get("likes", 0)),
                    "delta_views": int(week[-1].get("views", 0)) - int(week[0].get("views", 0)),
                },
            )
        if step == "keyword_scan":
            summary = self.engine.aggregate(rows)
            return ToolResult(step, {"top_keywords": summary.get("top_keywords", [])[:8]})
        if step == "top_posts":
            ranked = sorted(rows, key=lambda r: int(r.get("likes", 0) or 0), reverse=True)
            head = ranked[:3]
            compact = [
                {
                    "user": item.get("user", "unknown"),
                    "likes": int(item.get("likes", 0) or 0),
                    "retweets": int(item.get("retweets", 0) or 0),
                    "replies": int(item.get("replies", 0) or 0),
                    "views": int(item.get("views", 0) or 0),
                    "text": str(item.get("text", ""))[:180],
                }
                for item in head
            ]
            return ToolResult(step, {"top_posts": compact})
        return ToolResult(step, {"message": "Unknown step"})

    def _compose_answer(self, question: str, results: list[ToolResult]) -> str:
        lines: list[str] = ["Agentic analysis completed based on your question."]
        for result in results:
            if result.name == "summary_snapshot":
                out = result.output
                lines.append(
                    (
                        f"- Snapshot: {out.get('count', 0)} tweets, "
                        f"engagement rate {out.get('engagement_rate', 0)}%, "
                        f"likes {out.get('total_likes', 0)}, views {out.get('total_views', 0)}."
                    )
                )
            elif result.name == "sentiment_breakdown":
                out = result.output
                lines.append(
                    (
                        f"- Sentiment: +{out.get('positive', 0)} / "
                        f"={out.get('neutral', 0)} / -{out.get('negative', 0)}, "
                        f"avg score {out.get('avg_sentiment_score', 0)}."
                    )
                )
            elif result.name == "trend_scan":
                out = result.output
                if out.get("message"):
                    lines.append("- Trend: not enough timestamp data for a reliable trend.")
                else:
                    lines.append(
                        (
                            f"- 7-day delta: likes {out.get('delta_likes', 0)}, "
                            f"views {out.get('delta_views', 0)}."
                        )
                    )
            elif result.name == "keyword_scan":
                kws = result.output.get("top_keywords", [])
                lines.append(f"- Keywords: {', '.join(kws) if kws else 'not available' }.")
            elif result.name == "top_posts":
                posts = result.output.get("top_posts", [])
                if posts:
                    lines.append(
                        f"- Top post lead: @{posts[0].get('user', 'unknown')} with {posts[0].get('likes', 0)} likes."
                    )

        lines.append(f"- Query interpreted as: {question}")
        return "\n".join(lines)

    @staticmethod
    def _short_observation(result: ToolResult) -> str:
        if result.name == "summary_snapshot":
            return f"summary count={result.output.get('count', 0)}"
        if result.name == "sentiment_breakdown":
            return "computed positive/neutral/negative breakdown"
        if result.name == "trend_scan":
            return "computed weekly deltas"
        if result.name == "keyword_scan":
            return "extracted top keywords"
        if result.name == "top_posts":
            return "ranked highest-like posts"
        return "step executed"

    @staticmethod
    def _estimate_confidence(plan: list[str], rows: list[dict]) -> str:
        if not rows:
            return "low"
        if len(rows) < 3:
            return "medium"
        if "trend_scan" in plan and len(rows) < 7:
            return "medium"
        return "high"
