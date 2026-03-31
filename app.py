import os
import re
import io
import csv

import pandas as pd
import streamlit as st

# ── Config ──
DISCOUNT_TIERS = {
    2: 0.10,  # Bundle of 2 → 10% off MRP
    3: 0.15,  # Bundle of 3 → 15% off MRP
}
SPECIAL_DISCOUNT_TIERS = {
    2: 0.95,  # Special Bundle of 2 → Price * 0.95
    3: 0.90,  # Special Bundle of 3 → Price * 0.90
}
DEFAULT_DISCOUNT = 0.0

DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "sample_data", "master_sku.csv")


# ── Core Logic ──
def split_bundle_sku(bundle_sku: str) -> list[str]:
    if not bundle_sku or not isinstance(bundle_sku, str):
        return []
    return re.findall(r"\d+[A-Z]+", bundle_sku.strip())


def parse_master_csv(file) -> dict[str, dict]:
    df = pd.read_csv(file)
    df.columns = df.columns.str.strip().str.lower()

    required = {"sku", "mrp", "cogs", "price"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Master CSV missing columns: {missing}")

    df["sku"] = df["sku"].astype(str).str.strip().str.upper()
    master = {}
    for _, row in df.iterrows():
        master[row["sku"]] = {
            "mrp": float(row["mrp"]),
            "cogs": float(row["cogs"]),
            "price": float(row["price"]),
        }
    return master


def calculate_bundles(master, bundles, special_set=None):
    results = []
    warnings = []
    special_set = special_set or set()

    for bundle_sku in bundles:
        parts = split_bundle_sku(bundle_sku)

        if not parts:
            warnings.append(f"Skipped '{bundle_sku}' — no valid SKU parts found")
            continue

        missing = [p for p in parts if p not in master]
        if missing:
            warnings.append(f"Skipped '{bundle_sku}' — missing SKUs: {missing}")
            continue

        total_mrp = sum(master[p]["mrp"] for p in parts)
        total_cogs = sum(master[p]["cogs"] for p in parts)
        num_parts = len(parts)
        is_special = bundle_sku in special_set

        if is_special:
            total_price = sum(master[p]["price"] for p in parts)
            multiplier = SPECIAL_DISCOUNT_TIERS.get(num_parts, 1.0)
            price = round(total_price * multiplier, 2)
        else:
            discount = DISCOUNT_TIERS.get(num_parts, DEFAULT_DISCOUNT)
            price = round(total_mrp * (1 - discount), 2)

        results.append({
            "bundle_sku": bundle_sku,
            "parts": parts,
            "bundle_type": f"Bundle of {num_parts}",
            "is_special": is_special,
            "total_mrp": round(total_mrp, 2),
            "total_cogs": round(total_cogs, 2),
            "price": price,
        })

    return results, warnings


def results_to_csv(results):
    if not results:
        return ""
    output = io.StringIO()
    max_parts = max(len(r["parts"]) for r in results)
    fieldnames = ["bundle_sku"]
    fieldnames += [f"part_{i+1}" for i in range(max_parts)]
    fieldnames += ["bundle_type", "is_special", "total_mrp", "total_cogs", "price"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for r in results:
        row = {
            "bundle_sku": r["bundle_sku"],
            "bundle_type": r["bundle_type"],
            "is_special": "Yes" if r["is_special"] else "No",
            "total_mrp": r["total_mrp"],
            "total_cogs": r["total_cogs"],
            "price": r["price"],
        }
        for i, part in enumerate(r["parts"]):
            row[f"part_{i+1}"] = part
        writer.writerow(row)
    return output.getvalue()


def results_to_dataframe(results):
    if not results:
        return pd.DataFrame()
    max_parts = max(len(r["parts"]) for r in results)
    rows = []
    for r in results:
        row = {"Bundle SKU": r["bundle_sku"]}
        for i in range(max_parts):
            row[f"Part {i+1}"] = r["parts"][i] if i < len(r["parts"]) else "—"
        row["Type"] = r["bundle_type"]
        row["Special"] = "Yes" if r["is_special"] else "—"
        row["MRP"] = r["total_mrp"]
        row["COGS"] = r["total_cogs"]
        row["Price"] = r["price"]
        rows.append(row)
    return pd.DataFrame(rows)


# ── Streamlit UI ──
st.set_page_config(page_title="Bundle Calculator", page_icon="📦", layout="wide")

st.markdown("""
<style>
    .block-container { max-width: 1100px; padding-top: 2rem; }
    .stDataFrame { font-size: 14px; }
    div[data-testid="stMetric"] {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 12px 16px;
    }
</style>
""", unsafe_allow_html=True)

st.title("Bundle Calculator")
st.caption("Upload master data and enter bundle SKUs to calculate pricing")

st.divider()

# ── Input Section ──
col_file, col_skus = st.columns([1, 2])

with col_file:
    st.subheader("1. Master SKU Data")

    master_option = st.radio(
        "Choose data source",
        ["Use default master data", "Upload CSV"],
        horizontal=True,
    )

    master_file = None
    if master_option == "Upload CSV":
        master_file = st.file_uploader(
            "Upload CSV with columns: sku, mrp, cogs, price",
            type=["csv"],
            key="master",
        )

    if master_option == "Use default master data" and os.path.exists(DEFAULT_CSV_PATH):
        default_df = pd.read_csv(DEFAULT_CSV_PATH)
        st.caption(f"Loaded {len(default_df)} SKUs from default data")
        with st.expander("Preview default data"):
            st.dataframe(default_df, use_container_width=True, hide_index=True)

with col_skus:
    st.subheader("2. Bundle SKUs")
    bundle_input = st.text_area(
        "Enter bundle SKUs — one per line or comma-separated",
        height=120,
        placeholder="e.g. 1209SI1526CB1185CC, 1071DM1527CB",
    )

    special_input = ""
    with st.expander("Special SKUs (optional)"):
        st.caption("Uses Price-based pricing: Price × 0.95 (Bundle of 2), Price × 0.90 (Bundle of 3)")
        special_input = st.text_area(
            "Enter special bundle SKUs",
            height=80,
            placeholder="e.g. 1209SI1526CB",
            key="special",
        )

st.divider()

# ── Determine if ready ──
has_master = (master_option == "Use default master data" and os.path.exists(DEFAULT_CSV_PATH)) or \
             (master_option == "Upload CSV" and master_file is not None)
can_calculate = has_master and bundle_input.strip() != ""

# ── Calculate ──
if st.button("Calculate Bundles", type="primary", disabled=not can_calculate, use_container_width=True):
    try:
        if master_option == "Upload CSV":
            master = parse_master_csv(master_file)
        else:
            master = parse_master_csv(DEFAULT_CSV_PATH)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    bundles = [
        s.strip().upper()
        for s in bundle_input.strip().replace("\n", ",").split(",")
        if s.strip()
    ]

    special_set = set()
    if special_input and special_input.strip():
        special_set = {
            s.strip().upper()
            for s in special_input.strip().replace("\n", ",").split(",")
            if s.strip()
        }

    with st.spinner("Calculating bundles..."):
        results, warnings = calculate_bundles(master, bundles, special_set)

    # ── Summary ──
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Bundles", len(bundles))
    c2.metric("Processed", len(results))
    c3.metric("Skipped", len(bundles) - len(results))

    # ── Warnings ──
    if warnings:
        with st.expander(f"Warnings ({len(warnings)})", expanded=False):
            for w in warnings:
                st.warning(w, icon="⚠️")

    # ── Results Table ──
    if results:
        st.subheader("Results")
        df = results_to_dataframe(results)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "MRP": st.column_config.NumberColumn(format="₹ %.2f"),
                "COGS": st.column_config.NumberColumn(format="₹ %.2f"),
                "Price": st.column_config.NumberColumn(format="₹ %.2f"),
            },
        )

        # ── Download ──
        csv_data = results_to_csv(results)
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name="bundle_results.csv",
            mime="text/csv",
            type="secondary",
        )
    elif not warnings:
        st.info("No results to display.")
