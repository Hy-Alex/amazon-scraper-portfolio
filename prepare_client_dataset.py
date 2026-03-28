import logging
from pathlib import Path

import pandas as pd


INPUT_PATH = Path("output/amazon_products.csv")
OUTPUT_PATH = Path("output/client_ready_products.csv")
SUMMARY_PATH = Path("output/client_ready_summary.csv")
KEYWORD = "laptop"


def to_numeric_price(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace(r"[^0-9.]", "", regex=True)
        .replace("", pd.NA)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def to_numeric_reviews(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(r"[^0-9]", "", regex=True)
        .replace("", pd.NA)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def to_numeric_rating(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.extract(r"([0-9]+(?:\.[0-9]+)?)", expand=False)
        .replace("", pd.NA)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def price_category(price: float) -> str:
    if pd.isna(price):
        return "Unknown"
    if price < 300:
        return "Budget"
    if price < 700:
        return "Mid-range"
    return "Premium"


def build_client_ready_dataset(input_path: Path, output_path: Path, summary_path: Path) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    df = pd.read_csv(input_path)
    rows_before = len(df)

    required_columns = ["title", "price", "rating", "review_count", "product_url"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Drop technical columns when present.
    df = df.drop(columns=["asin", "is_prime", "is_sponsored"], errors="ignore")
    if "currency" in df.columns:
        currency_values = (
            df["currency"].dropna().astype(str).str.strip().str.upper().unique().tolist()
        )
        if not currency_values or set(currency_values) == {"USD"}:
            df = df.drop(columns=["currency"])

    client_df = df[required_columns].copy()

    client_df["title"] = (
        client_df["title"].astype(str).str.strip().str.slice(0, 80)
    )
    client_df["price"] = to_numeric_price(client_df["price"])
    client_df["rating"] = to_numeric_rating(client_df["rating"])
    client_df["review_count"] = to_numeric_reviews(client_df["review_count"])

    client_df = client_df.drop_duplicates()
    client_df = client_df.sort_values(
        by=["rating", "review_count"],
        ascending=[False, False],
        na_position="last",
    )

    client_df["Price Category"] = client_df["price"].apply(price_category)

    client_df = client_df.rename(
        columns={
            "title": "Product",
            "price": "Price (USD)",
            "rating": "Rating",
            "review_count": "Reviews",
            "product_url": "Product Link",
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    client_df.to_csv(output_path, index=False)

    summary_df = pd.DataFrame(
        [{"Keyword": KEYWORD, "Total products count": len(client_df)}]
    )
    summary_df.to_csv(summary_path, index=False)

    logging.info("Rows before cleaning: %s", rows_before)
    logging.info("Rows after cleaning: %s", len(client_df))
    logging.info("Saved client-ready CSV to: %s", output_path.resolve())
    logging.info("Saved summary CSV to: %s", summary_path.resolve())


if __name__ == "__main__":
    build_client_ready_dataset(INPUT_PATH, OUTPUT_PATH, SUMMARY_PATH)