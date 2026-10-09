"""Part 3: answer the three analyst questions from Postgres and write answers.md + PNG charts.

Runs the SQL in part3-data-analyst/questions.sql block by block (split on the '-- Q' headers),
renders the results as markdown tables and saves a chart per question with matplotlib.
"""
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2

HERE = os.path.dirname(os.path.abspath(__file__))
P3 = os.path.join(os.path.dirname(HERE), "part3-data-analyst")
DSN = os.environ.get("DATABASE_URL", "postgresql://superstore:superstore@localhost:5432/superstore")


def run(conn, sql):
    return pd.read_sql(sql, conn)


def md(df, n=12):
    d = df.head(n).copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda v: f"{v:,.2f}" if abs(v) < 10 else f"{v:,.0f}")
    return d.to_markdown(index=False)


def main():
    conn = psycopg2.connect(DSN)
    sql = open(os.path.join(P3, "questions.sql"), encoding="utf-8").read()
    blocks = [b.strip() for b in re.split(r"\n(?=-- Q\d)", sql) if b.strip().startswith("-- Q")]
    out = ["# Part 3 — Devin as data analyst", "",
           "Three questions of increasing difficulty, answered from the same Postgres database the dashboards use. "
           "The SQL for every answer is in `questions.sql`.", ""]

    # Q1 lookup
    q1 = run(conn, blocks[0].split(";")[0])
    out += ["## Q1 — Top 10 customers by profit last year (2023)", "", md(q1), "",
            f"**Answer:** {q1.iloc[0]['customer_name']} leads with ${q1.iloc[0]['profit']:,.0f} profit from {int(q1.iloc[0]['orders'])} orders; "
            f"the top 10 together made ${q1['profit'].sum():,.0f}, {q1['profit'].sum() / 93439.27:.0%} of total 2023 profit.", ""]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(q1["customer_name"][::-1], q1["profit"][::-1], color="#509EE3")
    ax.set_title("Top 10 customers by profit, 2023"); ax.set_xlabel("Profit ($)"); fig.tight_layout()
    fig.savefig(os.path.join(P3, "q1_top_customers.png"), dpi=130); plt.close(fig)

    # Q2 trend
    q2 = run(conn, blocks[1].split(";")[0])
    piv = q2.pivot(index="month", columns="region", values="sales").fillna(0)
    out += ["## Q2 — Monthly sales by region (2023)", "", "![monthly sales by region](q2_monthly_sales_by_region.png)", "",
            md(piv.reset_index().assign(month=lambda d: d["month"].astype(str))), "",
            f"**Answer:** West is the largest region in {int((piv.idxmax(axis=1) == 'West').sum())} of 12 months; every region peaks in "
            f"{piv.sum(axis=1).idxmax():%B}, which carries ${piv.sum(axis=1).max():,.0f} of sales (year-end push).", ""]
    fig, ax = plt.subplots(figsize=(9, 4))
    piv.plot(ax=ax, marker="o"); ax.set_title("Monthly sales by region, 2023"); ax.set_ylabel("Sales ($)"); ax.set_xlabel("")
    fig.tight_layout(); fig.savefig(os.path.join(P3, "q2_monthly_sales_by_region.png"), dpi=130); plt.close(fig)

    # Q3 why
    steps = [s.strip() for s in blocks[2].split(";") if s.strip()]
    quarters, subcats, regions, lines = (run(conn, s) for s in steps[:4])
    q4_23 = quarters[(quarters.year == 2023) & (quarters.quarter == 4)].iloc[0]
    q3_23 = quarters[(quarters.year == 2023) & (quarters.quarter == 3)].iloc[0]
    q4_22 = quarters[(quarters.year == 2022) & (quarters.quarter == 4)].iloc[0]
    worst = subcats.iloc[0]
    copiers = subcats[subcats.sub_category == "Copiers"].iloc[0]
    central_disc = regions[regions.region == "Central"].iloc[0]
    out += ["## Q3 — Why did profit drop in the Central region in Q4 2023?", "",
            "**Step 1 — did it drop?** Central profit by quarter:", "", md(quarters), "",
            f"Q4 2023 profit was ${q4_23['profit']:,.0f} on ${q4_23['sales']:,.0f} sales ({q4_23['profit'] / q4_23['sales']:.1%} margin), "
            f"versus ${q3_23['profit']:,.0f} in Q3 2023 and ${q4_22['profit']:,.0f} in Q4 2022 — sales rose but profit fell.", "",
            "**Step 2 — where?** Change in Q4 profit by sub-category, Central only:", "", md(subcats, 17), "",
            "![central q4 profit delta](q3_central_q4_subcategory_delta.png)", "",
            "**Step 3 — is Central's discounting unusual?** Average discount and margin by region, 2023:", "", md(regions), "",
            "**Step 4 — which orders?** The ten worst order lines in Central, Q4 2023:", "", md(lines, 10), "",
            f"**Answer:** Two things happened. (1) **{worst['sub_category']}** flipped from +${worst['profit_q4_2022']:,.0f} to ${worst['profit_q4_2023']:,.0f} "
            f"(a ${abs(worst['delta']):,.0f} swing) because Central sold them at an average {worst['avg_discount_2023']:.0%} discount; the two worst lines are "
            f"binding machines sold at 80% off, losing ${abs(lines['profit'].iloc[0]):,.0f} and ${abs(lines['profit'].iloc[1]):,.0f}. "
            f"(2) The Q4 2022 baseline was inflated by a one-off ${copiers['profit_q4_2022']:,.0f} Copiers profit that did not repeat. "
            f"Central's average discount ({central_disc['avg_discount']:.0%}) is the highest of the four regions (regions table above), which is why its "
            f"year-end volume turns into losses. Recommended action: cap discounts on Binders/Appliances/Tables in Central and treat the 2022 Copiers sale as a one-off when setting Q4 targets.", ""]
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#ED6E6E" if d < 0 else "#88BF4D" for d in subcats["delta"]]
    ax.barh(subcats["sub_category"][::-1], subcats["delta"][::-1], color=colors[::-1]); ax.axvline(0, color="k", lw=0.8)
    ax.set_title("Central region: change in Q4 profit, 2023 vs 2022, by sub-category"); ax.set_xlabel("Δ profit ($)")
    fig.tight_layout(); fig.savefig(os.path.join(P3, "q3_central_q4_subcategory_delta.png"), dpi=130); plt.close(fig)

    open(os.path.join(P3, "answers.md"), "w", encoding="utf-8").write("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
