import pandas as pd
from typing import Any

# Industry benchmark averages (email marketing 2024)
BENCHMARKS = {
    "open_rate": 21.5,
    "click_rate": 2.3,
    "click_to_open_rate": 10.5,
    "conversion_rate": 3.5,
    "bounce_rate": 0.7,
    "unsubscribe_rate": 0.1,
}


class CampaignAnalyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def get_campaign_stats(self, campaign: pd.Series) -> dict[str, Any]:
        row = campaign.to_dict() if isinstance(campaign, pd.Series) else campaign
        stats: dict[str, Any] = {}

        for metric, benchmark in BENCHMARKS.items():
            value = float(row.get(metric, 0))
            diff = round(value - benchmark, 2)
            stats[metric] = {
                "value": value,
                "benchmark": benchmark,
                "vs_benchmark": diff,
                "status": "above" if diff > 0 else "below" if diff < 0 else "at",
            }

        stats["revenue_generated"] = float(row.get("revenue_generated", 0))
        stats["total_sent"] = int(row.get("total_sent", 0))
        stats["total_converted"] = int(row.get("total_converted", 0))

        if stats["revenue_generated"] > 0 and stats["total_sent"] > 0:
            stats["revenue_per_email"] = round(
                stats["revenue_generated"] / stats["total_sent"], 4
            )
        else:
            stats["revenue_per_email"] = 0.0

        return stats

    def get_groups(self, group_by: str) -> list[tuple[str, pd.DataFrame]]:
        if group_by not in self.df.columns:
            raise ValueError(f"Column '{group_by}' not found in data")
        return list(self.df.groupby(group_by))

    def get_group_stats(self, group_df: pd.DataFrame) -> dict[str, Any]:
        stats: dict[str, Any] = {}

        for metric, benchmark in BENCHMARKS.items():
            if metric in group_df.columns:
                avg_value = round(float(group_df[metric].mean()), 2)
                max_value = round(float(group_df[metric].max()), 2)
                min_value = round(float(group_df[metric].min()), 2)
                diff = round(avg_value - benchmark, 2)
                stats[metric] = {
                    "avg": avg_value,
                    "max": max_value,
                    "min": min_value,
                    "benchmark": benchmark,
                    "vs_benchmark": diff,
                    "status": "above" if diff > 0 else "below" if diff < 0 else "at",
                }

        stats["total_campaigns"] = len(group_df)
        stats["total_sent"] = int(group_df["total_sent"].sum())
        stats["total_revenue"] = round(float(group_df["revenue_generated"].sum()), 2)
        stats["total_converted"] = int(group_df["total_converted"].sum())

        top_idx = group_df["open_rate"].idxmax()
        stats["best_open_rate_campaign"] = group_df.loc[top_idx, "campaign_name"]

        if "click_rate" in group_df.columns:
            top_click_idx = group_df["click_rate"].idxmax()
            stats["best_click_rate_campaign"] = group_df.loc[top_click_idx, "campaign_name"]

        return stats

    def get_overall_summary(self) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "total_campaigns": len(self.df),
            "total_sent": int(self.df["total_sent"].sum()),
            "total_revenue": round(float(self.df["revenue_generated"].sum()), 2),
            "date_range": {
                "start": str(self.df["send_date"].min().date()),
                "end": str(self.df["send_date"].max().date()),
            },
        }
        for metric in BENCHMARKS:
            if metric in self.df.columns:
                summary[f"avg_{metric}"] = round(float(self.df[metric].mean()), 2)
        return summary
