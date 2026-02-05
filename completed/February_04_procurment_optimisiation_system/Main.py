import pandas as pd
from pathlib import Path

# ============================================================
# Phase 1: Load Data & Cleansing Pipeline
# ============================================================

DATA_DIR = Path(r"C:\Users\Samue\OneDrive\Documents\OneDrive\Projecs\ai-skills-challenge-log\challenge_data\February_04_2026")


# ---- Load raw data ----
def load_data():
    purchase_orders = pd.read_csv(DATA_DIR / "purchase_orders.csv")
    department_budgets = pd.read_csv(DATA_DIR / "department_budgets.csv")
    vendor_info = pd.read_csv(DATA_DIR / "vendor_information.csv")
    return purchase_orders, department_budgets, vendor_info


# ---- Cleansing Pipeline ----
def cleanse_purchase_orders(df):
    raw_count = len(df)
    issues = []

    # 1. Strip whitespace from string columns
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())

    # 2. Standardise column names
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # 3. Remove duplicate PO rows
    dupes = df.duplicated(subset="po_id", keep="first").sum()
    if dupes:
        issues.append(f"Removed {dupes} duplicate PO rows")
        df = df.drop_duplicates(subset="po_id", keep="first")

    # 4. Parse dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = df["date"].isna().sum()
    if bad_dates:
        issues.append(f"{bad_dates} unparseable dates set to NaT")

    # 5. Ensure numeric types
    for col in ["quantity", "unit_price", "total_amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 6. Recalculate & validate total_amount
    expected = (df["quantity"] * df["unit_price"]).round(2)
    mismatch = (df["total_amount"] - expected).abs() > 0.01
    n_mismatch = mismatch.sum()
    if n_mismatch:
        issues.append(f"Corrected {n_mismatch} total_amount mismatches (qty * unit_price)")
        df.loc[mismatch, "total_amount"] = expected[mismatch]

    # 7. Flag missing contract IDs
    missing_contracts = df["contract_id"].isna().sum()
    if missing_contracts:
        issues.append(f"{missing_contracts} POs have no contract_id (spot purchases)")

    # 8. Standardise department names (title case, preserve abbreviations)
    ABBREVIATIONS = {"It": "IT", "Hr": "HR"}
    df["department"] = df["department"].str.title().replace(ABBREVIATIONS)

    # 9. Standardise payment terms
    df["payment_terms"] = df["payment_terms"].str.title()

    # 10. Flag negative or zero amounts
    bad_amounts = (df["total_amount"] <= 0).sum()
    if bad_amounts:
        issues.append(f"{bad_amounts} POs with zero/negative total_amount")

    print(f"\n{'='*60}")
    print("PURCHASE ORDERS CLEANSING REPORT")
    print(f"{'='*60}")
    print(f"  Raw rows loaded       : {raw_count}")
    print(f"  Rows after cleansing  : {len(df)}")
    print(f"  Issues found & fixed  : {len(issues)}")
    for i, issue in enumerate(issues, 1):
        print(f"    {i}. {issue}")
    print(f"  Columns               : {list(df.columns)}")
    print(f"  Date range            : {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  Unique vendors        : {df['vendor_id'].nunique()}")
    print(f"  Unique departments    : {df['department'].nunique()}")
    print(f"  Total spend           : ${df['total_amount'].sum():,.2f}")

    return df


def cleanse_department_budgets(df):
    raw_count = len(df)
    issues = []

    # 1. Strip whitespace from string columns
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())

    # 2. Standardise column names
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # 3. Remove duplicate departments
    dupes = df.duplicated(subset="department", keep="first").sum()
    if dupes:
        issues.append(f"Removed {dupes} duplicate department rows")
        df = df.drop_duplicates(subset="department", keep="first")

    # 4. Parse budget_utilization (remove % sign -> float)
    df["budget_utilization"] = (
        df["budget_utilization"]
        .astype(str)
        .str.replace("%", "", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )
    issues.append("Parsed budget_utilization from '68.5%' -> 68.5 (float)")

    # 5. Ensure numeric budget columns
    budget_cols = ["annual_budget", "quarterly_budget", "current_quarter_spent", "approval_limit"]
    for col in budget_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 6. Validate quarterly_budget ~ annual_budget / 4
    expected_q = (df["annual_budget"] / 4).round(2)
    q_mismatch = (df["quarterly_budget"] - expected_q).abs() > 1
    n_q_mismatch = q_mismatch.sum()
    if n_q_mismatch:
        issues.append(f"{n_q_mismatch} quarterly_budget values don't match annual/4")

    # 7. Standardise department names (preserve abbreviations)
    ABBREVIATIONS = {"It": "IT", "Hr": "HR"}
    df["department"] = df["department"].str.title().replace(ABBREVIATIONS)

    print(f"\n{'='*60}")
    print("DEPARTMENT BUDGETS CLEANSING REPORT")
    print(f"{'='*60}")
    print(f"  Raw rows loaded       : {raw_count}")
    print(f"  Rows after cleansing  : {len(df)}")
    print(f"  Issues found & fixed  : {len(issues)}")
    for i, issue in enumerate(issues, 1):
        print(f"    {i}. {issue}")
    print(f"  Departments           : {list(df['department'])}")
    print(f"  Total annual budget   : ${df['annual_budget'].sum():,.2f}")

    return df


def cleanse_vendor_info(df):
    raw_count = len(df)
    issues = []

    # 1. Strip whitespace from string columns
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())

    # 2. Standardise column names
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # 3. Remove duplicate vendors
    dupes = df.duplicated(subset="vendor_id", keep="first").sum()
    if dupes:
        issues.append(f"Removed {dupes} duplicate vendor rows")
        df = df.drop_duplicates(subset="vendor_id", keep="first")

    # 4. Parse contract_expiry to datetime
    df["contract_expiry"] = pd.to_datetime(df["contract_expiry"], errors="coerce")
    bad_dates = df["contract_expiry"].isna().sum()
    if bad_dates:
        issues.append(f"{bad_dates} unparseable contract_expiry dates")

    # 5. Flag expired contracts
    today = pd.Timestamp.today().normalize()
    df["contract_expired"] = df["contract_expiry"] < today
    n_expired = df["contract_expired"].sum()
    if n_expired:
        issues.append(f"{n_expired} vendors have expired contracts")

    # 6. Ensure numeric ratings
    for col in ["delivery_rating", "quality_rating"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 7. Parse volume discount tiers -> extract threshold and percentage
    for tier in ["volume_discount_tier_1", "volume_discount_tier_2", "volume_discount_tier_3"]:
        # e.g. "5% over $10000" -> pct=5.0, threshold=10000
        pct_col = tier + "_pct"
        thresh_col = tier + "_threshold"
        df[pct_col] = df[tier].str.extract(r"(\d+(?:\.\d+)?)%").astype(float)
        df[thresh_col] = df[tier].str.extract(r"\$(\d+(?:\.\d+)?)").astype(float)
    issues.append("Parsed volume discount tiers into numeric pct & threshold columns")

    # 8. Standardise payment terms
    df["payment_terms"] = df["payment_terms"].str.title()

    print(f"\n{'='*60}")
    print("VENDOR INFORMATION CLEANSING REPORT")
    print(f"{'='*60}")
    print(f"  Raw rows loaded       : {raw_count}")
    print(f"  Rows after cleansing  : {len(df)}")
    print(f"  Issues found & fixed  : {len(issues)}")
    for i, issue in enumerate(issues, 1):
        print(f"    {i}. {issue}")
    print(f"  Vendors               : {df['vendor_id'].nunique()}")
    print(f"  Expired contracts     : {df['contract_expired'].sum()}")
    print(f"  Avg delivery rating   : {df['delivery_rating'].mean():.2f}")
    print(f"  Avg quality rating    : {df['quality_rating'].mean():.2f}")

    return df


def run_cleansing_pipeline():
    print("Loading raw data...")
    po_raw, budgets_raw, vendors_raw = load_data()

    print(f"  purchase_orders   : {po_raw.shape}")
    print(f"  department_budgets: {budgets_raw.shape}")
    print(f"  vendor_information: {vendors_raw.shape}")

    po = cleanse_purchase_orders(po_raw.copy())
    budgets = cleanse_department_budgets(budgets_raw.copy())
    vendors = cleanse_vendor_info(vendors_raw.copy())

    print(f"\n{'='*60}")
    print("CLEANSING PIPELINE COMPLETE")
    print(f"{'='*60}")

    return po, budgets, vendors


# ============================================================
# Phase 2: Basic Spend Analysis
# ============================================================

def spend_analysis(po, budgets):
    print(f"\n{'='*60}")
    print("PHASE 2: BASIC SPEND ANALYSIS")
    print(f"{'='*60}")

    # --- By Vendor ---
    by_vendor = (
        po.groupby(["vendor_id", "vendor_name"])
        .agg(total_spend=("total_amount", "sum"),
             po_count=("po_id", "count"),
             avg_po_size=("total_amount", "mean"))
        .sort_values("total_spend", ascending=False)
        .reset_index()
    )
    by_vendor["spend_share"] = (by_vendor["total_spend"] / by_vendor["total_spend"].sum() * 100).round(1)

    print(f"\n  SPEND BY VENDOR (Top 10)")
    print(f"  {'Vendor':<25} {'Spend':>12} {'POs':>5} {'Avg PO':>10} {'Share':>7}")
    print(f"  {'-'*60}")
    for _, r in by_vendor.head(10).iterrows():
        print(f"  {r['vendor_name']:<25} ${r['total_spend']:>10,.2f} {r['po_count']:>5} ${r['avg_po_size']:>8,.2f} {r['spend_share']:>6.1f}%")

    # --- By Department ---
    by_dept = (
        po.groupby("department")
        .agg(total_spend=("total_amount", "sum"),
             po_count=("po_id", "count"),
             avg_po_size=("total_amount", "mean"),
             unique_vendors=("vendor_id", "nunique"))
        .sort_values("total_spend", ascending=False)
        .reset_index()
    )
    by_dept["spend_share"] = (by_dept["total_spend"] / by_dept["total_spend"].sum() * 100).round(1)

    # Merge with budgets to show utilization
    by_dept = by_dept.merge(
        budgets[["department", "annual_budget", "quarterly_budget"]],
        on="department", how="left"
    )

    print(f"\n  SPEND BY DEPARTMENT")
    print(f"  {'Dept':<15} {'Spend':>12} {'POs':>5} {'Vendors':>8} {'Annual Budget':>14} {'Share':>7}")
    print(f"  {'-'*65}")
    for _, r in by_dept.iterrows():
        budget_str = f"${r['annual_budget']:>11,.2f}" if pd.notna(r['annual_budget']) else "    N/A     "
        print(f"  {r['department']:<15} ${r['total_spend']:>10,.2f} {r['po_count']:>5} {r['unique_vendors']:>8} {budget_str} {r['spend_share']:>6.1f}%")

    # --- By Month ---
    po["month"] = po["date"].dt.to_period("M")
    by_month = (
        po.groupby("month")
        .agg(total_spend=("total_amount", "sum"),
             po_count=("po_id", "count"))
        .reset_index()
    )

    print(f"\n  SPEND BY MONTH")
    print(f"  {'Month':<12} {'Spend':>12} {'POs':>5}")
    print(f"  {'-'*32}")
    for _, r in by_month.iterrows():
        bar = "#" * int(r["total_spend"] / 3000)
        print(f"  {str(r['month']):<12} ${r['total_spend']:>10,.2f} {r['po_count']:>5}  {bar}")

    # --- By Category ---
    by_cat = (
        po.groupby("category")
        .agg(total_spend=("total_amount", "sum"),
             po_count=("po_id", "count"),
             avg_unit_price=("unit_price", "mean"))
        .sort_values("total_spend", ascending=False)
        .reset_index()
    )
    by_cat["spend_share"] = (by_cat["total_spend"] / by_cat["total_spend"].sum() * 100).round(1)

    print(f"\n  SPEND BY CATEGORY")
    print(f"  {'Category':<20} {'Spend':>12} {'POs':>5} {'Share':>7}")
    print(f"  {'-'*47}")
    for _, r in by_cat.iterrows():
        print(f"  {r['category']:<20} ${r['total_spend']:>10,.2f} {r['po_count']:>5} {r['spend_share']:>6.1f}%")

    return by_vendor, by_dept, by_month, by_cat


# ============================================================
# Phase 3: Vendor Consolidation Opportunities & Savings
# ============================================================

def vendor_consolidation(po, vendors):
    print(f"\n{'='*60}")
    print("PHASE 3: VENDOR CONSOLIDATION OPPORTUNITIES")
    print(f"{'='*60}")

    # Find items supplied by multiple vendors
    item_vendors = (
        po.groupby("item_description")
        .agg(vendor_count=("vendor_id", "nunique"),
             vendors=("vendor_name", lambda x: list(x.unique())),
             vendor_ids=("vendor_id", lambda x: list(x.unique())),
             total_qty=("quantity", "sum"),
             total_spend=("total_amount", "sum"),
             min_price=("unit_price", "min"),
             max_price=("unit_price", "max"),
             avg_price=("unit_price", "mean"))
        .reset_index()
    )

    multi_vendor_items = item_vendors[item_vendors["vendor_count"] > 1].sort_values("total_spend", ascending=False)

    print(f"\n  Items purchased from MULTIPLE vendors ({len(multi_vendor_items)} found):")
    print(f"  {'-'*70}")

    total_potential_savings = 0.0

    for _, item in multi_vendor_items.iterrows():
        price_spread = item["max_price"] - item["min_price"]
        savings_if_consolidated = item["total_qty"] * (item["avg_price"] - item["min_price"])
        total_potential_savings += savings_if_consolidated

        print(f"\n  Item: {item['item_description']}")
        print(f"    Vendors         : {', '.join(item['vendors'])}")
        print(f"    Total qty       : {item['total_qty']:,.0f}")
        print(f"    Price range     : ${item['min_price']:.2f} - ${item['max_price']:.2f} (spread: ${price_spread:.2f})")
        print(f"    Current spend   : ${item['total_spend']:,.2f}")
        print(f"    Savings at best : ${savings_if_consolidated:,.2f}")

        # Show per-vendor breakdown
        item_pos = po[po["item_description"] == item["item_description"]]
        vendor_detail = (
            item_pos.groupby(["vendor_id", "vendor_name"])
            .agg(qty=("quantity", "sum"), avg_price=("unit_price", "mean"), spend=("total_amount", "sum"))
            .reset_index()
        )
        for _, v in vendor_detail.iterrows():
            marker = " <-- BEST PRICE" if v["avg_price"] == item["min_price"] else ""
            print(f"      {v['vendor_name']:<25} qty={v['qty']:>6,.0f}  avg=${v['avg_price']:.2f}  spend=${v['spend']:,.2f}{marker}")

    # Volume discount opportunities
    print(f"\n  VOLUME DISCOUNT OPPORTUNITIES")
    print(f"  {'-'*70}")

    vendor_spend = po.groupby("vendor_id")["total_amount"].sum().reset_index()
    vendor_spend = vendor_spend.merge(vendors[["vendor_id", "vendor_name",
                                                "volume_discount_tier_1_pct", "volume_discount_tier_1_threshold",
                                                "volume_discount_tier_2_pct", "volume_discount_tier_2_threshold",
                                                "volume_discount_tier_3_pct", "volume_discount_tier_3_threshold"]],
                                       on="vendor_id", how="left")

    volume_savings = 0.0
    for _, v in vendor_spend.iterrows():
        spend = v["total_amount"]
        discount_pct = 0
        tier_hit = ""
        if pd.notna(v["volume_discount_tier_3_threshold"]) and spend >= v["volume_discount_tier_3_threshold"]:
            discount_pct = v["volume_discount_tier_3_pct"]
            tier_hit = "Tier 3"
        elif pd.notna(v["volume_discount_tier_2_threshold"]) and spend >= v["volume_discount_tier_2_threshold"]:
            discount_pct = v["volume_discount_tier_2_pct"]
            tier_hit = "Tier 2"
        elif pd.notna(v["volume_discount_tier_1_threshold"]) and spend >= v["volume_discount_tier_1_threshold"]:
            discount_pct = v["volume_discount_tier_1_pct"]
            tier_hit = "Tier 1"

        if discount_pct > 0:
            saving = spend * discount_pct / 100
            volume_savings += saving
            print(f"  {v['vendor_name']:<25} spend=${spend:>10,.2f}  {tier_hit} ({discount_pct}%)  save=${saving:,.2f}")

    print(f"\n  CONSOLIDATION SUMMARY")
    print(f"  {'-'*40}")
    print(f"    Price consolidation savings : ${total_potential_savings:,.2f}")
    print(f"    Volume discount savings     : ${volume_savings:,.2f}")
    print(f"    TOTAL POTENTIAL SAVINGS      : ${total_potential_savings + volume_savings:,.2f}")

    return multi_vendor_items, total_potential_savings, volume_savings


# ============================================================
# Phase 4: Department Efficiency Scoring & Red Flags
# ============================================================

def department_efficiency(po, budgets):
    print(f"\n{'='*60}")
    print("PHASE 4: DEPARTMENT EFFICIENCY SCORING & RED FLAGS")
    print(f"{'='*60}")

    # Build metrics per department
    dept_metrics = (
        po.groupby("department")
        .agg(total_spend=("total_amount", "sum"),
             po_count=("po_id", "count"),
             avg_po_size=("total_amount", "mean"),
             unique_vendors=("vendor_id", "nunique"),
             unique_categories=("category", "nunique"),
             contracted=("contract_id", lambda x: x.notna().sum()),
             spot=("contract_id", lambda x: x.isna().sum()))
        .reset_index()
    )
    dept_metrics["contract_rate"] = (dept_metrics["contracted"] / dept_metrics["po_count"] * 100).round(1)

    # Merge with budgets
    dept_metrics = dept_metrics.merge(budgets[["department", "annual_budget", "quarterly_budget",
                                                "current_quarter_spent", "budget_utilization", "approval_limit"]],
                                       on="department", how="left")

    # Scoring (0-100 scale)
    # Factors: contract_rate (higher=better), budget_utilization (moderate=better),
    #          avg_po_size (higher=better, fewer small POs), vendor consolidation
    scores = []
    red_flags = {}

    for _, d in dept_metrics.iterrows():
        dept = d["department"]
        flags = []
        score = 0

        # Contract compliance score (0-30 pts)
        contract_score = min(d["contract_rate"] / 100 * 30, 30)
        score += contract_score
        if d["contract_rate"] < 40:
            flags.append(f"LOW CONTRACT RATE: {d['contract_rate']}% of POs are spot purchases")

        # Budget discipline (0-25 pts) - sweet spot is 60-85% utilization
        if pd.notna(d["budget_utilization"]):
            if 60 <= d["budget_utilization"] <= 85:
                budget_score = 25
            elif d["budget_utilization"] < 60:
                budget_score = d["budget_utilization"] / 60 * 20
                flags.append(f"UNDERUTILIZED BUDGET: {d['budget_utilization']}% used")
            else:
                budget_score = max(0, 25 - (d["budget_utilization"] - 85) * 2)
                if d["budget_utilization"] > 90:
                    flags.append(f"NEAR BUDGET LIMIT: {d['budget_utilization']}% used")
        else:
            budget_score = 0
            flags.append("NO BUDGET DATA AVAILABLE")
        score += budget_score

        # PO efficiency (0-20 pts) - prefer fewer, larger POs
        if d["po_count"] > 0:
            if d["avg_po_size"] >= 5000:
                po_score = 20
            elif d["avg_po_size"] >= 2000:
                po_score = 15
            elif d["avg_po_size"] >= 1000:
                po_score = 10
            else:
                po_score = 5
                flags.append(f"SMALL AVG PO SIZE: ${d['avg_po_size']:,.2f} - consider bundling orders")
        else:
            po_score = 0
        score += po_score

        # Vendor concentration (0-15 pts) - not too many, not too few per PO
        if d["unique_vendors"] <= 3:
            vendor_score = 15
        elif d["unique_vendors"] <= 6:
            vendor_score = 10
        else:
            vendor_score = 5
            flags.append(f"VENDOR FRAGMENTATION: {d['unique_vendors']} vendors used")
        score += vendor_score

        # Approval limit checks (0-10 pts)
        if pd.notna(d["approval_limit"]):
            over_limit = po[(po["department"] == dept) & (po["total_amount"] > d["approval_limit"])]
            if len(over_limit) == 0:
                approval_score = 10
            else:
                approval_score = max(0, 10 - len(over_limit) * 2)
                flags.append(f"OVER APPROVAL LIMIT: {len(over_limit)} POs exceed ${d['approval_limit']:,.0f} limit")
        else:
            approval_score = 5
        score += approval_score

        score = round(score, 1)
        scores.append(score)
        red_flags[dept] = flags

    dept_metrics["efficiency_score"] = scores

    # Rating label
    def rating(s):
        if s >= 80: return "EXCELLENT"
        if s >= 65: return "GOOD"
        if s >= 50: return "FAIR"
        return "NEEDS IMPROVEMENT"

    dept_metrics["rating"] = dept_metrics["efficiency_score"].apply(rating)
    dept_metrics = dept_metrics.sort_values("efficiency_score", ascending=False)

    print(f"\n  DEPARTMENT SCORECARD")
    print(f"  {'Dept':<15} {'Score':>6} {'Rating':<18} {'Spend':>12} {'POs':>5} {'Contract%':>10}")
    print(f"  {'-'*70}")
    for _, r in dept_metrics.iterrows():
        print(f"  {r['department']:<15} {r['efficiency_score']:>5.1f} {r['rating']:<18} ${r['total_spend']:>10,.2f} {r['po_count']:>5} {r['contract_rate']:>9.1f}%")

    print(f"\n  RED FLAGS")
    print(f"  {'-'*60}")
    for dept, flags in red_flags.items():
        if flags:
            print(f"\n  {dept}:")
            for flag in flags:
                print(f"    [!] {flag}")

    if not any(red_flags.values()):
        print("  No red flags detected.")

    return dept_metrics, red_flags


# ============================================================
# Phase 5: Automated Purchase Order Anomaly Detection
# ============================================================

def anomaly_detection(po, budgets):
    print(f"\n{'='*60}")
    print("PHASE 5: AUTOMATED PO ANOMALY DETECTION")
    print(f"{'='*60}")

    anomalies = []

    # 1. Price anomalies - unit price >2 std devs from mean for the same item
    print(f"\n  1. PRICE ANOMALIES (unit price outliers per item)")
    print(f"  {'-'*60}")
    items_with_multiple = po.groupby("item_description").filter(lambda x: len(x) > 1)
    item_stats = items_with_multiple.groupby("item_description")["unit_price"].agg(["mean", "std"]).reset_index()
    item_stats = item_stats[item_stats["std"] > 0]

    price_anomaly_count = 0
    for _, stats in item_stats.iterrows():
        item = stats["item_description"]
        mean_price = stats["mean"]
        std_price = stats["std"]
        item_pos = po[po["item_description"] == item]
        for _, p in item_pos.iterrows():
            z_score = abs(p["unit_price"] - mean_price) / std_price if std_price > 0 else 0
            if z_score > 1.5:
                price_anomaly_count += 1
                direction = "ABOVE" if p["unit_price"] > mean_price else "BELOW"
                anomalies.append({
                    "type": "Price Anomaly",
                    "po_id": p["po_id"],
                    "detail": f"{item}: ${p['unit_price']:.2f} is {direction} avg ${mean_price:.2f} (z={z_score:.1f})"
                })
                print(f"    {p['po_id']}: {item} at ${p['unit_price']:.2f} vs avg ${mean_price:.2f} ({direction}, z={z_score:.1f})")

    if price_anomaly_count == 0:
        print(f"    No significant price anomalies detected.")

    # 2. High-value PO anomalies (>$10K single PO)
    print(f"\n  2. HIGH-VALUE POs (>$10,000)")
    print(f"  {'-'*60}")
    high_value = po[po["total_amount"] > 10000].sort_values("total_amount", ascending=False)
    for _, p in high_value.iterrows():
        contract_status = "CONTRACTED" if pd.notna(p["contract_id"]) else "SPOT PURCHASE"
        anomalies.append({
            "type": "High Value",
            "po_id": p["po_id"],
            "detail": f"${p['total_amount']:,.2f} - {p['item_description']} ({contract_status})"
        })
        print(f"    {p['po_id']}: ${p['total_amount']:>10,.2f} | {p['department']:<15} | {p['item_description']:<30} | {contract_status}")

    # 3. Approval limit breaches
    print(f"\n  3. APPROVAL LIMIT BREACHES")
    print(f"  {'-'*60}")
    po_with_limits = po.merge(budgets[["department", "approval_limit"]], on="department", how="left")
    breaches = po_with_limits[po_with_limits["total_amount"] > po_with_limits["approval_limit"]]
    if len(breaches) > 0:
        for _, b in breaches.iterrows():
            overage = b["total_amount"] - b["approval_limit"]
            anomalies.append({
                "type": "Approval Breach",
                "po_id": b["po_id"],
                "detail": f"${b['total_amount']:,.2f} exceeds ${b['approval_limit']:,.0f} limit by ${overage:,.2f}"
            })
            print(f"    {b['po_id']}: ${b['total_amount']:>10,.2f} exceeds {b['department']} limit ${b['approval_limit']:>8,.0f} (over by ${overage:,.2f})")
    else:
        print(f"    No approval limit breaches found.")

    # 4. Spot purchase concentration
    print(f"\n  4. SPOT PURCHASE PATTERNS (no contract)")
    print(f"  {'-'*60}")
    spot = po[po["contract_id"].isna()]
    spot_by_dept = spot.groupby("department").agg(
        spot_count=("po_id", "count"),
        spot_spend=("total_amount", "sum")
    ).reset_index()

    total_by_dept = po.groupby("department")["po_id"].count().reset_index(name="total_pos")
    spot_by_dept = spot_by_dept.merge(total_by_dept, on="department")
    spot_by_dept["spot_rate"] = (spot_by_dept["spot_count"] / spot_by_dept["total_pos"] * 100).round(1)

    for _, s in spot_by_dept.sort_values("spot_rate", ascending=False).iterrows():
        flag = " [!] HIGH" if s["spot_rate"] > 60 else ""
        print(f"    {s['department']:<15} {s['spot_count']:>3} spot POs / {s['total_pos']:>3} total ({s['spot_rate']}%){flag}  spend=${s['spot_spend']:,.2f}")

    # 5. Duplicate / near-duplicate detection
    print(f"\n  5. POTENTIAL DUPLICATE ORDERS")
    print(f"  {'-'*60}")
    po["date_only"] = po["date"].dt.date
    dupes = po.groupby(["vendor_id", "item_description", "date_only"]).filter(lambda x: len(x) > 1)
    if len(dupes) > 0:
        for (vid, item, date), group in dupes.groupby(["vendor_id", "item_description", "date_only"]):
            po_ids = ", ".join(group["po_id"])
            anomalies.append({
                "type": "Potential Duplicate",
                "po_id": po_ids,
                "detail": f"{item} from {vid} on {date}"
            })
            print(f"    {po_ids}: {item} from {vid} on {date}")
    else:
        print(f"    No duplicate orders detected.")

    po.drop(columns=["date_only"], inplace=True)

    print(f"\n  ANOMALY SUMMARY: {len(anomalies)} anomalies detected")

    return anomalies


# ============================================================
# Phase 6: Executive Summary
# ============================================================

def executive_summary(po, budgets, vendors, by_vendor, dept_metrics, red_flags,
                      consolidation_savings, volume_savings, anomalies):
    total_spend = po["total_amount"].sum()
    total_budget = budgets["annual_budget"].sum()
    total_savings = consolidation_savings + volume_savings

    print(f"\n{'='*60}")
    print("PHASE 6: EXECUTIVE SUMMARY")
    print(f"{'='*60}")

    print(f"""
  PROCUREMENT OPTIMIZATION SYSTEM - EXECUTIVE REPORT
  Period: {po['date'].min().date()} to {po['date'].max().date()}
  {'='*55}

  KEY METRICS
  -----------------------------------------------
    Total Purchase Orders    : {len(po)}
    Total Spend              : ${total_spend:,.2f}
    Total Annual Budget      : ${total_budget:,.2f}
    Active Vendors           : {po['vendor_id'].nunique()}
    Active Departments       : {po['department'].nunique()}
    Avg PO Value             : ${total_spend / len(po):,.2f}

  SAVINGS OPPORTUNITIES
  -----------------------------------------------
    Vendor Price Consolidation : ${consolidation_savings:,.2f}
    Volume Discount Capture    : ${volume_savings:,.2f}
    TOTAL POTENTIAL SAVINGS     : ${total_savings:,.2f}
    Savings as % of Spend      : {total_savings / total_spend * 100:.1f}%

  TOP 3 VENDORS BY SPEND
  -----------------------------------------------""")
    for _, v in by_vendor.head(3).iterrows():
        print(f"    {v['vendor_name']:<25} ${v['total_spend']:>10,.2f} ({v['spend_share']}%)")

    print(f"""
  DEPARTMENT PERFORMANCE
  -----------------------------------------------""")
    for _, d in dept_metrics.iterrows():
        print(f"    {d['department']:<15} Score: {d['efficiency_score']:>5.1f}/100  [{d['rating']}]")

    # Count total red flags
    total_flags = sum(len(f) for f in red_flags.values())
    print(f"""
  RISK INDICATORS
  -----------------------------------------------
    Red flags raised         : {total_flags}
    Anomalies detected       : {len(anomalies)}
    Expired vendor contracts : {vendors['contract_expired'].sum()} of {len(vendors)}
    Spot purchase rate       : {po['contract_id'].isna().sum()}/{len(po)} POs ({po['contract_id'].isna().sum()/len(po)*100:.0f}%)

  RECOMMENDATIONS
  -----------------------------------------------""")

    recommendations = []

    # Consolidation recommendation
    if consolidation_savings > 0:
        recommendations.append(f"CONSOLIDATE vendors for duplicate items to save ${consolidation_savings:,.2f}")

    # Volume discount recommendation
    if volume_savings > 0:
        recommendations.append(f"LEVERAGE volume discounts across {len(by_vendor)} vendors to save ${volume_savings:,.2f}")

    # Contract coverage
    spot_rate = po["contract_id"].isna().sum() / len(po) * 100
    if spot_rate > 50:
        recommendations.append(f"IMPROVE contract coverage - {spot_rate:.0f}% of POs are spot purchases")

    # Expired contracts
    n_expired = vendors["contract_expired"].sum()
    if n_expired > 0:
        recommendations.append(f"RENEW {n_expired} expired vendor contracts to maintain negotiated rates")

    # Departments with red flags
    flagged_depts = [d for d, f in red_flags.items() if f]
    if flagged_depts:
        recommendations.append(f"REVIEW procurement practices in: {', '.join(flagged_depts)}")

    for i, rec in enumerate(recommendations, 1):
        print(f"    {i}. {rec}")

    print(f"\n  {'='*55}")
    print(f"  Report generated: {pd.Timestamp.today().strftime('%Y-%m-%d %H:%M')}")
    print(f"  {'='*55}\n")


# ---- Main ----
if __name__ == "__main__":
    # Phase 1
    purchase_orders, department_budgets, vendor_info = run_cleansing_pipeline()

    # Phase 2
    by_vendor, by_dept, by_month, by_cat = spend_analysis(purchase_orders, department_budgets)

    # Phase 3
    multi_vendor_items, consolidation_savings, volume_savings = vendor_consolidation(purchase_orders, vendor_info)

    # Phase 4
    dept_metrics, red_flags = department_efficiency(purchase_orders, department_budgets)

    # Phase 5
    anomalies = anomaly_detection(purchase_orders, department_budgets)

    # Phase 6
    executive_summary(purchase_orders, department_budgets, vendor_info,
                      by_vendor, dept_metrics, red_flags,
                      consolidation_savings, volume_savings, anomalies)
