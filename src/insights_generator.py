import json
import time
import anthropic
from rich.console import Console
from rich.markdown import Markdown

console = Console()

MODEL = "claude-opus-4-6"

# ── Cached system prompt ──────────────────────────────────────────────────────
# This block is sent with cache_control so the API can reuse it across all calls
# within a session (5-min TTL), saving input-token cost on every subsequent call.
SYSTEM_PROMPT = (
    "You are an expert email marketing analyst and strategist with deep knowledge of "
    "campaign optimisation, audience segmentation, A/B testing, deliverability, and "
    "performance benchmarking. You are precise, data-driven, and always tie your "
    "recommendations to specific numbers from the data provided."
)

# ── Per-entity user prompts ───────────────────────────────────────────────────
CAMPAIGN_PROMPT = """\
Analyze the following individual email campaign and provide structured, data-driven insights.

## Campaign Details
{campaign_json}

## Performance Statistics (with industry benchmarks)
{stats_json}

Provide your analysis in this exact format:

---

## Campaign: {campaign_name}

### Performance Overview
[2-3 sentences summarizing overall campaign performance and its business impact]

### ✅ What Worked
- [Specific success #1 with supporting data]
- [Specific success #2 with supporting data]
- [Specific success #3 with supporting data]

### ❌ What Didn't Work
- [Specific underperformance #1 with supporting data]
- [Specific underperformance #2 with supporting data]
- [Specific underperformance #3 with supporting data]

### 🎯 What to Optimize Next
1. [Highest-priority actionable recommendation with expected impact]
2. [Second recommendation with rationale]
3. [Third recommendation with rationale]

### Key Takeaway
[One sentence — the single most important insight from this campaign]

---
"""

GROUP_PROMPT = """\
Analyze the performance of a group of email campaigns and identify patterns, trends, and \
strategic recommendations.

## Group: {group_name}
## Campaigns in this group ({count} campaigns)
{campaigns_json}

## Aggregate Statistics (with industry benchmarks)
{stats_json}

Provide your analysis in this exact format:

---

## Group Analysis: {group_name}

### Group Performance Overview
[3-4 sentences summarizing the overall performance of this campaign group, key trends, \
and business significance]

### ✅ What Worked Across This Group
- [Pattern or strength #1 with data evidence]
- [Pattern or strength #2 with data evidence]
- [Pattern or strength #3 with data evidence]

### ❌ What Didn't Work Across This Group
- [Consistent underperformance or challenge #1 with data]
- [Consistent underperformance or challenge #2 with data]
- [Consistent underperformance or challenge #3 with data]

### 🎯 What to Optimize Next for This Group
1. [Strategic recommendation #1 — highest impact]
2. [Strategic recommendation #2 with rationale]
3. [Strategic recommendation #3 with rationale]

### Standout Campaigns
- **Best performer:** [Campaign name and why]
- **Needs most attention:** [Campaign name and why]

### Group-Level Takeaway
[One sentence — the single most important strategic insight for this campaign group]

---
"""

EXECUTIVE_SUMMARY_PROMPT = """\
You are presenting a portfolio-level email performance review to the C-suite.

## Overall Portfolio Statistics
{summary_json}

## All Campaigns (summary)
{campaigns_json}

Write a concise executive summary in this exact format:

---

## Executive Summary

### Portfolio Health
[2-3 sentences on overall portfolio performance vs industry benchmarks]

### Top Performers
- [Best campaign name + the metric that stands out and by how much]
- [Second-best campaign name + standout metric]

### Campaigns Needing Attention
- [Underperforming campaign name + the most critical issue with data]
- [Second underperformer + issue]

### Strategic Recommendations for Next Quarter
1. [Recommendation with expected impact]
2. [Recommendation with rationale]
3. [Recommendation with rationale]

### Portfolio Verdict
[One sentence — the single most important strategic conclusion]

---
"""

AB_COMPARISON_PROMPT = """\
Compare these two email campaigns head-to-head and explain what drove the differences \
in their performance.

## Campaign A: {name_a}
{campaign_a_json}
Stats: {stats_a_json}

## Campaign B: {name_b}
{campaign_b_json}
Stats: {stats_b_json}

Provide your comparison in this exact format:

---

## A/B Comparison: {name_a} vs {name_b}

### Head-to-Head Summary
[2-3 sentences summarising which campaign performed better overall and the most significant differences]

### Key Metric Differences
| Metric | {name_a} | {name_b} | Winner |
|--------|----------|----------|--------|
[Fill in open_rate, click_rate, conversion_rate, bounce_rate, unsubscribe_rate, revenue_generated]

### Why {name_a} Performed Differently
- [Root cause #1 with supporting data]
- [Root cause #2]

### Why {name_b} Performed Differently
- [Root cause #1 with supporting data]
- [Root cause #2]

### What to Replicate
[The single most impactful element from the better-performing campaign to carry forward]

### What to Fix
[The single most important issue to address in the underperformer]

---
"""


def _safe_serialize(obj: object) -> str:
    def default(o: object) -> str:
        return str(o)
    return json.dumps(obj, indent=2, default=default)


def _system_block() -> list[dict]:
    """Return the cached system prompt as an Anthropic content block."""
    return [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]


class InsightsGenerator:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    # ── Streaming helpers ─────────────────────────────────────────────────────

    def _stream_insight(self, user_prompt: str, label: str) -> str:
        full_text = ""
        console.print(f"  [dim]Streaming insights for {label}...[/dim]")

        with self.client.messages.stream(
            model=MODEL,
            max_tokens=2048,
            system=_system_block(),
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for event in stream:
                if (
                    event.type == "content_block_delta"
                    and event.delta.type == "text_delta"
                ):
                    full_text += event.delta.text

        return full_text.strip()

    # ── Per-entity insight generation ─────────────────────────────────────────

    def generate_campaign_insight(self, campaign: dict, stats: dict) -> str:
        prompt = CAMPAIGN_PROMPT.format(
            campaign_name=campaign.get("campaign_name", "Unknown"),
            campaign_json=_safe_serialize(campaign),
            stats_json=_safe_serialize(stats),
        )
        return self._stream_insight(prompt, label=campaign.get("campaign_name", "campaign"))

    def generate_group_insight(
        self, group_name: str, campaigns: list[dict], stats: dict
    ) -> str:
        prompt = GROUP_PROMPT.format(
            group_name=group_name,
            count=len(campaigns),
            campaigns_json=_safe_serialize(campaigns),
            stats_json=_safe_serialize(stats),
        )
        return self._stream_insight(prompt, label=f"group: {group_name}")

    def generate_executive_summary(
        self, overall_summary: dict, all_campaigns: list[dict]
    ) -> str:
        # Compact campaign list for the prompt (just names + key rates)
        compact = [
            {
                "campaign_name": c.get("campaign_name"),
                "campaign_type": c.get("campaign_type"),
                "open_rate": c.get("open_rate"),
                "click_rate": c.get("click_rate"),
                "conversion_rate": c.get("conversion_rate"),
                "revenue_generated": c.get("revenue_generated"),
            }
            for c in all_campaigns
        ]
        prompt = EXECUTIVE_SUMMARY_PROMPT.format(
            summary_json=_safe_serialize(overall_summary),
            campaigns_json=_safe_serialize(compact),
        )
        return self._stream_insight(prompt, label="executive summary")

    def generate_ab_comparison(
        self,
        campaign_a: dict,
        stats_a: dict,
        campaign_b: dict,
        stats_b: dict,
    ) -> str:
        name_a = campaign_a.get("campaign_name", "Campaign A")
        name_b = campaign_b.get("campaign_name", "Campaign B")
        prompt = AB_COMPARISON_PROMPT.format(
            name_a=name_a,
            name_b=name_b,
            campaign_a_json=_safe_serialize(campaign_a),
            stats_a_json=_safe_serialize(stats_a),
            campaign_b_json=_safe_serialize(campaign_b),
            stats_b_json=_safe_serialize(stats_b),
        )
        return self._stream_insight(prompt, label=f"A/B: {name_a} vs {name_b}")

    # ── Batch API ─────────────────────────────────────────────────────────────

    def submit_batch(self, campaigns: list[dict], stats_map: dict) -> str:
        """
        Submit all campaigns to the Anthropic Batches API.
        Returns the batch_id for later retrieval.
        stats_map: {campaign_id: stats_dict}
        """
        requests = []
        for c in campaigns:
            cid = str(c.get("campaign_id", c.get("campaign_name")))
            stats = stats_map.get(cid, {})
            prompt = CAMPAIGN_PROMPT.format(
                campaign_name=c.get("campaign_name", "Unknown"),
                campaign_json=_safe_serialize(c),
                stats_json=_safe_serialize(stats),
            )
            requests.append(
                anthropic.types.message_create_params.MessageCreateParamsNonStreaming(
                    custom_id=cid,
                    params={
                        "model": MODEL,
                        "max_tokens": 2048,
                        "system": _system_block(),
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
            )

        batch = self.client.messages.batches.create(requests=requests)
        console.print(f"[cyan]Batch submitted:[/cyan] {batch.id}  ({len(requests)} requests)")
        return batch.id

    def get_batch_status(self, batch_id: str) -> dict:
        """Return processing_status and request counts for a batch."""
        batch = self.client.messages.batches.retrieve(batch_id)
        return {
            "id": batch.id,
            "status": batch.processing_status,
            "request_counts": batch.request_counts.model_dump()
            if hasattr(batch.request_counts, "model_dump")
            else dict(batch.request_counts),
            "ended_at": str(batch.ended_at) if batch.ended_at else None,
        }

    def retrieve_batch_results(self, batch_id: str) -> dict[str, str]:
        """
        Retrieve completed batch results.
        Returns {custom_id: insight_text} for succeeded requests.
        """
        results: dict[str, str] = {}
        for result in self.client.messages.batches.results(batch_id):
            if result.result.type == "succeeded":
                text = ""
                for block in result.result.message.content:
                    if hasattr(block, "text"):
                        text += block.text
                results[result.custom_id] = text.strip()
            else:
                error_type = getattr(result.result, "error", {})
                results[result.custom_id] = f"[Error: {error_type}]"
        return results
