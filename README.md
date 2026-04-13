# GenAI-Powered Email Performance Insights

A GenAI-driven tool that automatically analyzes historical email campaign performance data and generates actionable insights using **Claude Opus 4.6** (Anthropic).

## What It Does

- Loads email campaign data from CSV
- Computes key metrics and compares against industry benchmarks
- Generates structured AI insights **per campaign** and **per group**
- Produces a standardized **"What Worked / What Didn't / What to Optimize Next"** output
- Exports reports as both Markdown and JSON

## Output Format

For every campaign and group, the tool generates:

```
## Campaign: Black Friday Sale

### Performance Overview
...summary...

### ✅ What Worked
- Subject line drove 30% above-benchmark open rate...
- High-value segment click-to-open outperformed benchmark by 8%...

### ❌ What Didn't Work
- Unsubscribe rate 0.3% above benchmark — audience fatigue signal...
- Bounce rate elevated at 4% suggesting list hygiene issue...

### 🎯 What to Optimize Next
1. Segment the list to reduce unsubscribes — target engaged users only
2. A/B test subject line urgency vs. value framing
3. Clean bounced addresses before next promotional send

### Key Takeaway
Strong revenue performance masks deliverability risk that must be addressed.
```

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/email-performance-insights.git
cd email-performance-insights
pip install -r requirements.txt
```

### 2. Set Your API Key

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

Or export directly:

```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

Get your key at [console.anthropic.com](https://console.anthropic.com).

### 3. Run

```bash
# Full analysis (campaigns + groups)
python main.py

# Campaigns only
python main.py --mode campaigns

# Groups only, grouped by customer segment
python main.py --mode groups --group-by segment

# Custom data file and output directory
python main.py --data data/my_campaigns.csv --output-dir reports/
```

Reports are saved to `output/` as `insight_report_TIMESTAMP.md` and `.json`.

## Input Data Format

Provide a CSV with these columns:

| Column | Description |
|---|---|
| `campaign_id` | Unique identifier |
| `campaign_name` | Human-readable name |
| `campaign_type` | e.g. `promotional`, `newsletter`, `onboarding` |
| `segment` | Target audience segment |
| `send_date` | Date sent (YYYY-MM-DD) |
| `subject_line` | Email subject |
| `total_sent` | Total emails sent |
| `total_delivered` | Successfully delivered |
| `total_opened` | Unique opens |
| `total_clicked` | Unique clicks |
| `total_converted` | Conversions (purchases, signups, etc.) |
| `total_bounced` | Bounced emails |
| `total_unsubscribed` | Unsubscribes |
| `revenue_generated` | Revenue attributed to campaign |

Rate columns (`open_rate`, `click_rate`, etc.) are computed automatically if not provided.

A sample dataset with 15 realistic campaigns is included at `data/sample_campaigns.csv`.

## Project Structure

```
email-performance-insights/
├── main.py                  # CLI entry point
├── requirements.txt
├── .env.example
├── data/
│   └── sample_campaigns.csv # Sample data (15 campaigns)
├── src/
│   ├── data_loader.py       # CSV loading & validation
│   ├── analyzer.py          # Stats calculation & benchmarking
│   ├── insights_generator.py # Claude API integration (streaming)
│   └── report.py            # Markdown/JSON report generation
└── output/                  # Generated reports (gitignored)
```

## CLI Options

| Flag | Default | Description |
|---|---|---|
| `--data` | `data/sample_campaigns.csv` | Path to CSV file |
| `--output-dir` | `output` | Report output directory |
| `--mode` | `all` | `all`, `campaigns`, or `groups` |
| `--group-by` | `campaign_type` | `campaign_type` or `segment` |

## Industry Benchmarks Used

The tool compares campaign metrics against these industry averages:

| Metric | Benchmark |
|---|---|
| Open Rate | 21.5% |
| Click Rate | 2.3% |
| Click-to-Open Rate | 10.5% |
| Conversion Rate | 3.5% |
| Bounce Rate | 0.7% |
| Unsubscribe Rate | 0.1% |

## Business Value

| Before | After |
|---|---|
| Manual data export + spreadsheet analysis | Automated insight generation |
| Hours of analyst time per campaign | Minutes per full dataset |
| Inconsistent report formats | Standardized "What Worked / What Didn't / What to Optimize" |
| Insights locked in spreadsheets | Exportable Markdown + JSON for any workflow |

## Extending the Framework

- **New email streams:** Add rows to the CSV — no code changes needed
- **Custom benchmarks:** Edit `BENCHMARKS` in `src/analyzer.py`
- **Slack/email delivery:** Pipe the Markdown output to any notification service
- **Dashboard integration:** Use the JSON output to populate a BI tool
- **Batch processing:** Use the Anthropic Batches API for large datasets at 50% cost

## Requirements

- Python 3.10+
- Anthropic API key
