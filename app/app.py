"""
Jupyter Finance — Wealthsimple-inspired dashboard + chat.
Run with: streamlit run app/app.py (from repo root).
"""
import streamlit as st
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Page config and global CSS
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Jupyter Finance", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Global font and force dark text (fixes visibility in dark-mode browsers) */
html, body, [class*="css"], [data-testid="stMarkdown"], [data-testid="stHeader"] {
    font-family: 'Inter', sans-serif;
    color: #1a1a2e !important;
}

[data-testid="stAppViewContainer"] { background: #fafafa; }
[data-testid="stHeader"] { background: transparent; }

/* Chat: high-contrast, readable assistant messages */
div[data-testid="stChatMessage"] { align-items: flex-start; }
div[data-testid="stChatMessage"] div[data-testid="stMarkdown"] p,
div[data-testid="stChatMessage"] div[data-testid="stMarkdown"] {
    color: #1a1a2e !important; font-size: 0.95rem !important; line-height: 1.5 !important;
}
div[data-testid="stChatMessage"] > div:first-of-type + div {
    background: #ffffff !important; color: #1a1a2e !important;
    border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px 14px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

/* Compact dashboard */
.card {
    background: #ffffff; border-radius: 12px; padding: 16px 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 10px;
}
.metric-value { font-size: 1.8rem; font-weight: 700; color: #1a1a2e; line-height: 1.1; }

/* Darker contrast for labels/subtitles */
.metric-label {
    font-size: 0.72rem; font-weight: 600; color: #52525b; /* Darker gray */
    text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 2px;
}
.metric-sub { font-size: 0.8rem; font-weight: 600; margin-top: 2px; }

.positive { color: #16a34a; } /* Slightly darker green for contrast */
.negative { color: #dc2626; } /* Slightly darker red */

.section-title { font-size: 0.95rem; font-weight: 600; color: #1a1a2e; margin: 14px 0 8px 0; }

.insight-box {
    background: #f2f2f7; border-left: 4px solid #007aff; border-radius: 10px;
    padding: 10px 14px; margin-bottom: 6px; font-size: 0.82rem; color: #3a3a3c;
}

.budget-label { font-size: 0.8rem; font-weight: 600; color: #3a3a3c; margin-bottom: 1px; }
.budget-sub { font-size: 0.72rem; color: #52525b; margin-bottom: 4px; } /* Darker gray */

/* Fix Streamlit captions to be visible */
[data-testid="stCaptionContainer"] {
    color: #52525b !important;
}

/* Compact tables in chat */
.streamlit-dataframe { font-size: 0.8rem; max-height: 280px !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Library imports
# ---------------------------------------------------------------------------
try:
    from jupyter_finance.core import get_all_active_budgets, db_sql
    from jupyter_finance.categorization import (
        get_transactions_enriched, get_recurring_summary, run_enrichment,
        apply_user_friendly_category, detect_recurring, detect_unusual,
    )
    from jupyter_finance.agents import explore_agent, create_budget_agent, whatif_agent, whatif_compute, parse_date_range
    LIB_OK = True
except Exception as e:
    LIB_OK = False
    st.error(f"Cannot load jupyter_finance: {e}. Check .env and database.")

# ---------------------------------------------------------------------------
# Plotly theme helper
# ---------------------------------------------------------------------------
# Ensure all chart text (legend, titles, axis labels) is dark and visible
_LEGEND_FONT = dict(color="#1a1a2e", size=11)
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#1a1a2e", size=12),
    margin=dict(l=16, r=16, t=32, b=16),
    xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(color="#52525b", size=11)),
    yaxis=dict(showgrid=True, gridcolor="#f0f0f0", zeroline=False, tickfont=dict(color="#52525b", size=11)),
    hoverlabel=dict(bgcolor="#fff", font_size=13, bordercolor="#e0e0e0", font_color="#1a1a2e"),
    legend=dict(font=_LEGEND_FONT),
)
COLORS = ["#007aff", "#34c759", "#ff9500", "#ff3b30", "#5856d6", "#af52de", "#ff2d55", "#00c7be"]


def _styled_fig(fig):
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig

# ---------------------------------------------------------------------------
# Data helpers (safe — return empty DataFrames on error)
# ---------------------------------------------------------------------------

def _safe_transactions() -> pd.DataFrame:
    if not LIB_OK:
        return pd.DataFrame()
    try:
        df = get_transactions_enriched()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def _safe_balances() -> pd.DataFrame:
    if not LIB_OK:
        return pd.DataFrame()
    try:
        return db_sql("SELECT * FROM v_latest_account_balance")
    except Exception:
        return pd.DataFrame()


def _safe_accounts() -> pd.DataFrame:
    if not LIB_OK:
        return pd.DataFrame()
    try:
        return db_sql("SELECT account_id, name, type FROM accounts")
    except Exception:
        return pd.DataFrame()


def _safe_budget_df() -> pd.DataFrame:
    if not LIB_OK:
        return pd.DataFrame()
    try:
        return db_sql("""
            SELECT b.id, b.name, b.balance_limit, b.rules,
                   COALESCE(bb.current_balance, 0) AS current_balance,
                   COALESCE(bb.under_limit, true) AS under_limit
            FROM budget b
            LEFT JOIN v_latest_budget_batches bb ON bb.budget_id = b.id
            WHERE b.is_deleted = false
        """)
    except Exception:
        return pd.DataFrame()


def _safe_balance_history() -> pd.DataFrame:
    if not LIB_OK:
        return pd.DataFrame()
    try:
        return db_sql("""
            SELECT account_id, balances_current, balances_datetime
            FROM accounts_balance_history ORDER BY balances_datetime
        """)
    except Exception:
        return pd.DataFrame()


def _date_range(period: str):
    today = date.today()
    if period == "last_month":
        start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        end = today.replace(day=1) - timedelta(days=1)
    elif period == "last_3_months":
        start = today - relativedelta(months=3)
        end = today
    elif period == "last_6_months":
        start = today - relativedelta(months=6)
        end = today
    elif period == "last_12_months":
        start = today - relativedelta(months=12)
        end = today
    else:
        start = today.replace(day=1)
        end = today
    return start, end


# ===================================================================
# LAYOUT: left = dashboard (compact, max 2 per row), right = chat pane
# ===================================================================
CHART_H = 240
LEFT_COL, RIGHT_COL = st.columns([3, 1])

# Precompute dashboard data when LIB_OK
if LIB_OK:
    txn = _safe_transactions()
    bal = _safe_balances()
    accts = _safe_accounts()
    budgets = _safe_budget_df()
    today = date.today()
    if not bal.empty and not accts.empty:
        bal = bal.merge(accts[["account_id", "type"]], on="account_id", how="left")
    txn_d = txn.dropna(subset=["date"]) if (not txn.empty and "date" in txn.columns) else pd.DataFrame()
    if not txn_d.empty:
        latest_txn_date = txn_d["date"].max().date()
        active_month_start = latest_txn_date.replace(day=1)
        prev_m_end = active_month_start - timedelta(days=1)
        prev_m_start = prev_m_end.replace(day=1)
        this_month_txn = txn_d[(txn_d["date"].dt.date >= active_month_start) & (txn_d["date"].dt.date <= (active_month_start + relativedelta(months=1) - timedelta(days=1)))]
        prev_month_txn = txn_d[(txn_d["date"].dt.date >= prev_m_start) & (txn_d["date"].dt.date <= prev_m_end)]
        active_label = active_month_start.strftime("%B %Y")
    else:
        this_month_txn = pd.DataFrame()
        prev_month_txn = pd.DataFrame()
        active_label = "This Month"
    has_balance_data = not bal.empty and "balances_current" in bal.columns
    total_bal = bal["balances_current"].sum() if has_balance_data else 0
    spend_this = this_month_txn[this_month_txn["amount"] > 0]["amount"].sum() if not this_month_txn.empty else 0
    spend_prev = prev_month_txn[prev_month_txn["amount"] > 0]["amount"].sum() if not prev_month_txn.empty else 0
    income_this = abs(this_month_txn[this_month_txn["amount"] < 0]["amount"].sum()) if not this_month_txn.empty else 0
    net_cashflow = income_this - spend_this
    pct_change = ((spend_this - spend_prev) / spend_prev * 100) if spend_prev else 0
    checking_bal = bal[bal["type"] == "depository"]["balances_current"].sum() if has_balance_data and "type" in bal.columns else 0
    invest_bal = bal[bal["type"] == "investment"]["balances_current"].sum() if has_balance_data and "type" in bal.columns else 0
    if not has_balance_data and not txn_d.empty:
        total_bal = abs(txn_d[txn_d["amount"] < 0]["amount"].sum()) - txn_d[txn_d["amount"] > 0]["amount"].sum()
    card_data = [
        ("Income", income_this), ("Expenses", spend_this),
        ("Investments" if has_balance_data else "Net Cash Flow", invest_bal if has_balance_data else net_cashflow),
        ("Net Cash Flow" if has_balance_data else "Txns", net_cashflow if has_balance_data else float(len(txn))),
    ]
    if has_balance_data:
        card_data = [("Checking", checking_bal), ("Investments", invest_bal), ("Income", income_this), ("Net Cash Flow", net_cashflow)]
else:
    today = date.today()
    card_data = []
    this_month_txn = pd.DataFrame()
    budgets = pd.DataFrame()
    txn = pd.DataFrame()
    active_label = "This Month"
    has_balance_data = False
    total_bal = 0
    net_cashflow = 0
    pct_change = 0


def _classify_intent(msg: str) -> str:
    m = msg.strip().lower()
    if "enrich" in m or ("categoriz" in m and "run" in m):
        return "enrich"
    if "create" in m and "budget" in m:
        return "create_budget"
    if "what if" in m or "whatif" in m or ("projected" in m and ("spend" in m or "cut" in m or "no more" in m)):
        return "whatif"
    if "budget" in m and any(k in m for k in ("drill", "detail", "transaction", "merchant", "history", "breakdown")):
        return "budget_drilldown"
    if any(k in m for k in ("breakdown of", "drill into", "drill down", "detail of", "transactions for", "transactions in")):
        return "category_drilldown"
    if any(cat in m for cat in ("essential", "discretionary", "saving")) and any(k in m for k in ("breakdown", "detail", "drill", "transaction")):
        return "category_drilldown"
    if any(k in m for k in ("categor", "pie", "spending by", "breakdown")) or ("spending" in m and ("show" in m or "my" in m)):
        return "categorization_pie"
    if "budget" in m and any(k in m for k in ("over", "limit", "track", "overview", "progress")):
        return "budget_overview"
    if "over time" in m or "spending over" in m or "trend" in m:
        return "spending_over_time"
    if "income" in m and "expense" in m:
        return "income_vs_expenses"
    if "recurring" in m or "subscription" in m:
        return "recurring"
    if "saving" in m or "invest" in m:
        return "savings_tracking"
    if "anomal" in m or "unusual" in m or "alert" in m:
        return "anomalies"
    return "generic"


def _extract_drill_category(msg: str) -> str | None:
    """Extract category name for drill-down: essentials, discretionary, savings."""
    m = (msg or "").strip().lower()
    if "essential" in m:
        return "Essentials"
    if "discretionary" in m:
        return "Discretionary"
    if "saving" in m or "invest" in m:
        return "Savings & Investments"
    return None


def _handle_category_drilldown(user_msg=""):
    """Drill into a specific category: show spending by sub-type, top merchants, and transactions."""
    df = _safe_transactions()
    if df.empty:
        return "No transaction data.", None
    start, end, label = parse_date_range(user_msg) if LIB_OK else (_date_range("this_month")[0], _date_range("this_month")[1], "This Month")
    df = df.dropna(subset=["date"])
    df = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]
    spend = df[df["amount"] > 0].copy()
    cat_col = "user_friendly_category" if "user_friendly_category" in spend.columns else "personal_finance_category"
    if cat_col not in spend.columns:
        spend[cat_col] = "Uncategorized"
    target = _extract_drill_category(user_msg)
    if not target:
        return f"Which category? Try: 'Breakdown of **Essentials** in February' or 'Drill into **Discretionary**'.", None
    sub = spend[spend[cat_col].str.strip().str.lower() == target.lower()].copy()
    if sub.empty:
        return f"No **{target}** spending in **{label}** ({start} to {end}).", None
    total = sub["amount"].sum()
    charts = []
    if "personal_finance_category_detailed" in sub.columns:
        by_type = sub.groupby("personal_finance_category_detailed")["amount"].sum().reset_index()
        by_type = by_type.rename(columns={"personal_finance_category_detailed": "spending_type"})
        by_type["spending_type"] = by_type["spending_type"].fillna("Other").astype(str).str.replace("_", " ").str.title()
        by_type = by_type.sort_values("amount", ascending=False).head(12)
        if not by_type.empty:
            charts.append({"chart_type": "horizontal_bar", "data": by_type, "meta": {"x": "amount", "y": "spending_type", "caption": "Spending by type"}})
    by_merchant = sub.groupby("merchant_name")["amount"].sum().reset_index()
    by_merchant = by_merchant.rename(columns={"merchant_name": "merchant"})
    by_merchant = by_merchant.sort_values("amount", ascending=False).head(10)
    if not by_merchant.empty:
        charts.append({"chart_type": "horizontal_bar", "data": by_merchant, "meta": {"x": "amount", "y": "merchant", "caption": "Top merchants"}})
    txn_cols = ["date", "merchant_name", "amount"]
    txn_cols = [c for c in txn_cols if c in sub.columns]
    txn_list = sub[txn_cols].sort_values("amount", ascending=False).head(50).copy()
    txn_list = txn_list.rename(columns={"merchant_name": "merchant"})
    charts.append({"chart_type": "table", "data": txn_list, "meta": {"caption": "Transactions"}})
    title = f"**{target}** drill-down — **{label}** ({start} to {end}) • Total: ${total:,.2f}"
    return title, {"chart_type": "multi", "charts": charts, "data": pd.DataFrame()}


def _handle_categorization_pie(user_msg=""):
    df = _safe_transactions()
    if df.empty:
        return "No transaction data.", None
    start, end, label = parse_date_range(user_msg) if LIB_OK else (_date_range("this_month")[0], _date_range("this_month")[1], "This Month")
    df = df.dropna(subset=["date"])
    df = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]
    spend = df[df["amount"] > 0].copy()
    cat_col = "user_friendly_category" if "user_friendly_category" in spend.columns else "personal_finance_category"
    if cat_col not in spend.columns:
        spend[cat_col] = "Uncategorized"
    agg = spend.groupby(cat_col)["amount"].sum().reset_index()
    agg.columns = ["category", "total_amount"]
    agg = agg[agg["total_amount"] > 0].sort_values("total_amount", ascending=False)
    if agg.empty:
        return f"No spending data for {label}.", None
    return f"Spending by category — **{label}** ({start} to {end}):", {"chart_type": "donut", "data": agg, "meta": {"names": "category", "values": "total_amount"}}


def _handle_budget_overview():
    df = _safe_budget_df()
    if df.empty:
        return "No active budgets.", None
    df = df.fillna(0)
    return "Budget overview:", {"chart_type": "budget_bar", "data": df}


def _handle_spending_over_time(user_msg=""):
    if LIB_OK:
        start, end, label = parse_date_range(user_msg)
    else:
        start, end = _date_range("this_month")
        label = "This Month"
    df = _safe_transactions()
    if df.empty:
        return "No transaction data.", None
    df = df.dropna(subset=["date"])
    df = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]
    spend = df[df["amount"] > 0].copy()
    if spend.empty:
        return f"No spending in {label}.", None
    spend["day"] = spend["date"].dt.date
    daily = spend.groupby("day")["amount"].sum().reset_index()
    daily.columns = ["date", "amount"]
    return f"Spending over time — **{label}** ({start} to {end}):", {"chart_type": "line", "data": daily, "meta": {"x": "date", "y": "amount"}}


def _handle_income_vs_expenses(user_msg=""):
    if LIB_OK and user_msg:
        start, end, label = parse_date_range(user_msg)
    else:
        start, end = _date_range("last_6_months")
        label = "Last 6 Months"
    df = _safe_transactions()
    if df.empty:
        return "No transaction data.", None
    df = df.dropna(subset=["date"])
    df = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]
    df["month"] = df["date"].dt.to_period("M").astype(str)
    income_m = df[df["amount"] < 0].groupby("month")["amount"].sum().abs().reset_index()
    income_m["type"] = "Income"
    expense_m = df[df["amount"] > 0].groupby("month")["amount"].sum().reset_index()
    expense_m["type"] = "Expenses"
    combo = pd.concat([income_m, expense_m])
    if combo.empty:
        return f"No income/expense data for {label}.", None
    return f"Income vs expenses — **{label}** ({start} to {end}):", {"chart_type": "grouped_bar", "data": combo, "meta": {"x": "month", "y": "amount", "color": "type"}}


def _handle_recurring():
    if not LIB_OK:
        return "Library not loaded.", None
    try:
        rec = get_recurring_summary()
    except Exception:
        return "Could not load recurring summary. Try \"enrich data\" first.", None
    if rec.empty:
        return "No recurring charges detected.", None
    expenses = rec[rec["type"] == "Expense"].copy()
    income = rec[rec["type"] == "Income"].copy()
    parts = []
    if not expenses.empty:
        parts.append(f"**Recurring Expenses** ({len(expenses)} items, ~${expenses['typical_amount'].sum():,.0f}/mo)")
    if not income.empty:
        parts.append(f"**Recurring Income** ({len(income)} items, ~${income['typical_amount'].sum():,.0f}/mo)")
    title = " | ".join(parts) if parts else "Recurring payments:"
    return title, {"chart_type": "recurring_split", "data": rec, "meta": {}}


def _handle_savings():
    try:
        inv = db_sql("SELECT name, balances_current FROM v_investments_balance")
    except Exception:
        return "Could not load savings data.", None
    inv = inv.dropna(subset=["balances_current"]) if not inv.empty else inv
    inv = inv[inv["balances_current"] != 0] if not inv.empty else inv
    if inv.empty:
        return "No investment accounts found.", None
    return "Savings & investments:", {"chart_type": "donut", "data": inv, "meta": {"names": "name", "values": "balances_current"}}


def _handle_anomalies():
    df = _safe_transactions()
    if df.empty or "is_unusual" not in df.columns or not df["is_unusual"].any():
        return "No unusual transactions flagged.", None
    unusual = df[df["is_unusual"] == True][["date", "merchant_name", "amount", "unusual_reason"]].head(50)
    return "Unusual transactions:", {"chart_type": "scatter", "data": unusual, "meta": {"x": "date", "y": "amount", "color": "unusual_reason"}}


def _handle_budget_drilldown(user_msg=""):
    """Budget drill-down: history by month, top transactions, top merchants, category split."""
    if not LIB_OK:
        return "Library not loaded.", None
    from jupyter_finance.agents import _run_read_only_query
    start, end, label = parse_date_range(user_msg)
    batch_df = _run_read_only_query("budget_batch_history")
    if batch_df.empty:
        return "No budget history found.", None

    txn_df = _run_read_only_query("budget_transactions", {
        "start_date": start.isoformat(), "end_date": end.isoformat()
    })

    charts = []

    batch_df["start_date"] = pd.to_datetime(batch_df["start_date"], errors="coerce")
    batch_df["month"] = batch_df["start_date"].dt.to_period("M").astype(str)
    monthly = batch_df.groupby(["name", "month"]).agg(
        spent=("current_balance", "sum"), limit=("balance_limit", "max")
    ).reset_index()
    charts.append({
        "chart_type": "grouped_bar",
        "data": monthly.melt(id_vars=["name", "month"], value_vars=["spent", "limit"], var_name="metric", value_name="amount"),
        "meta": {"x": "month", "y": "amount", "color": "metric"}
    })

    if not txn_df.empty:
        by_merchant = txn_df.groupby("merchant_name")["amount"].sum().reset_index().sort_values("amount", ascending=False).head(10)
        by_merchant.columns = ["merchant", "amount"]
        charts.append({"chart_type": "horizontal_bar", "data": by_merchant, "meta": {"x": "amount", "y": "merchant"}})

        if "category" in txn_df.columns:
            by_cat = txn_df.groupby("category")["amount"].sum().reset_index()
            by_cat.columns = ["category", "amount"]
            by_cat = by_cat[by_cat["amount"] > 0].sort_values("amount", ascending=False)
            charts.append({"chart_type": "donut", "data": by_cat, "meta": {"names": "category", "values": "amount"}})

    title = f"Budget drill-down — **{label}** ({start} to {end})"
    return title, {"chart_type": "multi", "charts": charts, "data": pd.DataFrame()}


def _handle_whatif(msg):
    if not LIB_OK:
        return "Library not loaded.", None
    outcome = whatif_compute(msg)
    narration = outcome["narration"]
    result = outcome.get("result")
    if not result:
        return narration, None

    charts = []

    # 5a: Before/After bar chart
    if result["all_categories"]:
        rows = []
        for cat, vals in result["all_categories"].items():
            rows.append({"category": cat, "Current": vals["original"], "Adjusted": vals["adjusted"]})
        ba_df = pd.DataFrame(rows)
        ba_melted = ba_df.melt(id_vars="category", value_vars=["Current", "Adjusted"],
                               var_name="scenario", value_name="amount")
        charts.append({"chart_type": "whatif_before_after", "data": ba_melted,
                        "meta": {"x": "category", "y": "amount", "color": "scenario"}})

    # 5b: Waterfall chart
    if result["per_rule"]:
        base = result["projected_total"] if result["is_mid_period"] else result["original_total"]
        measures = ["absolute"]
        labels = ["Current Total"]
        values = [base]
        for pr in result["per_rule"]:
            act_label = {"cut": f"{pr['category']} -{pr.get('pct', 0):.0f}%",
                         "zero_out": f"{pr['category']} eliminated",
                         "cap": f"{pr['category']} capped"}.get(pr["action"], pr["category"])
            measures.append("relative")
            labels.append(act_label)
            values.append(-pr["savings"])
        measures.append("total")
        labels.append("New Total")
        values.append(result["new_total"])
        charts.append({"chart_type": "whatif_waterfall",
                        "data": pd.DataFrame({"label": labels, "amount": values, "measure": measures}),
                        "meta": {}})

    # 5c: Burn gauges (mid-period only)
    if result["is_mid_period"] and result["per_rule"]:
        gauge_rows = []
        for pr in result["per_rule"]:
            spent = result.get("cat_actual", {}).get(pr["category"], 0)
            gauge_rows.append({"category": pr["category"], "spent_so_far": spent,
                               "adjusted_cap": pr["adjusted"], "original": pr["original"]})
        if gauge_rows:
            charts.append({"chart_type": "whatif_gauges",
                            "data": pd.DataFrame(gauge_rows), "meta": {}})

    # 5d: Projection line (mid-period only)
    if result["is_mid_period"] and not result["daily_spending"].empty and result["days_remaining"] > 0:
        charts.append({"chart_type": "whatif_projection",
                        "data": result["daily_spending"],
                        "meta": {"daily_rate": result["spent_so_far"] / max(result["days_elapsed"], 1),
                                 "adjusted_daily_rate": max(result["new_total"] - result["spent_so_far"], 0) / max(result["days_remaining"], 1),
                                 "start": result["start"], "end": result["end"],
                                 "days_remaining": result["days_remaining"],
                                 "spent_so_far": result["spent_so_far"],
                                 "new_total": result["new_total"],
                                 "projected_total": result["projected_total"]}})

    # 5e: Category treemap
    if result["all_categories"]:
        tree_rows = []
        for cat, vals in result["all_categories"].items():
            diff_pct = ((vals["adjusted"] - vals["original"]) / vals["original"] * 100) if vals["original"] > 0 else 0
            tree_rows.append({"category": cat, "amount": vals["original"],
                              "impact_pct": round(diff_pct, 1), "adjusted": vals["adjusted"]})
        charts.append({"chart_type": "whatif_treemap",
                        "data": pd.DataFrame(tree_rows), "meta": {}})

    return narration, {"chart_type": "multi", "charts": charts}


def handle_message(user_text: str):
    intent = _classify_intent(user_text)
    if intent == "enrich":
        try:
            run_enrichment()
            return "Enrichment complete. Ask about spending, recurring charges, or anomalies.", None
        except Exception as e:
            return f"Enrichment failed: {e}", None
    if intent == "create_budget":
        return create_budget_agent(user_text), None
    if intent == "whatif":
        return _handle_whatif(user_text)
    if intent == "budget_drilldown":
        return _handle_budget_drilldown(user_text)
    if intent == "category_drilldown":
        return _handle_category_drilldown(user_text)
    dispatch = {
        "categorization_pie": lambda: _handle_categorization_pie(user_text),
        "budget_overview": _handle_budget_overview,
        "spending_over_time": lambda: _handle_spending_over_time(user_text),
        "income_vs_expenses": lambda: _handle_income_vs_expenses(user_text),
        "recurring": _handle_recurring,
        "savings_tracking": _handle_savings,
        "anomalies": _handle_anomalies,
    }
    if intent in dispatch:
        return dispatch[intent]()
    return explore_agent(user_text), None


def render_payload(payload):
    if not payload:
        return
    ct = payload.get("chart_type", "table")
    if ct == "multi":
        for sub in payload.get("charts", []):
            render_payload(sub)
        return
    if "data" not in payload:
        return
    df = payload["data"]
    if not isinstance(df, pd.DataFrame) or df.empty:
        return
    meta = payload.get("meta", {})
    try:
        if ct in ("pie", "donut"):
            names = meta.get("names", df.columns[0])
            values = meta.get("values", df.columns[-1])
            fig = px.pie(df, names=names, values=values, hole=0.55, color_discrete_sequence=COLORS)
            fig = _styled_fig(fig)
            fig.update_traces(textinfo="label+percent", textposition="outside",
                              textfont=dict(color="#1a1a2e", size=11),
                              hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<extra></extra>")
            fig.update_layout(height=CHART_H, showlegend=True, legend=dict(orientation="h", y=-0.1, font=_LEGEND_FONT))
            st.plotly_chart(fig, use_container_width=True)

        elif ct == "budget_bar":
            for _, brow in df.head(8).iterrows():
                lim = float(brow.get("balance_limit") or 1)
                sp = float(brow.get("current_balance") or 0)
                ratio = min(sp / lim, 1.0) if lim else 0
                bar_color = "#ff3b30" if ratio >= 1 else ("#ff9500" if ratio >= 0.8 else "#34c759")
                st.markdown(f'<p class="budget-label">{brow["name"]}</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="budget-sub">${sp:,.2f} of ${lim:,.2f}</p>', unsafe_allow_html=True)
                st.markdown(
                    f'<div style="background:#e8e8ed;border-radius:6px;height:10px;overflow:hidden;margin-bottom:14px;">'
                    f'<div style="width:{ratio*100:.1f}%;height:100%;background:{bar_color};border-radius:6px;"></div>'
                    f'</div>', unsafe_allow_html=True)

        elif ct == "grouped_bar":
            x, y = meta.get("x", "month"), meta.get("y", "amount")
            color = meta.get("color", "type")
            fig = px.bar(df, x=x, y=y, color=color, barmode="group",
                         color_discrete_map={"Income": "#34c759", "Expenses": "#ff3b30"})
            fig = _styled_fig(fig)
            fig.update_layout(height=CHART_H, xaxis_title="", yaxis_title="", legend=dict(orientation="h", y=1.12, font=_LEGEND_FONT))
            st.plotly_chart(fig, use_container_width=True)

        elif ct == "bar":
            x, y = meta.get("x", df.columns[0]), meta.get("y", df.columns[-1])
            fig = px.bar(df, x=x, y=y, color_discrete_sequence=COLORS)
            fig = _styled_fig(fig)
            fig.update_layout(height=CHART_H, xaxis_title="", yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

        elif ct == "horizontal_bar":
            if meta.get("caption"):
                st.caption(meta["caption"])
            x_col = meta.get("x", "typical_amount")
            y_col = meta.get("y", "merchant_name")
            if x_col in df.columns and y_col in df.columns:
                fig = px.bar(df, y=y_col, x=x_col, orientation="h", color_discrete_sequence=COLORS)
                fig = _styled_fig(fig)
                fig.update_layout(height=min(280, max(CHART_H, len(df) * 28)), xaxis_title="", yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True, hide_index=True, height=200)

        elif ct == "line":
            x, y = meta.get("x", df.columns[0]), meta.get("y", df.columns[-1])
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df[x], y=df[y], mode="lines",
                                     line=dict(color="#007aff", width=2.5, shape="spline"),
                                     fill="tozeroy", fillcolor="rgba(0,122,255,0.08)"))
            fig = _styled_fig(fig)
            fig.update_layout(height=CHART_H, xaxis_title="", yaxis_title="", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        elif ct == "recurring_split":
            expenses = df[df["type"] == "Expense"].copy() if "type" in df.columns else df.copy()
            income = df[df["type"] == "Income"].copy() if "type" in df.columns else pd.DataFrame()
            if not expenses.empty:
                st.markdown('<p class="budget-label">Recurring Expenses</p>', unsafe_allow_html=True)
                fig = px.bar(expenses, y="merchant_name", x="typical_amount", orientation="h",
                             color_discrete_sequence=["#ff3b30"],
                             hover_data=["count"])
                fig = _styled_fig(fig)
                fig.update_layout(height=min(280, max(CHART_H, len(expenses) * 28)),
                                  xaxis_title="Monthly Amount ($)", yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
            if not income.empty:
                st.markdown('<p class="budget-label">Recurring Income</p>', unsafe_allow_html=True)
                fig = px.bar(income, y="merchant_name", x="typical_amount", orientation="h",
                             color_discrete_sequence=["#34c759"],
                             hover_data=["count"])
                fig = _styled_fig(fig)
                fig.update_layout(height=min(280, max(CHART_H, len(income) * 28)),
                                  xaxis_title="Monthly Amount ($)", yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)

        elif ct == "whatif_before_after":
            st.caption("Current vs Adjusted spending")
            fig = px.bar(df, x=meta.get("x", "category"), y=meta.get("y", "amount"),
                         color=meta.get("color", "scenario"), barmode="group",
                         color_discrete_map={"Current": "#007aff", "Adjusted": "#34c759"})
            fig = _styled_fig(fig)
            fig.update_layout(height=CHART_H + 30, xaxis_title="", yaxis_title="",
                              margin=dict(l=16, r=16, t=50, b=16),
                              legend=dict(orientation="h", y=1.15, font=_LEGEND_FONT),
                              legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)

        elif ct == "whatif_waterfall":
            st.caption("Savings waterfall")
            fig = go.Figure(go.Waterfall(
                orientation="v", measure=df["measure"].tolist(),
                x=df["label"].tolist(), y=df["amount"].tolist(),
                connector={"line": {"color": "#e0e0e0"}},
                increasing={"marker": {"color": "#34c759"}},
                decreasing={"marker": {"color": "#ff3b30"}},
                totals={"marker": {"color": "#007aff"}},
                textposition="outside",
                text=[f"${abs(v):,.0f}" for v in df["amount"]],
                textfont=dict(color="#1a1a2e", size=10),
            ))
            fig = _styled_fig(fig)
            fig.update_layout(height=CHART_H + 40, xaxis_title="", yaxis_title="", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        elif ct == "whatif_gauges":
            st.caption("Month-to-date burn")
            gauge_cols = st.columns(min(len(df), 4))
            for i, (_, row) in enumerate(df.iterrows()):
                with gauge_cols[i % len(gauge_cols)]:
                    spent = float(row["spent_so_far"])
                    cap = float(row["adjusted_cap"])
                    orig = float(row["original"])
                    ratio = spent / cap if cap > 0 else 0
                    bar_color = "#ff3b30" if ratio >= 1 else ("#ff9500" if ratio >= 0.8 else "#34c759")
                    st.markdown(
                        f'<p class="budget-label">{row["category"]}</p>'
                        f'<p class="budget-sub">${spent:,.0f} spent / ${cap:,.0f} cap (was ${orig:,.0f})</p>'
                        f'<div style="background:#e8e8ed;border-radius:6px;height:10px;overflow:hidden;margin-bottom:10px;">'
                        f'<div style="width:{min(ratio*100, 100):.1f}%;height:100%;background:{bar_color};border-radius:6px;"></div>'
                        f'</div>', unsafe_allow_html=True)

        elif ct == "whatif_projection":
            st.caption("30-day spending projection")
            actual_df = df.copy()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=actual_df["date"], y=actual_df["cumulative"],
                                     mode="lines", name="Actual",
                                     line=dict(color="#007aff", width=2.5)))
            dr = meta.get("daily_rate", 0)
            adr = meta.get("adjusted_daily_rate", 0)
            remaining = meta.get("days_remaining", 0)
            last_val = float(actual_df["cumulative"].iloc[-1]) if not actual_df.empty else 0
            last_date = actual_df["date"].iloc[-1] if not actual_df.empty else meta.get("start")
            if remaining > 0:
                proj_dates = [last_date + timedelta(days=i) for i in range(1, remaining + 1)]
                proj_current = [last_val + dr * i for i in range(1, remaining + 1)]
                proj_adjusted = [last_val + adr * i for i in range(1, remaining + 1)]
                fig.add_trace(go.Scatter(x=proj_dates, y=proj_current, mode="lines",
                                         name="Current pace", line=dict(color="#ff9500", width=2, dash="dot")))
                fig.add_trace(go.Scatter(x=proj_dates, y=proj_adjusted, mode="lines",
                                         name="With changes", line=dict(color="#34c759", width=2, dash="dash")))
            fig = _styled_fig(fig)
            fig.update_layout(height=CHART_H + 20, xaxis_title="", yaxis_title="Cumulative ($)",
                              legend=dict(orientation="h", y=1.1, font=_LEGEND_FONT))
            st.plotly_chart(fig, use_container_width=True)

        elif ct == "whatif_treemap":
            with st.expander("Category impact treemap", expanded=False):
                fig = px.treemap(df, path=["category"], values="amount",
                                 color="impact_pct",
                                 color_continuous_scale=["#34c759", "#fafafa", "#ff3b30"],
                                 color_continuous_midpoint=0,
                                 hover_data={"adjusted": ":$,.2f", "impact_pct": ":.1f%"})
                fig = _styled_fig(fig)
                fig.update_layout(height=CHART_H + 60, margin=dict(l=4, r=4, t=4, b=4))
                fig.update_traces(textinfo="label+value", textfont=dict(color="#1a1a2e", size=11))
                st.plotly_chart(fig, use_container_width=True)

        elif ct == "scatter":
            x, y = meta.get("x", "date"), meta.get("y", "amount")
            color = meta.get("color") if meta.get("color") and meta["color"] in df.columns else None
            fig = px.scatter(df, x=x, y=y, color=color, color_discrete_sequence=COLORS,
                             hover_data=df.columns.tolist())
            fig = _styled_fig(fig)
            fig.update_layout(height=CHART_H)
            st.plotly_chart(fig, use_container_width=True)

        else:
            if meta.get("caption"):
                st.caption(meta["caption"])
            st.dataframe(df, use_container_width=True, hide_index=True, height=200)

    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True, height=200)


# ---------------------------------------------------------------------------
# Left pane: compact dashboard (max 2 charts per row)
# ---------------------------------------------------------------------------
with LEFT_COL:
    if LIB_OK:
        st.markdown(
            f'<div class="card"><p class="metric-label">{"Total Balance" if has_balance_data else "Net Flow"}</p>'
            f'<p class="metric-value">${total_bal:,.2f}</p>'
            f'<p class="metric-sub {"positive" if pct_change <= 0 else "negative"}">{"▼" if pct_change <= 0 else "▲"} {abs(pct_change):.1f}% vs prior month</p></div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(len(card_data) or 4)
        for col, (label, value) in zip(cols, card_data or [("—", 0)] * 4):
            with col:
                sub = f'<p class="metric-sub {"positive" if value >= 0 else "negative"}">{"+" if value >= 0 else "-"}${abs(value):,.2f}</p>' if label == "Net Cash Flow" else ""
                st.markdown(f'<div class="card"><p class="metric-label">{label}</p><p class="metric-value" style="font-size:1.2rem;">${abs(value):,.2f}</p>{sub}</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<p class="section-title">Net Worth Trend</p>', unsafe_allow_html=True)
            hist = _safe_balance_history()
            if not hist.empty and "balances_datetime" in hist.columns:
                hist = hist.copy()
                hist["balances_datetime"] = pd.to_datetime(hist["balances_datetime"], errors="coerce")
                hist = hist[hist["balances_datetime"].dt.date >= (today - relativedelta(months=12))]
                if not hist.empty:
                    monthly_nw = hist.groupby(hist["balances_datetime"].dt.to_period("M"))["balances_current"].sum().reset_index()
                    monthly_nw["month"] = monthly_nw["balances_datetime"].astype(str)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=monthly_nw["month"], y=monthly_nw["balances_current"], mode="lines", line=dict(color="#007aff", width=2.5, shape="spline"), fill="tozeroy", fillcolor="rgba(0,122,255,0.08)", hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>"))
                    st.plotly_chart(_styled_fig(fig).update_layout(height=CHART_H, xaxis_title="", yaxis_title="", showlegend=False), use_container_width=True)
                else:
                    st.caption("No balance history.")
            else:
                st.caption("No balance history.")
        with c2:
            st.markdown(f'<p class="section-title">Spending — {active_label}</p>', unsafe_allow_html=True)
            if not this_month_txn.empty:
                spend_df = this_month_txn[this_month_txn["amount"] > 0].copy()
                cat_col = "user_friendly_category" if "user_friendly_category" in spend_df.columns else "personal_finance_category"
                if cat_col not in spend_df.columns:
                    spend_df[cat_col] = "Uncategorized"
                cat_agg = spend_df.groupby(cat_col)["amount"].sum().reset_index()
                cat_agg.columns = ["category", "amount"]
                cat_agg = cat_agg[cat_agg["amount"] > 0].sort_values("amount", ascending=False)
                if not cat_agg.empty:
                    fig = px.pie(cat_agg, names="category", values="amount", hole=0.55, color_discrete_sequence=COLORS)
                    fig = _styled_fig(fig)
                    fig.update_traces(textinfo="label+percent", textposition="outside",
                                      textfont=dict(color="#1a1a2e", size=11),
                                      hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<extra></extra>")
                    fig.update_layout(height=CHART_H, showlegend=True, legend=dict(orientation="h", y=-0.15, font=_LEGEND_FONT))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.caption("No spending this month.")
            else:
                st.caption("No transactions this month.")
        c3, c4 = st.columns(2)
        with c3:
            st.markdown('<p class="section-title">Income vs Expenses</p>', unsafe_allow_html=True)
            if not txn.empty and "date" in txn.columns:
                ie_df = txn.dropna(subset=["date"])
                ie_df = ie_df[ie_df["date"].dt.date >= (today - relativedelta(months=6))]
                if not ie_df.empty:
                    ie_df = ie_df.copy()
                    ie_df["month"] = ie_df["date"].dt.to_period("M").astype(str)
                    income_m = ie_df[ie_df["amount"] < 0].groupby("month")["amount"].sum().abs().reset_index()
                    income_m.columns = ["month", "amount"]
                    income_m["type"] = "Income"
                    expense_m = ie_df[ie_df["amount"] > 0].groupby("month")["amount"].sum().reset_index()
                    expense_m.columns = ["month", "amount"]
                    expense_m["type"] = "Expenses"
                    combo = pd.concat([income_m, expense_m])
                    fig = px.bar(combo, x="month", y="amount", color="type", barmode="group", color_discrete_map={"Income": "#34c759", "Expenses": "#ff3b30"})
                    st.plotly_chart(_styled_fig(fig).update_layout(height=CHART_H, xaxis_title="", yaxis_title="", legend=dict(orientation="h", y=1.05, font=_LEGEND_FONT)), use_container_width=True)
                else:
                    st.caption("No data.")
            else:
                st.caption("No transaction data.")
        with c4:
            st.markdown('<p class="section-title">Budget Progress</p>', unsafe_allow_html=True)
            if not budgets.empty:
                for _, brow in budgets.iterrows():
                    limit_val = float(brow.get("balance_limit") or 1)
                    spent_val = float(brow.get("current_balance") or 0)
                    ratio = min(spent_val / limit_val, 1.0) if limit_val else 0
                    bar_color = "#ff3b30" if ratio >= 1 else ("#ff9500" if ratio >= 0.8 else "#34c759")
                    st.markdown(f'<p class="budget-label">{brow["name"]}</p><p class="budget-sub">${spent_val:,.0f} / ${limit_val:,.0f}</p><div style="background:#e8e8ed;border-radius:6px;height:8px;overflow:hidden;margin-bottom:10px;"><div style="width:{ratio*100:.1f}%;height:100%;background:{bar_color};border-radius:6px;"></div></div>', unsafe_allow_html=True)
            else:
                st.caption("No active budgets.")
        st.markdown('<p class="section-title">AI Insights</p>', unsafe_allow_html=True)
        insights = []
        if not budgets.empty and "under_limit" in budgets.columns:
            for _, r in budgets[budgets["under_limit"] == False].iterrows():
                insights.append(f"⚠️ <b>{r['name']}</b> over limit.")
        if not txn.empty and "is_unusual" in txn.columns and txn["is_unusual"].any():
            for _, u in txn[txn["is_unusual"] == True].head(3).iterrows():
                insights.append(f"🔍 Unusual: <b>{u.get('merchant_name') or u.get('name') or 'Unknown'}</b> ${abs(float(u['amount'])):,.0f}")
        if net_cashflow > 0:
            insights.append(f"💰 Cash flow +${net_cashflow:,.0f}. Consider savings.")
        elif net_cashflow < 0:
            insights.append(f"📉 Cash flow -${abs(net_cashflow):,.0f}. Review spending.")
        if not insights:
            insights.append("✅ No alerts.")
        for ins in insights:
            st.markdown(f'<div class="insight-box">{ins}</div>', unsafe_allow_html=True)
    else:
        st.info("Connect to database to see dashboard.")

# ---------------------------------------------------------------------------
# Right pane: chat (readable contrast, compact tables)
# ---------------------------------------------------------------------------
with RIGHT_COL:
    st.markdown("**Chat with your finances**")
    st.caption("Ask about spending, budgets, recurring, anomalies, what-if, or \"enrich data\".")
    st.session_state.setdefault("chat_history", [])

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["text"])
            if msg.get("payload"):
                render_payload(msg["payload"])

    if prompt := st.chat_input("Ask about spending, budgets, recurring charges..."):
        st.session_state["chat_history"].append({"role": "user", "text": prompt, "payload": None})
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply_text, payload = handle_message(prompt)
            st.markdown(reply_text)
            if payload:
                render_payload(payload)
        st.session_state["chat_history"].append({"role": "assistant", "text": reply_text, "payload": payload})
        st.rerun()
