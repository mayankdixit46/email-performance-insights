import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

console = Console()


def _safe_serialize(obj: object) -> object:
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_serialize(i) for i in obj]
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


class ReportGenerator:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def generate_report(self, all_insights: dict[str, Any]) -> None:
        self._print_to_console(all_insights)
        self._save_markdown(all_insights)
        self._save_json(all_insights)

    def _print_to_console(self, all_insights: dict[str, Any]) -> None:
        console.print("\n")
        console.print(
            Panel(
                "[bold white]Email Performance Insight Report[/bold white]",
                style="bold blue",
            )
        )

        if "campaigns" in all_insights:
            console.print("\n[bold yellow]── Per-Campaign Insights ──[/bold yellow]")
            for cid, data in all_insights["campaigns"].items():
                console.print(
                    Panel(
                        Markdown(data["insight"]),
                        title=f"[cyan]{data['campaign']['campaign_name']}[/cyan]",
                        border_style="dim",
                    )
                )
                self._print_metrics_table(data["stats"], data["campaign"]["campaign_name"])

        if "groups" in all_insights:
            console.print("\n[bold yellow]── Group-Level Insights ──[/bold yellow]")
            for group_name, data in all_insights["groups"].items():
                console.print(
                    Panel(
                        Markdown(data["insight"]),
                        title=f"[magenta]Group: {group_name}[/magenta]",
                        border_style="dim",
                    )
                )

    def _print_metrics_table(self, stats: dict, title: str) -> None:
        table = Table(title=f"Metrics — {title}", show_header=True, header_style="bold")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        table.add_column("Benchmark", justify="right")
        table.add_column("vs Benchmark", justify="right")

        rate_metrics = [
            "open_rate", "click_rate", "click_to_open_rate",
            "conversion_rate", "bounce_rate", "unsubscribe_rate",
        ]
        for metric in rate_metrics:
            if metric in stats and isinstance(stats[metric], dict):
                m = stats[metric]
                diff = m["vs_benchmark"]
                color = "green" if (
                    (metric not in ("bounce_rate", "unsubscribe_rate") and diff >= 0)
                    or (metric in ("bounce_rate", "unsubscribe_rate") and diff <= 0)
                ) else "red"
                table.add_row(
                    metric.replace("_", " ").title(),
                    f"{m['value']}%",
                    f"{m['benchmark']}%",
                    f"[{color}]{'+' if diff > 0 else ''}{diff}%[/{color}]",
                )
        console.print(table)

    def _save_markdown(self, all_insights: dict[str, Any]) -> None:
        lines = [
            "# Email Performance Insight Report",
            f"\n_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n",
            "---\n",
        ]

        if "campaigns" in all_insights:
            lines.append("## Per-Campaign Insights\n")
            for _, data in all_insights["campaigns"].items():
                lines.append(data["insight"])
                lines.append("\n---\n")

        if "groups" in all_insights:
            lines.append("## Group-Level Insights\n")
            for _, data in all_insights["groups"].items():
                lines.append(data["insight"])
                lines.append("\n---\n")

        md_path = self.output_dir / f"insight_report_{self.timestamp}.md"
        md_path.write_text("\n".join(lines), encoding="utf-8")
        console.print(f"[green]Markdown report saved:[/green] {md_path}")

    def _save_json(self, all_insights: dict[str, Any]) -> None:
        safe = _safe_serialize(all_insights)
        json_path = self.output_dir / f"insight_report_{self.timestamp}.json"
        json_path.write_text(json.dumps(safe, indent=2), encoding="utf-8")
        console.print(f"[green]JSON report saved:[/green]     {json_path}")
