import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .analyzer import BENCHMARKS

RATE_METRICS = [
    "open_rate", "click_rate", "click_to_open_rate",
    "conversion_rate", "bounce_rate", "unsubscribe_rate",
]
POSITIVE_METRICS = ["open_rate", "click_rate", "click_to_open_rate", "conversion_rate"]


def benchmark_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """Grouped bar chart: campaign averages vs industry benchmarks for key metrics."""
    metrics = [m for m in POSITIVE_METRICS if m in df.columns]
    rows = []
    for m in metrics:
        label = m.replace("_", " ").title()
        rows.append({"Metric": label, "Value": round(float(df[m].mean()), 2), "Type": "Your Campaigns (avg)"})
        rows.append({"Metric": label, "Value": BENCHMARKS[m], "Type": "Industry Benchmark"})

    bench_df = pd.DataFrame(rows)
    fig = px.bar(
        bench_df,
        x="Metric",
        y="Value",
        color="Type",
        barmode="group",
        title="Campaign Averages vs Industry Benchmarks",
        color_discrete_map={
            "Your Campaigns (avg)": "#636EFA",
            "Industry Benchmark": "#EF553B",
        },
        text="Value",
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(yaxis_title="Rate (%)", legend_title="", uniformtext_minsize=8)
    return fig


def trend_chart(df: pd.DataFrame, metric: str) -> go.Figure:
    """Line chart: a given metric plotted chronologically by send_date."""
    sorted_df = df.sort_values("send_date").copy()
    benchmark = BENCHMARKS.get(metric)
    label = metric.replace("_", " ").title()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sorted_df["send_date"],
        y=sorted_df[metric].astype(float),
        mode="lines+markers",
        name=label,
        text=sorted_df["campaign_name"],
        hovertemplate="<b>%{text}</b><br>%{x|%b %d, %Y}<br>" + label + ": %{y:.2f}%<extra></extra>",
        line=dict(width=2),
        marker=dict(size=7),
    ))

    if benchmark is not None:
        fig.add_hline(
            y=benchmark,
            line_dash="dash",
            line_color="red",
            opacity=0.6,
            annotation_text=f"Benchmark {benchmark}%",
            annotation_position="bottom right",
        )

    fig.update_layout(
        title=f"{label} Over Time",
        xaxis_title="Send Date",
        yaxis_title="Rate (%)",
    )
    return fig


def campaign_radar(df: pd.DataFrame, campaign_names: list[str]) -> go.Figure:
    """Radar/spider chart comparing up to 4 campaigns across key metrics + benchmark."""
    metrics = [m for m in POSITIVE_METRICS if m in df.columns]
    labels = [m.replace("_", " ").title() for m in metrics]
    closed_labels = labels + [labels[0]]

    fig = go.Figure()

    for name in campaign_names[:4]:
        row = df[df["campaign_name"] == name]
        if row.empty:
            continue
        values = [float(row[m].iloc[0]) for m in metrics]
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=closed_labels,
            fill="toself",
            name=name,
            opacity=0.75,
        ))

    bench_values = [BENCHMARKS[m] for m in metrics]
    fig.add_trace(go.Scatterpolar(
        r=bench_values + [bench_values[0]],
        theta=closed_labels,
        fill="toself",
        name="Industry Benchmark",
        line=dict(dash="dash", color="red"),
        fillcolor="rgba(255,0,0,0.05)",
    ))

    fig.update_layout(
        title="Campaign Comparison Radar",
        polar=dict(radialaxis=dict(visible=True, range=[0, max(
            max(float(df[m].max()) for m in metrics),
            max(BENCHMARKS[m] for m in metrics),
        ) * 1.15])),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
    )
    return fig


def revenue_chart(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart: revenue per campaign, sorted descending."""
    sorted_df = df.sort_values("revenue_generated", ascending=True)
    fig = px.bar(
        sorted_df,
        x="revenue_generated",
        y="campaign_name",
        orientation="h",
        title="Revenue by Campaign",
        color="revenue_generated",
        color_continuous_scale="Blues",
        labels={"revenue_generated": "Revenue ($)", "campaign_name": ""},
        text="revenue_generated",
    )
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig.update_layout(coloraxis_showscale=False, margin=dict(l=10))
    return fig


def metric_heatmap(df: pd.DataFrame) -> go.Figure:
    """Heatmap of all rate metrics across campaigns (actual values, colour-coded by normalised score)."""
    metrics = [m for m in RATE_METRICS if m in df.columns]
    sorted_df = df.sort_values("open_rate", ascending=False).reset_index(drop=True)

    z_raw = [[float(sorted_df[m].iloc[j]) for j in range(len(sorted_df))] for m in metrics]

    # Normalise per row (metric) for colouring; invert for negative metrics
    z_norm = []
    for i, m in enumerate(metrics):
        row_vals = z_raw[i]
        lo, hi = min(row_vals), max(row_vals)
        span = hi - lo if hi != lo else 1
        normed = [(v - lo) / span for v in row_vals]
        if m in ("bounce_rate", "unsubscribe_rate"):
            normed = [1 - v for v in normed]
        z_norm.append(normed)

    text_vals = [[f"{z_raw[i][j]:.1f}%" for j in range(len(sorted_df))] for i in range(len(metrics))]

    fig = go.Figure(data=go.Heatmap(
        z=z_norm,
        x=sorted_df["campaign_name"].tolist(),
        y=[m.replace("_", " ").title() for m in metrics],
        colorscale="RdYlGn",
        text=text_vals,
        texttemplate="%{text}",
        showscale=False,
        hoverongaps=False,
    ))
    fig.update_layout(
        title="Campaign Metrics Heatmap (green = better)",
        xaxis_tickangle=-40,
        height=320,
        margin=dict(b=120),
    )
    return fig


def ab_comparison_chart(df: pd.DataFrame, campaign_a: str, campaign_b: str) -> go.Figure:
    """Side-by-side grouped bar chart comparing two campaigns across all metrics."""
    metrics = [m for m in RATE_METRICS if m in df.columns]
    labels = [m.replace("_", " ").title() for m in metrics]

    row_a = df[df["campaign_name"] == campaign_a]
    row_b = df[df["campaign_name"] == campaign_b]

    fig = go.Figure()
    if not row_a.empty:
        fig.add_trace(go.Bar(
            name=campaign_a,
            x=labels,
            y=[float(row_a[m].iloc[0]) for m in metrics],
            text=[f"{float(row_a[m].iloc[0]):.1f}%" for m in metrics],
            textposition="outside",
        ))
    if not row_b.empty:
        fig.add_trace(go.Bar(
            name=campaign_b,
            x=labels,
            y=[float(row_b[m].iloc[0]) for m in metrics],
            text=[f"{float(row_b[m].iloc[0]):.1f}%" for m in metrics],
            textposition="outside",
        ))

    bench_vals = [BENCHMARKS.get(m, 0) for m in metrics]
    fig.add_trace(go.Scatter(
        name="Benchmark",
        x=labels,
        y=bench_vals,
        mode="markers",
        marker=dict(symbol="line-ew", size=14, color="red", line=dict(width=2, color="red")),
    ))

    fig.update_layout(
        title=f"A/B Comparison: {campaign_a}  vs  {campaign_b}",
        barmode="group",
        yaxis_title="Rate (%)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        uniformtext_minsize=8,
    )
    return fig
