import json
import anthropic
from rich.console import Console
from rich.markdown import Markdown

console = Console()

MODEL = "claude-opus-4-6"

CAMPAIGN_PROMPT = """\
You are an expert email marketing analyst with deep knowledge of campaign optimization, \
audience segmentation, and performance benchmarking.

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
You are an expert email marketing strategist. Analyze the performance of a group of \
email campaigns and identify patterns, trends, and strategic recommendations.

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


def _safe_serialize(obj: object) -> str:
    def default(o: object) -> str:
        return str(o)
    return json.dumps(obj, indent=2, default=default)


class InsightsGenerator:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

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

    def _stream_insight(self, prompt: str, label: str) -> str:
        full_text = ""
        console.print(f"  [dim]Streaming insights for {label}...[/dim]")

        with self.client.messages.stream(
            model=MODEL,
            max_tokens=2048,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for event in stream:
                if (
                    event.type == "content_block_delta"
                    and event.delta.type == "text_delta"
                ):
                    full_text += event.delta.text

        return full_text.strip()
