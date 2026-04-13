#!/usr/bin/env python3
"""
GenAI-Powered Email Performance Insight Generator
Analyzes historical email campaign data and generates actionable insights
using Claude AI (claude-opus-4-6 with adaptive thinking).
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

load_dotenv()

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GenAI-Powered Email Performance Insight Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --data data/my_campaigns.csv --mode campaigns
  python main.py --mode groups --group-by segment
  python main.py --output-dir reports/
        """,
    )
    parser.add_argument(
        "--data",
        type=str,
        default="data/sample_campaigns.csv",
        help="Path to campaign data CSV file (default: data/sample_campaigns.csv)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory to save reports (default: output/)",
    )
    parser.add_argument(
        "--mode",
        choices=["all", "campaigns", "groups"],
        default="all",
        help="Analysis mode: all, campaigns only, or groups only (default: all)",
    )
    parser.add_argument(
        "--group-by",
        choices=["campaign_type", "segment"],
        default="campaign_type",
        help="Field to group campaigns by (default: campaign_type)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY environment variable not set.[/red]")
        console.print("Copy .env.example to .env and add your key, or run:")
        console.print("  export ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    console.print(
        Panel(
            Text.assemble(
                ("GenAI-Powered Email Performance Insights\n", "bold blue"),
                ("Powered by Claude Opus 4.6 with Adaptive Thinking", "dim"),
            ),
            padding=(1, 4),
        )
    )

    # Lazy imports after validation
    from src.data_loader import load_campaign_data
    from src.analyzer import CampaignAnalyzer
    from src.insights_generator import InsightsGenerator
    from src.report import ReportGenerator

    # Load data
    console.print(f"\n[cyan]Loading data:[/cyan] {args.data}")
    df = load_campaign_data(args.data)
    console.print(f"[green]Loaded {len(df)} campaigns[/green]")

    analyzer = CampaignAnalyzer(df)
    insights_gen = InsightsGenerator(api_key=api_key)
    report_gen = ReportGenerator(output_dir=args.output_dir)

    all_insights: dict = {}

    if args.mode in ("all", "campaigns"):
        console.print("\n[bold yellow]Analyzing individual campaigns...[/bold yellow]")
        campaign_insights = {}
        for _, row in df.iterrows():
            name = row["campaign_name"]
            console.print(f"  [cyan]→[/cyan] {name}")
            stats = analyzer.get_campaign_stats(row)
            insight = insights_gen.generate_campaign_insight(row.to_dict(), stats)
            campaign_insights[row["campaign_id"]] = {
                "campaign": row.to_dict(),
                "stats": stats,
                "insight": insight,
            }
        all_insights["campaigns"] = campaign_insights

    if args.mode in ("all", "groups"):
        console.print(
            f"\n[bold yellow]Analyzing groups by '{args.group_by}'...[/bold yellow]"
        )
        group_insights = {}
        for group_name, group_df in analyzer.get_groups(args.group_by):
            console.print(f"  [magenta]→[/magenta] {group_name}")
            stats = analyzer.get_group_stats(group_df)
            insight = insights_gen.generate_group_insight(
                str(group_name),
                group_df.to_dict(orient="records"),
                stats,
            )
            group_insights[str(group_name)] = {
                "group_by": args.group_by,
                "campaigns": group_df.to_dict(orient="records"),
                "stats": stats,
                "insight": insight,
            }
        all_insights["groups"] = group_insights

    console.print("\n[bold green]Generating reports...[/bold green]")
    report_gen.generate_report(all_insights)
    console.print(f"\n[bold green]Done![/bold green] Reports saved to [cyan]{args.output_dir}/[/cyan]")


if __name__ == "__main__":
    main()
