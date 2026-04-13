import pandas as pd
from pathlib import Path


REQUIRED_COLUMNS = [
    "campaign_id", "campaign_name", "campaign_type", "segment",
    "send_date", "subject_line", "total_sent", "total_delivered",
    "total_opened", "total_clicked", "total_converted",
    "total_bounced", "total_unsubscribed", "revenue_generated",
]


def load_campaign_data(filepath: str) -> pd.DataFrame:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")

    df = pd.read_csv(filepath, parse_dates=["send_date"])

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Compute derived rate columns if not present
    if "open_rate" not in df.columns:
        df["open_rate"] = (df["total_opened"] / df["total_delivered"] * 100).round(2)
    if "click_rate" not in df.columns:
        df["click_rate"] = (df["total_clicked"] / df["total_delivered"] * 100).round(2)
    if "click_to_open_rate" not in df.columns:
        df["click_to_open_rate"] = (
            df["total_clicked"] / df["total_opened"].replace(0, pd.NA) * 100
        ).round(2)
    if "conversion_rate" not in df.columns:
        df["conversion_rate"] = (
            df["total_converted"] / df["total_clicked"].replace(0, pd.NA) * 100
        ).round(2)
    if "bounce_rate" not in df.columns:
        df["bounce_rate"] = (df["total_bounced"] / df["total_sent"] * 100).round(2)
    if "unsubscribe_rate" not in df.columns:
        df["unsubscribe_rate"] = (df["total_unsubscribed"] / df["total_delivered"] * 100).round(2)
    if "delivery_rate" not in df.columns:
        df["delivery_rate"] = (df["total_delivered"] / df["total_sent"] * 100).round(2)

    df = df.fillna(0)
    return df
