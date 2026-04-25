import os
import io
import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.data_loader import load_campaign_data
from src.analyzer import CampaignAnalyzer
from src.insights_generator import InsightsGenerator
from src.charts import (
    benchmark_comparison_chart,
    trend_chart,
    revenue_chart,
    metric_heatmap,
    campaign_radar,
    ab_comparison_chart,
)

st.set_page_config(
    page_title="Email Performance Insights",
    page_icon="📧",
    layout="wide",
)

st.title("📧 GenAI-Powered Email Performance Insights")
st.caption("Analyze email campaigns and get actionable AI insights using Claude Opus 4.6")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")

    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        help="Get your key at console.anthropic.com",
    )

    st.divider()

    st.header("📂 Data Source")
    data_source = st.radio("Choose data source", ["Use sample data", "Upload CSV"])

    uploaded_file = None
    if data_source == "Upload CSV":
        uploaded_file = st.file_uploader("Upload campaign CSV", type=["csv"])
        with st.expander("Required columns"):
            st.code(
                "campaign_id, campaign_name, campaign_type, segment,\n"
                "send_date, subject_line, total_sent, total_delivered,\n"
                "total_opened, total_clicked, total_converted,\n"
                "total_bounced, total_unsubscribed, revenue_generated"
            )

    st.divider()

    st.header("🔍 Analysis Options")
    mode = st.selectbox("Analysis mode", ["All (campaigns + groups)", "Campaigns only", "Groups only"])
    group_by = st.selectbox("Group campaigns by", ["campaign_type", "segment"])

    st.divider()

    st.header("⚡ Batch Mode")
    use_batch = st.toggle(
        "Use Anthropic Batches API",
        value=False,
        help="Submit all campaign insights as a single batch request (async, ~50% cheaper). "
             "Results may take a few minutes.",
    )


# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def get_sample_data() -> pd.DataFrame:
    return load_campaign_data("data/sample_campaigns.csv")


def load_data() -> pd.DataFrame | None:
    if data_source == "Upload CSV" and uploaded_file:
        return load_campaign_data(io.StringIO(uploaded_file.read().decode()))
    elif data_source == "Use sample data":
        return get_sample_data()
    return None


df = load_data()

if df is None:
    st.info("Upload a CSV file or select 'Use sample data' to get started.")
    st.stop()

# ── Data Preview ──────────────────────────────────────────────────────────────
with st.expander("📊 Campaign Data Preview", expanded=False):
    display_cols = [
        "campaign_name", "campaign_type", "segment", "send_date",
        "open_rate", "click_rate", "conversion_rate", "bounce_rate",
        "unsubscribe_rate", "revenue_generated",
    ]
    available = [c for c in display_cols if c in df.columns]
    st.dataframe(df[available], use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Campaigns", len(df))
    col2.metric("Total Sent", f"{df['total_sent'].sum():,}")
    col3.metric("Avg Open Rate", f"{df['open_rate'].mean():.1f}%")
    col4.metric("Total Revenue", f"${df['revenue_generated'].sum():,.0f}")

# ── Dashboard Charts ──────────────────────────────────────────────────────────
st.divider()
st.subheader("📈 Performance Dashboard")

tab_bench, tab_revenue, tab_heat = st.tabs(["Benchmarks", "Revenue", "Heatmap"])

with tab_bench:
    st.plotly_chart(benchmark_comparison_chart(df), use_container_width=True)

with tab_revenue:
    st.plotly_chart(revenue_chart(df), use_container_width=True)

with tab_heat:
    st.plotly_chart(metric_heatmap(df), use_container_width=True)

# ── Trend Over Time ───────────────────────────────────────────────────────────
st.divider()
st.subheader("📉 Trend Analysis")

trend_metric = st.selectbox(
    "Select metric to track over time",
    options=["open_rate", "click_rate", "click_to_open_rate", "conversion_rate", "bounce_rate", "unsubscribe_rate"],
    format_func=lambda m: m.replace("_", " ").title(),
    key="trend_metric_select",
)
st.plotly_chart(trend_chart(df, trend_metric), use_container_width=True)

# ── A/B Comparison ────────────────────────────────────────────────────────────
st.divider()
st.subheader("🔬 A/B Campaign Comparison")

campaign_names = df["campaign_name"].tolist()
ab_col1, ab_col2 = st.columns(2)
with ab_col1:
    campaign_a = st.selectbox("Campaign A", campaign_names, index=0, key="ab_a")
with ab_col2:
    campaign_b = st.selectbox("Campaign B", campaign_names, index=min(1, len(campaign_names) - 1), key="ab_b")

if campaign_a != campaign_b:
    st.plotly_chart(ab_comparison_chart(df, campaign_a, campaign_b), use_container_width=True)

    # Side-by-side metric table
    row_a = df[df["campaign_name"] == campaign_a].iloc[0]
    row_b = df[df["campaign_name"] == campaign_b].iloc[0]
    rate_cols = ["open_rate", "click_rate", "click_to_open_rate", "conversion_rate", "bounce_rate", "unsubscribe_rate"]
    table_data = {
        "Metric": [m.replace("_", " ").title() for m in rate_cols],
        campaign_a: [f"{float(row_a[m]):.2f}%" for m in rate_cols],
        campaign_b: [f"{float(row_b[m]):.2f}%" for m in rate_cols],
    }
    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

    # Radar chart
    st.plotly_chart(campaign_radar(df, [campaign_a, campaign_b]), use_container_width=True)

    # Optional AI comparison
    if st.button("🤖 Generate AI Comparison Insight", key="ab_insight_btn"):
        if not api_key:
            st.error("Please enter your Anthropic API key in the sidebar.")
        else:
            analyzer = CampaignAnalyzer(df)
            insights_gen = InsightsGenerator(api_key=api_key)
            stats_a = analyzer.get_campaign_stats(row_a)
            stats_b = analyzer.get_campaign_stats(row_b)
            with st.spinner("Generating A/B comparison insight..."):
                ab_insight = insights_gen.generate_ab_comparison(
                    row_a.to_dict(), stats_a, row_b.to_dict(), stats_b
                )
            st.markdown(ab_insight)
else:
    st.info("Select two different campaigns to compare.")

# ── Generate AI Insights ──────────────────────────────────────────────────────
st.divider()

if use_batch:
    # ── Batch Mode ────────────────────────────────────────────────────────────
    st.subheader("⚡ Batch Insight Generation")
    st.info(
        "Batch mode submits all campaigns to the Anthropic Batches API in one request. "
        "This costs ~50% less and is ideal for large datasets. Results are ready in minutes."
    )

    if "batch_id" not in st.session_state:
        st.session_state.batch_id = None
    if "batch_results" not in st.session_state:
        st.session_state.batch_results = {}

    submit_col, status_col = st.columns(2)

    with submit_col:
        if st.button("🚀 Submit Batch", type="primary", use_container_width=True):
            if not api_key:
                st.error("Please enter your Anthropic API key in the sidebar.")
            else:
                analyzer = CampaignAnalyzer(df)
                insights_gen = InsightsGenerator(api_key=api_key)
                stats_map = {
                    str(row["campaign_id"]): analyzer.get_campaign_stats(row)
                    for _, row in df.iterrows()
                }
                with st.spinner("Submitting batch to Anthropic API..."):
                    batch_id = insights_gen.submit_batch(
                        df.to_dict(orient="records"), stats_map
                    )
                st.session_state.batch_id = batch_id
                st.success(f"Batch submitted! ID: `{batch_id}`")

    with status_col:
        if st.button("🔄 Check Batch Status", use_container_width=True):
            if not st.session_state.batch_id:
                st.warning("No batch submitted yet.")
            elif not api_key:
                st.error("Please enter your Anthropic API key.")
            else:
                insights_gen = InsightsGenerator(api_key=api_key)
                status = insights_gen.get_batch_status(st.session_state.batch_id)
                st.json(status)
                if status["status"] == "ended":
                    st.success("Batch complete — click 'Retrieve Results' below.")

    if st.session_state.batch_id:
        st.caption(f"Current batch ID: `{st.session_state.batch_id}`")

        if st.button("📥 Retrieve Batch Results", use_container_width=True):
            if not api_key:
                st.error("Please enter your Anthropic API key.")
            else:
                insights_gen = InsightsGenerator(api_key=api_key)
                with st.spinner("Retrieving batch results..."):
                    results = insights_gen.retrieve_batch_results(st.session_state.batch_id)
                st.session_state.batch_results = results
                st.success(f"Retrieved {len(results)} results.")

        if st.session_state.batch_results:
            st.subheader("📌 Batch Campaign Insights")
            id_to_name = {str(row["campaign_id"]): row["campaign_name"] for _, row in df.iterrows()}
            for cid, insight in st.session_state.batch_results.items():
                name = id_to_name.get(cid, cid)
                with st.expander(f"📩 {name}"):
                    st.markdown(insight)

            batch_md = "\n\n---\n\n".join(
                f"## {id_to_name.get(cid, cid)}\n\n{txt}"
                for cid, txt in st.session_state.batch_results.items()
            )
            st.download_button(
                "📄 Download Batch Report (Markdown)",
                data=batch_md,
                file_name="batch_insight_report.md",
                mime="text/markdown",
                use_container_width=True,
            )

else:
    # ── Streaming Mode ────────────────────────────────────────────────────────
    run_button = st.button("🚀 Generate AI Insights", type="primary", use_container_width=True)

    if run_button:
        if not api_key:
            st.error("Please enter your Anthropic API key in the sidebar.")
            st.stop()

        analyzer = CampaignAnalyzer(df)
        insights_gen = InsightsGenerator(api_key=api_key)

        run_campaigns = mode in ("All (campaigns + groups)", "Campaigns only")
        run_groups = mode in ("All (campaigns + groups)", "Groups only")

        all_insights: dict = {}

        # ── Executive Summary ─────────────────────────────────────────────────
        st.subheader("🏆 Executive Summary")
        with st.spinner("Generating executive summary..."):
            overall_summary = analyzer.get_overall_summary()
            exec_insight = insights_gen.generate_executive_summary(
                overall_summary, df.to_dict(orient="records")
            )
        st.markdown(exec_insight)
        all_insights["executive_summary"] = exec_insight

        # Summary KPIs
        kpi_cols = st.columns(4)
        kpi_cols[0].metric("Campaigns", overall_summary["total_campaigns"])
        kpi_cols[1].metric("Total Sent", f"{overall_summary['total_sent']:,}")
        kpi_cols[2].metric("Total Revenue", f"${overall_summary['total_revenue']:,.0f}")
        kpi_cols[3].metric(
            "Avg Open Rate",
            f"{overall_summary.get('avg_open_rate', 0):.1f}%",
            help="vs 21.5% benchmark",
        )

        # ── Per-Campaign ──────────────────────────────────────────────────────
        if run_campaigns:
            st.divider()
            st.subheader("📌 Per-Campaign Insights")
            campaign_insights = {}

            for _, row in df.iterrows():
                name = row["campaign_name"]
                with st.expander(f"📩 {name}", expanded=False):
                    with st.spinner(f"Generating insights for {name}..."):
                        stats = analyzer.get_campaign_stats(row)
                        insight = insights_gen.generate_campaign_insight(row.to_dict(), stats)

                    st.markdown(insight)

                    metric_cols = st.columns(3)
                    rate_metrics = [
                        ("open_rate", "Open Rate"),
                        ("click_rate", "Click Rate"),
                        ("click_to_open_rate", "CTOR"),
                        ("conversion_rate", "Conv. Rate"),
                        ("bounce_rate", "Bounce Rate"),
                        ("unsubscribe_rate", "Unsub Rate"),
                    ]
                    for i, (key, label) in enumerate(rate_metrics):
                        if key in stats and isinstance(stats[key], dict):
                            m = stats[key]
                            delta = m["vs_benchmark"]
                            delta_color = "normal"
                            if key in ("bounce_rate", "unsubscribe_rate"):
                                delta_color = "inverse"
                            metric_cols[i % 3].metric(
                                label,
                                f"{m['value']}%",
                                f"{'+' if delta > 0 else ''}{delta}% vs benchmark",
                                delta_color=delta_color,
                            )

                    campaign_insights[row["campaign_id"]] = {
                        "campaign": row.to_dict(),
                        "stats": stats,
                        "insight": insight,
                    }

            all_insights["campaigns"] = campaign_insights

        # ── Groups ────────────────────────────────────────────────────────────
        if run_groups:
            st.divider()
            st.subheader(f"🗂️ Group Insights — by {group_by}")
            group_insights = {}

            for group_name, group_df in analyzer.get_groups(group_by):
                with st.expander(f"📁 {group_name} ({len(group_df)} campaigns)", expanded=False):
                    with st.spinner(f"Generating insights for group: {group_name}..."):
                        stats = analyzer.get_group_stats(group_df)
                        insight = insights_gen.generate_group_insight(
                            str(group_name),
                            group_df.to_dict(orient="records"),
                            stats,
                        )

                    st.markdown(insight)

                    group_insights[str(group_name)] = {
                        "group_by": group_by,
                        "campaigns": group_df.to_dict(orient="records"),
                        "stats": stats,
                        "insight": insight,
                    }

            all_insights["groups"] = group_insights

        # ── Download ──────────────────────────────────────────────────────────
        st.divider()
        st.subheader("⬇️ Download Report")

        def _safe(obj):
            if isinstance(obj, dict):
                return {k: _safe(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_safe(i) for i in obj]
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)

        json_str = json.dumps(_safe(all_insights), indent=2)

        md_lines = ["# Email Performance Insight Report\n"]
        if "executive_summary" in all_insights:
            md_lines.append("## Executive Summary\n")
            md_lines.append(all_insights["executive_summary"])
            md_lines.append("\n---\n")
        for section in ("campaigns", "groups"):
            if section in all_insights:
                md_lines.append(f"## {section.title()}\n")
                for _, data in all_insights[section].items():
                    md_lines.append(data["insight"])
                    md_lines.append("\n---\n")

        col_dl1, col_dl2 = st.columns(2)
        col_dl1.download_button(
            "📄 Download Markdown Report",
            data="\n".join(md_lines),
            file_name="email_insight_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        col_dl2.download_button(
            "📦 Download JSON Report",
            data=json_str,
            file_name="email_insight_report.json",
            mime="application/json",
            use_container_width=True,
        )

        st.success("✅ Analysis complete!")
