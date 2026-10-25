"""Generate source-backed static charts from the DuckDB Gold marts."""

from __future__ import annotations

import os
from pathlib import Path

from ingestion.config import resolve_warehouse_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".cache" / "matplotlib"))

import duckdb
import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter, PercentFormatter

WAREHOUSE_PATH = resolve_warehouse_path()
OUTPUT_DIR = PROJECT_ROOT / "docs" / "assets" / "charts"
GOLD_SCHEMA = "analytics_gold"

PALETTE = {
    "blue": "#315F78",
    "blue_light": "#78A8B8",
    "orange": "#C66A3D",
    "gold": "#C49A43",
    "slate": "#65737E",
    "light": "#D9E2E7",
    "text": "#24313A",
    "grid": "#E6ECEF",
}

DISCOUNT_ORDER = ["0%", "(0-20%]", "(20-40%]", "(40-60%]", ">60%", "Unknown"]
SEGMENT_ORDER = ["Corporate", "Consumer", "Self-Employed"]
KNOWN_CATEGORY_ORDER = [
    "Body care",
    "Face care",
    "Hair care",
    "Home and Accessories",
    "Make up",
]

REQUIRED_MARTS = {
    "mart_sales_by_segment",
    "mart_discount_profitability",
    "mart_customer_rfm",
    "mart_monthly_sales",
    "mart_product_performance",
    "mart_profitability_by_market",
    "mart_top_countries_by_sales",
    "mart_category_sales_mix_by_segment",
    "mart_customer_profile_by_gender_occupation",
    "mart_customer_region_behavior",
}


def query_df(connection: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    """Run a read-only query and return its result as a DataFrame."""
    return connection.execute(sql).fetchdf()


def amount_formatter(value: float, _position: int | None = None) -> str:
    """Format source amounts without inventing a currency symbol."""
    return f"{value:,.0f}".replace(",", ".")


def compact_amount_formatter(value: float, _position: int | None = None) -> str:
    """Keep large monetary axes legible while preserving the source unit."""
    absolute = abs(value)
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:g}M"
    if absolute >= 1_000:
        return f"{value / 1_000:g}k"
    return f"{value:g}"


def integer_label(value: float) -> str:
    return f"{int(round(value)):,}".replace(",", ".")


def amount_label(value: float, decimals: int = 0) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def setup_style() -> None:
    sns.set_theme(
        style="whitegrid",
        context="notebook",
        font="DejaVu Sans",
        rc={
            "axes.edgecolor": PALETTE["grid"],
            "axes.labelcolor": PALETTE["text"],
            "axes.titlecolor": PALETTE["text"],
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "grid.color": PALETTE["grid"],
            "text.color": PALETTE["text"],
            "xtick.color": PALETTE["text"],
            "ytick.color": PALETTE["text"],
            "axes.unicode_minus": False,
        },
    )


def save_figure(figure: plt.Figure, filename: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / filename
    figure.savefig(output_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return output_path


def check_marts(connection: duckdb.DuckDBPyConnection) -> None:
    found = {
        row[0]
        for row in connection.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = ?
            """,
            [GOLD_SCHEMA],
        ).fetchall()
    }
    missing = sorted(REQUIRED_MARTS - found)
    if missing:
        raise RuntimeError(
            "Required Gold marts are missing. Run dbt build first: "
            + ", ".join(missing)
        )


def load_chart_data(connection: duckdb.DuckDBPyConnection) -> dict[str, pd.DataFrame]:
    prefix = f'"{GOLD_SCHEMA}".'
    data: dict[str, pd.DataFrame] = {}

    data["segments"] = query_df(
        connection,
        f"select * from {prefix}mart_sales_by_segment order by total_sales desc",
    )
    data["discount"] = query_df(
        connection,
        f"""
        select
            discount_band,
            sum(sales_line_count) as sales_line_count,
            sum(total_sales) as total_sales,
            sum(total_profit) as total_profit,
            sum(loss_making_line_count) as loss_making_line_count
        from {prefix}mart_discount_profitability
        group by discount_band
        """,
    )
    data["monthly"] = query_df(
        connection,
        f"select * from {prefix}mart_monthly_sales order by sales_month",
    )
    data["mix"] = query_df(
        connection,
        f"select * from {prefix}mart_category_sales_mix_by_segment",
    )
    data["products"] = query_df(
        connection,
        f"""
        select
            product_code, product_name, category, units_sold,
            total_sales, total_profit
        from {prefix}mart_product_performance
        where category <> 'Unknown'
        order by units_sold desc, product_code
        limit 10
        """,
    )
    data["products_by_profit"] = query_df(
        connection,
        f"""
        select
            product_code, product_name, category, units_sold,
            total_sales, total_profit
        from {prefix}mart_product_performance
        where category <> 'Unknown'
        order by total_profit desc, product_code
        limit 10
        """,
    )
    data["markets"] = query_df(
        connection,
        f"""
        select market, sales_line_count, total_sales, total_profit, profit_margin
        from {prefix}mart_profitability_by_market
        where market <> 'Unknown'
        order by profit_margin, market
        """,
    )
    data["unknown_market"] = query_df(
        connection,
        f"""
        select sales_line_count, total_sales, total_profit
        from {prefix}mart_profitability_by_market
        where market = 'Unknown'
        """,
    )
    data["countries"] = query_df(
        connection,
        f"""
        select country, sales_line_count, total_sales
        from {prefix}mart_top_countries_by_sales
        where sales_rank is not null
        order by sales_rank
        limit 10
        """,
    )
    data["rfm_sensitivity"] = query_df(
        connection,
        f"""
        with thresholds(threshold_days) as (
            values (60), (90), (180)
        )
        select
            t.threshold_days,
            count(*) as customer_population,
            sum(case when r.recency_days >= t.threshold_days then 1 else 0 end)
                as customers_at_risk,
            sum(case when r.is_vip then 1 else 0 end) as vip_population,
            sum(case
                when r.is_vip and r.recency_days >= t.threshold_days then 1
                else 0
            end) as vip_customers_at_risk
        from {prefix}mart_customer_rfm as r
        cross join thresholds as t
        group by t.threshold_days
        order by t.threshold_days
        """,
    )
    data["customer_profile"] = query_df(
        connection,
        f"""
        select gender, occupation, customer_count
        from {prefix}mart_customer_profile_by_gender_occupation
        """,
    )
    data["customer_regions"] = query_df(
        connection,
        f"""
        select
            matched_region_count,
            count(*) as customer_count,
            sum(case when has_orphan_region_activity then 1 else 0 end)
                as customers_with_orphan_region_activity
        from {prefix}mart_customer_region_behavior
        group by matched_region_count
        order by matched_region_count
        """,
    )
    data["rfm_snapshot"] = query_df(
        connection,
        f"select min(snapshot_date) as snapshot_date from {prefix}mart_customer_rfm",
    )
    data["unknown_country"] = query_df(
        connection,
        f"""
        select sales_line_count, total_sales
        from {prefix}mart_top_countries_by_sales
        where country = 'Unknown'
        """,
    )
    return data


def validate_reconciliation(data: dict[str, pd.DataFrame]) -> None:
    segments = data["segments"]
    discount = data["discount"]
    monthly = data["monthly"]

    expected_lines = int(segments["sales_line_count"].sum())
    expected_sales = float(segments["total_sales"].sum())
    expected_profit = float(segments["total_profit"].sum())

    discount_lines = int(discount["sales_line_count"].sum())
    monthly_lines = int(monthly["sales_line_count"].sum())
    if discount_lines != expected_lines or monthly_lines != expected_lines:
        raise RuntimeError(
            "Gold mart reconciliation failed for sales lines: "
            f"segment={expected_lines}, discount={discount_lines}, "
            f"monthly={monthly_lines}."
        )

    for metric, expected, actual in (
        ("sales", expected_sales, float(discount["total_sales"].sum())),
        ("profit", expected_profit, float(discount["total_profit"].sum())),
        ("monthly sales", expected_sales, float(monthly["total_sales"].sum())),
        ("monthly profit", expected_profit, float(monthly["total_profit"].sum())),
    ):
        if abs(expected - actual) > 0.01:
            raise RuntimeError(
                f"Gold mart reconciliation failed for {metric}: "
                f"segment={expected:.2f}, compared={actual:.2f}."
            )


def chart_executive_overview(data: dict[str, pd.DataFrame]) -> Path:
    segments = data["segments"]
    sales = float(segments["total_sales"].sum())
    profit = float(segments["total_profit"].sum())
    lines = int(segments["sales_line_count"].sum())
    orders = int(segments["order_count"].sum())
    customers = int(
        query_value_for_population(data["rfm_sensitivity"], "customer_population")
    )
    margin = profit / sales if sales else 0.0
    monthly = data["monthly"]
    period = (
        f"{pd.to_datetime(monthly['sales_month'].min()).strftime('%Y-%m')} – "
        f"{pd.to_datetime(monthly['sales_month'].max()).strftime('%Y-%m')}"
    )

    cards = [
        ("TOTAL SALES", amount_label(sales, 0), "đơn vị theo nguồn"),
        ("TOTAL PROFIT", amount_label(profit, 2), "đơn vị theo nguồn"),
        ("PROFIT MARGIN", f"{margin:.2%}", "profit / sales"),
        ("ORDERS", integer_label(orders), "đếm order_id khác nhau"),
        ("SALES LINES", integer_label(lines), "grain row_id"),
        ("CUSTOMERS", integer_label(customers), "snapshot RFM"),
    ]

    figure, axes = plt.subplots(1, len(cards), figsize=(16, 3.3))
    for axis, (title, value, note) in zip(axes, cards, strict=True):
        axis.axis("off")
        axis.text(0.5, 0.74, title, ha="center", va="center", fontsize=10,
                  color=PALETTE["slate"], fontweight="bold")
        axis.text(0.5, 0.47, value, ha="center", va="center", fontsize=16,
                  color=PALETTE["blue"], fontweight="bold")
        axis.text(0.5, 0.20, note, ha="center", va="center", fontsize=8,
                  color=PALETTE["slate"])

    figure.suptitle("Tổng quan hiệu quả kinh doanh", x=0.02, ha="left",
                    fontsize=17, fontweight="bold", color=PALETTE["text"])
    figure.text(0.02, 0.06,
                f"Kỳ dữ liệu: {period} | Giá trị tiền tệ giữ nguyên đơn vị của nguồn.",
                fontsize=9, color=PALETTE["slate"])
    figure.tight_layout(rect=(0, 0.12, 1, 0.85))
    return save_figure(figure, "01_executive_overview.png")


def query_value_for_population(frame: pd.DataFrame, column: str) -> float:
    """Return the first value from the threshold-independent population column."""
    if frame.empty:
        return 0
    return float(frame[column].iloc[0])


def chart_discount_profitability(data: dict[str, pd.DataFrame]) -> Path:
    frame = data["discount"].copy()
    frame["discount_band"] = pd.Categorical(
        frame["discount_band"], categories=DISCOUNT_ORDER, ordered=True
    )
    frame = frame.sort_values("discount_band")
    frame["loss_line_rate"] = (
        frame["loss_making_line_count"] / frame["sales_line_count"]
    )
    x = range(len(frame))
    profits = frame["total_profit"].astype(float).tolist()
    rates = frame["loss_line_rate"].astype(float).tolist()
    bands = frame["discount_band"].astype(str).tolist()

    figure, axes = plt.subplots(1, 2, figsize=(13.5, 5.4))
    profit_colors = [
        PALETTE["orange"] if value < 0 else PALETTE["blue"] for value in profits
    ]
    axes[0].bar(x, profits, color=profit_colors, width=0.68)
    axes[0].axhline(0, color=PALETTE["text"], linewidth=0.9)
    axes[0].set_xticks(list(x), bands, rotation=18, ha="right")
    axes[0].set_title("Total profit theo discount band", loc="left", fontweight="bold")
    axes[0].set_ylabel("Profit (đơn vị theo nguồn)")
    axes[0].yaxis.set_major_formatter(FuncFormatter(amount_formatter))
    for axis, value in zip(axes[0].patches, profits, strict=True):
        y = value + (max(abs(v) for v in profits) * 0.025 if value >= 0 else -max(abs(v) for v in profits) * 0.06)
        axes[0].text(axis.get_x() + axis.get_width() / 2, y,
                     amount_label(value, 0), ha="center",
                     va="bottom" if value >= 0 else "top", fontsize=8)

    axes[1].bar(x, [rate * 100 for rate in rates],
                color=[PALETTE["slate"], PALETTE["blue_light"],
                       PALETTE["orange"], PALETTE["orange"], PALETTE["orange"],
                       PALETTE["light"]][:len(rates)], width=0.68)
    axes[1].set_xticks(list(x), bands, rotation=18, ha="right")
    axes[1].set_ylim(0, 108)
    axes[1].set_ylabel("Tỷ lệ dòng lỗ")
    axes[1].yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:.0f}%"))
    axes[1].set_title("Tỷ lệ dòng giao dịch có profit < 0", loc="left", fontweight="bold")
    for patch, rate in zip(axes[1].patches, rates, strict=True):
        axes[1].text(patch.get_x() + patch.get_width() / 2,
                     patch.get_height() + 2, f"{rate:.1%}", ha="center", fontsize=8)

    figure.suptitle("Discount và profitability", x=0.04, ha="left",
                    fontsize=16, fontweight="bold")
    figure.text(0.04, 0.015,
                "Tổng hợp từ mart theo category × discount band; tỷ lệ lỗ tính trên số dòng row_id. "
                "Đây là so sánh mô tả, không xác định quan hệ nhân quả.",
                fontsize=8.5, color=PALETTE["slate"])
    figure.tight_layout(rect=(0, 0.09, 1, 0.91))
    return save_figure(figure, "02_discount_profitability.png")


def chart_segment_profitability(data: dict[str, pd.DataFrame]) -> Path:
    frame = data["segments"].copy()
    frame["segment"] = pd.Categorical(
        frame["segment"], categories=SEGMENT_ORDER, ordered=True
    )
    frame = frame.sort_values("segment")
    figure, axes = plt.subplots(1, 3, figsize=(15, 5.2))
    metrics = [
        ("total_sales", "Total sales", PALETTE["blue"], False),
        ("total_profit", "Total profit", PALETTE["orange"], False),
        ("profit_margin", "Profit margin", PALETTE["gold"], True),
    ]
    for axis, (column, title, color, is_rate) in zip(axes, metrics, strict=True):
        values = frame[column].astype(float)
        labels = frame["segment"].astype(str)
        axis.barh(labels, values, color=color, height=0.58)
        axis.invert_yaxis()
        axis.set_title(title, loc="left", fontweight="bold")
        if is_rate:
            axis.xaxis.set_major_formatter(PercentFormatter(xmax=1))
            axis.set_xlabel("Profit / total sales")
            for y, value in enumerate(values):
                axis.text(value + 0.003, y, f"{value:.1%}", va="center", fontsize=9)
        else:
            axis.xaxis.set_major_formatter(FuncFormatter(compact_amount_formatter))
            axis.set_xlabel("Giá trị theo đơn vị nguồn")
            pad = max(values.max(), 1) * 0.02
            for y, value in enumerate(values):
                axis.text(value + pad, y, amount_label(value, 0), va="center", fontsize=8)
        axis.grid(axis="x", alpha=0.7)
        axis.grid(axis="y", visible=False)

    figure.suptitle("Hiệu quả theo segment", x=0.035, ha="left",
                    fontsize=16, fontweight="bold")
    figure.text(0.035, 0.025,
                "Order count được đếm distinct theo segment; dữ liệu profile không có đơn thuộc nhiều segment.",
                fontsize=8.5, color=PALETTE["slate"])
    figure.tight_layout(rect=(0, 0.09, 1, 0.9))
    return save_figure(figure, "03_segment_profitability.png")


def chart_monthly_performance(data: dict[str, pd.DataFrame]) -> Path:
    frame = data["monthly"].copy()
    frame["sales_month"] = pd.to_datetime(frame["sales_month"])
    figure, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True)
    series = [
        ("total_sales", "Total sales", PALETTE["blue"], False),
        ("total_profit", "Total profit", PALETTE["orange"], False),
        ("sales_yoy_growth_rate", "Sales YoY growth", PALETTE["gold"], True),
    ]
    for axis, (column, title, color, is_rate) in zip(axes, series, strict=True):
        sns.lineplot(data=frame, x="sales_month", y=column, ax=axis,
                     color=color, linewidth=2.1, marker="o", markersize=3,
                     errorbar=None)
        axis.set_title(title, loc="left", fontweight="bold", fontsize=11)
        axis.set_xlabel("")
        if is_rate:
            axis.yaxis.set_major_formatter(PercentFormatter(xmax=1))
            axis.axhline(0, color=PALETTE["slate"], linewidth=0.8)
        else:
            axis.yaxis.set_major_formatter(FuncFormatter(amount_formatter))
            axis.set_ylabel("Đơn vị theo nguồn")
    start = frame["sales_month"].min()
    end = frame["sales_month"].max()
    for axis, (column, _title, _color, is_rate) in zip(axes, series, strict=True):
        if is_rate:
            axis.set_ylabel("Tăng trưởng YoY")
    axes[-1].set_xlim(start, end)
    axes[-1].xaxis.set_major_locator(mdates.YearLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[-1].set_xlabel("Tháng")
    figure.suptitle("Sales và profit theo tháng", x=0.04, ha="left",
                    fontsize=16, fontweight="bold")
    figure.text(0.04, 0.015,
                "YoY so sánh total_sales với cùng tháng năm trước; năm 2020 không có prior-year baseline.",
                fontsize=8.5, color=PALETTE["slate"])
    figure.tight_layout(rect=(0, 0.07, 1, 0.94))
    return save_figure(figure, "04_monthly_performance.png")


def chart_category_mix(data: dict[str, pd.DataFrame]) -> Path:
    frame = data["mix"].copy()
    all_categories = [
        category for category in KNOWN_CATEGORY_ORDER
        if category in set(frame["category"])
    ]
    if "Unknown" in set(frame["category"]):
        all_categories.append("Unknown")
    matrix = frame.pivot(
        index="segment", columns="category", values="sales_share_of_segment"
    ).reindex(index=SEGMENT_ORDER, columns=all_categories).fillna(0)
    labels = [name.replace(" and ", " and\n") for name in matrix.columns]

    def share_label(value: float) -> str:
        if 0 < value < 0.0001:
            return "<0.01%"
        if value < 0.0005:
            return "<0.05%"
        return f"{value:.1%}"

    annotations = matrix.apply(lambda column: column.map(share_label))

    figure, axis = plt.subplots(figsize=(12, 4.6))
    sns.heatmap(
        matrix,
        cmap="Blues",
        vmin=0,
        vmax=max(float(matrix.max().max()), 0.01),
        annot=annotations,
        fmt="",
        linewidths=1,
        linecolor="white",
        cbar_kws={
            "label": "Tỷ trọng sales trong segment",
            "format": PercentFormatter(xmax=1),
        },
        ax=axis,
        annot_kws={"fontsize": 10},
    )
    axis.set_xticklabels(labels, rotation=0, ha="center")
    axis.set_xlabel("Category")
    axis.set_ylabel("")
    axis.set_title("Category mix theo segment", loc="left",
                   fontsize=15, fontweight="bold", pad=14)
    figure.text(0.02, 0.015,
                "Mỗi hàng dùng segment_total_sales làm mẫu số. Ô 0% biểu thị không có dòng tương ứng trong mart.",
                fontsize=8.5, color=PALETTE["slate"])
    figure.tight_layout(rect=(0, 0.08, 1, 1))
    return save_figure(figure, "05_category_mix_by_segment.png")


def product_label(row: pd.Series) -> str:
    name = str(row["product_name"])
    if len(name) > 28:
        name = name[:25].rstrip() + "…"
    return f"{row['product_code']} · {name}"


def chart_product_performance(data: dict[str, pd.DataFrame]) -> Path:
    figure, axes = plt.subplots(1, 2, figsize=(16, 7.2))
    products = [data["products"], data["products_by_profit"]]
    specs = [
        ("units_sold", "Top sản phẩm theo units sold", PALETTE["blue"], "Units"),
        ("total_profit", "Top sản phẩm theo total profit", PALETTE["orange"],
         "Profit (đơn vị theo nguồn)"),
    ]
    for axis, frame, (column, title, color, xlabel) in zip(
        axes, products, specs, strict=True
    ):
        frame = frame.copy()
        frame["label"] = frame.apply(product_label, axis=1)
        frame = frame.sort_values(column, ascending=True)
        values = frame[column].astype(float)
        axis.barh(frame["label"], values, color=color, height=0.68)
        axis.set_title(title, loc="left", fontsize=12, fontweight="bold")
        axis.set_xlabel(xlabel)
        axis.xaxis.set_major_formatter(
            FuncFormatter(amount_formatter) if column == "total_profit"
            else FuncFormatter(lambda v, _p: integer_label(v))
        )
        axis.grid(axis="x", alpha=0.7)
        axis.grid(axis="y", visible=False)
        pad = max(values.max(), 1) * 0.015
        for y, value in enumerate(values):
            axis.text(value + pad, y, amount_label(value, 0), va="center", fontsize=8)
    figure.suptitle("Hiệu suất sản phẩm", x=0.035, ha="left",
                    fontsize=16, fontweight="bold")
    figure.text(0.035, 0.015,
                "Units sold = sum(quantity). Loại nhóm category Unknown khỏi bảng xếp hạng để không xếp hạng mã orphan như sản phẩm đã định danh.",
                fontsize=8.5, color=PALETTE["slate"])
    figure.tight_layout(rect=(0, 0.08, 1, 0.91))
    return save_figure(figure, "06_product_performance.png")


def chart_geography(data: dict[str, pd.DataFrame]) -> Path:
    figure, axes = plt.subplots(1, 2, figsize=(14, 6.6))

    markets = data["markets"].copy().sort_values("profit_margin", ascending=True)
    axes[0].barh(markets["market"], markets["profit_margin"],
                 color=PALETTE["blue"], height=0.62)
    axes[0].set_title("Profit margin theo market", loc="left",
                      fontsize=12, fontweight="bold")
    axes[0].set_xlabel("Profit / total sales")
    axes[0].xaxis.set_major_formatter(PercentFormatter(xmax=1))
    for y, row in enumerate(markets.itertuples(index=False)):
        axes[0].text(row.profit_margin + 0.002, y,
                     f"{row.profit_margin:.1%}  |  sales {amount_label(float(row.total_sales), 0)}",
                     va="center", fontsize=8)

    countries = data["countries"].copy().sort_values("total_sales", ascending=True)
    axes[1].barh(countries["country"], countries["total_sales"].astype(float),
                 color=PALETTE["gold"], height=0.68)
    axes[1].set_title("Top 10 quốc gia theo total sales", loc="left",
                      fontsize=12, fontweight="bold")
    axes[1].set_xlabel("Total sales (đơn vị theo nguồn)")
    axes[1].xaxis.set_major_formatter(FuncFormatter(compact_amount_formatter))
    pad = float(countries["total_sales"].max()) * 0.015
    for y, value in enumerate(countries["total_sales"].astype(float)):
        axes[1].text(value + pad, y, amount_label(value, 0), va="center", fontsize=8)

    unknown = data["unknown_market"]
    unknown_note = ""
    if not unknown.empty:
        unknown_note = (
            " Unknown market được tách khỏi xếp hạng: "
            f"{integer_label(float(unknown['sales_line_count'].iloc[0]))} dòng, "
            f"sales {amount_label(float(unknown['total_sales'].iloc[0]), 0)}."
        )
    figure.suptitle("Hiệu quả theo địa lý", x=0.04, ha="left",
                    fontsize=16, fontweight="bold")
    figure.text(0.04, 0.015,
                "Market margin dùng tổng profit / tổng sales. Quốc gia Unknown không nằm trong top 10." + unknown_note,
                fontsize=8.5, color=PALETTE["slate"])
    figure.tight_layout(rect=(0, 0.08, 1, 0.91))
    return save_figure(figure, "07_geography_performance.png")


def chart_rfm_sensitivity(data: dict[str, pd.DataFrame]) -> Path:
    frame = data["rfm_sensitivity"].copy()
    snapshot = pd.to_datetime(data["rfm_snapshot"]["snapshot_date"].iloc[0]).strftime("%Y-%m-%d")
    frame["customer_risk_rate"] = frame["customers_at_risk"] / frame["customer_population"]
    frame["vip_risk_rate"] = frame["vip_customers_at_risk"] / frame["vip_population"]

    figure, axes = plt.subplots(1, 2, figsize=(12, 5.4))
    panels = [
        ("customers_at_risk", "customer_risk_rate", "All customers", PALETTE["blue"]),
        ("vip_customers_at_risk", "vip_risk_rate", "VIP customers", PALETTE["orange"]),
    ]
    for axis, (count_col, rate_col, title, color) in zip(axes, panels, strict=True):
        x = range(len(frame))
        values = frame[count_col].astype(float)
        axis.bar(x, values, color=color, width=0.62)
        axis.set_xticks(list(x), [f"{int(value)} ngày" for value in frame["threshold_days"]])
        axis.set_title(title, loc="left", fontweight="bold")
        axis.set_ylabel("Số khách hàng")
        axis.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: integer_label(v)))
        for index, (_, row) in enumerate(frame.iterrows()):
            axis.text(index, float(row[count_col]) + max(values) * 0.025,
                      f"{integer_label(float(row[count_col]))}\n{float(row[rate_col]):.1%}",
                      ha="center", va="bottom", fontsize=9)
        axis.set_ylim(0, max(values) * 1.22)

    figure.suptitle("Độ nhạy của nhãn inactivity risk", x=0.04, ha="left",
                    fontsize=16, fontweight="bold")
    figure.text(0.04, 0.015,
                f"Snapshot {snapshot}. Mỗi nhãn là recency_days ≥ ngưỡng; tỷ lệ dưới số lượng dùng population tương ứng. "
                "Đây là heuristic, không phải churn label thực tế.",
                fontsize=8.5, color=PALETTE["slate"])
    figure.tight_layout(rect=(0, 0.09, 1, 0.91))
    return save_figure(figure, "08_rfm_risk_sensitivity.png")


def chart_customer_region_behavior(data: dict[str, pd.DataFrame]) -> Path:
    frame = data["customer_regions"].copy()
    if not frame.empty:
        first_region = int(frame["matched_region_count"].min())
        last_region = int(frame["matched_region_count"].max())
        frame = (
            frame.set_index("matched_region_count")
            .reindex(range(first_region, last_region + 1), fill_value=0)
            .rename_axis("matched_region_count")
            .reset_index()
        )
    figure, axis = plt.subplots(figsize=(10, 5.2))
    values = frame["customer_count"].astype(float)
    labels = [str(int(value)) for value in frame["matched_region_count"]]
    axis.bar(labels, values, color=PALETTE["blue_light"], width=0.68)
    axis.set_title("Số region khớp được trong lịch sử giao dịch của khách hàng",
                   loc="left", fontsize=13, fontweight="bold")
    axis.set_xlabel("Số region_code dimension khác nhau đã khớp")
    axis.set_ylabel("Số khách hàng")
    axis.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: integer_label(v)))
    for index, value in enumerate(values):
        axis.text(index, value + max(values) * 0.015, integer_label(value),
                  ha="center", fontsize=8)

    orphan_customers = int(
        data["customer_regions"]["customers_with_orphan_region_activity"].sum()
    )
    figure.text(0.02, 0.015,
                f"Tổng hợp trên customer mart; khách hàng có hoạt động region orphan: {orphan_customers}. "
                "Số region không đồng nghĩa với số market.",
                fontsize=8.5, color=PALETTE["slate"])
    figure.tight_layout(rect=(0, 0.08, 1, 1))
    return save_figure(figure, "09_customer_region_behavior.png")


def chart_customer_profile(data: dict[str, pd.DataFrame]) -> Path:
    frame = data["customer_profile"].copy()
    matrix = frame.pivot(index="gender", columns="occupation", values="customer_count").fillna(0)
    gender_order = [value for value in ["F", "M", "Unknown"] if value in matrix.index]
    gender_order += [value for value in matrix.index if value not in gender_order]
    matrix = matrix.reindex(index=gender_order)

    figure, axis = plt.subplots(figsize=(12, 5.2))
    sns.heatmap(
        matrix,
        cmap="Blues",
        annot=True,
        fmt=".0f",
        linewidths=1,
        linecolor="white",
        cbar_kws={"label": "Số khách hàng"},
        ax=axis,
        annot_kws={"fontsize": 9},
    )
    axis.set_xlabel("Occupation")
    axis.set_ylabel("Gender")
    axis.set_title("Phân bố khách hàng theo gender và occupation",
                   loc="left", fontsize=14, fontweight="bold", pad=14)
    figure.text(0.02, 0.015,
                "Nguồn là customer dimension; nhóm Unknown được giữ lại. Biểu đồ chỉ hiển thị số liệu tổng hợp.",
                fontsize=8.5, color=PALETTE["slate"])
    figure.tight_layout(rect=(0, 0.08, 1, 1))
    return save_figure(figure, "10_customer_profile.png")


def main() -> None:
    if not WAREHOUSE_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB warehouse not found: {WAREHOUSE_PATH}. Run DLT ingestion and dbt first."
        )

    setup_style()
    with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as connection:
        check_marts(connection)
        data = load_chart_data(connection)
        validate_reconciliation(data)

    chart_builders = [
        chart_executive_overview,
        chart_discount_profitability,
        chart_segment_profitability,
        chart_monthly_performance,
        chart_category_mix,
        chart_product_performance,
        chart_geography,
        chart_rfm_sensitivity,
        chart_customer_region_behavior,
        chart_customer_profile,
    ]
    outputs = [builder(data) for builder in chart_builders]

    print(f"Generated {len(outputs)} charts from {GOLD_SCHEMA}.")
    print(f"Warehouse (read-only): {WAREHOUSE_PATH}")
    for output in outputs:
        print(f"- {output.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
