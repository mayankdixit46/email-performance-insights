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

# ── Generate Insights ─────────────────────────────────────────────────────────
st.divider()

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

    # ── Per-Campaign ──────────────────────────────────────────────────────────
    if run_campaigns:
        st.subheader("📌 Per-Campaign Insights")
        campaign_insights = {}

        for _, row in df.iterrows():
            name = row["campaign_name"]
            with st.expander(f"📩 {name}", expanded=False):
                with st.spinner(f"Generating insights for {name}..."):
                    stats = analyzer.get_campaign_stats(row)
                    insight = insights_gen.generate_campaign_insight(row.to_dict(), stats)

                st.markdown(insight)

                # Metrics table
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

    # ── Groups ────────────────────────────────────────────────────────────────
    if run_groups:
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

    # ── Download ──────────────────────────────────────────────────────────────
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
    for section, items in all_insights.items():
        md_lines.append(f"## {section.title()}\n")
        for _, data in items.items():
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
