"""
preview.py — generates repo preview image for AI SQL Query Assistant
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

BG=  "#0d1117"; SURFACE="#161b22"; BORDER="#21262d"
ACCENT="#00d4aa"; PURPLE="#7c6af7"; ORANGE="#f7a74a"
RED="#ff6b6b"; TEXT="#e6edf3"; MUTED="#7d8590"

fig = plt.figure(figsize=(14, 8), facecolor=BG)
gs  = gridspec.GridSpec(3, 4, figure=fig, hspace=0.55, wspace=0.4,
                        top=0.90, bottom=0.07, left=0.04, right=0.97)

fig.text(0.03, 0.96, "AI-Powered SQL Query Assistant",
         color=TEXT, fontsize=15, fontweight="bold", va="top", fontfamily="monospace")
fig.text(0.03, 0.92, "Natural Language → SQL → Results → AI Interpretation · Claude API · Streamlit · SQLite",
         color=MUTED, fontsize=8, va="top", fontfamily="monospace")

# ── Terminal/query box simulation ─────────────────────────────────────────────
ax_term = fig.add_subplot(gs[0, :])
ax_term.set_facecolor(SURFACE)
for sp in ax_term.spines.values(): sp.set_edgecolor(ACCENT)
ax_term.set_xticks([]); ax_term.set_yticks([])
ax_term.text(0.01, 0.72, "❯  ", transform=ax_term.transAxes,
             color=ACCENT, fontsize=11, fontfamily="monospace", va="center")
ax_term.text(0.04, 0.72, "Show me the top 10 customers by total revenue this year",
             transform=ax_term.transAxes,
             color=TEXT, fontsize=10, fontfamily="monospace", va="center")
ax_term.text(0.01, 0.30,
             "SELECT customer_name, segment, ROUND(SUM(revenue),2) AS total_revenue, COUNT(*) AS orders\n"
             "FROM v_order_revenue WHERE strftime('%Y', order_date) = strftime('%Y','now')\n"
             "GROUP BY customer_id ORDER BY total_revenue DESC LIMIT 10",
             transform=ax_term.transAxes,
             color=PURPLE, fontsize=8, fontfamily="monospace", va="center")

# ── KPI row ───────────────────────────────────────────────────────────────────
kpis = [("10", "Rows", ACCENT), ("4", "Columns", PURPLE),
        ("0.008s", "Query Time", ORANGE), ("bar_h", "Chart", MUTED)]
for i, (v, l, c) in enumerate(kpis):
    ax = fig.add_subplot(gs[1, i])
    ax.set_facecolor(SURFACE)
    for sp in ax.spines.values(): sp.set_edgecolor(BORDER)
    ax.set_xticks([]); ax.set_yticks([])
    ax.text(0.5, 0.60, v, transform=ax.transAxes, ha="center", va="center",
            color=c, fontsize=16, fontweight="bold", fontfamily="monospace")
    ax.text(0.5, 0.18, l, transform=ax.transAxes, ha="center", va="center",
            color=MUTED, fontsize=7, fontfamily="monospace")

# ── Horizontal bar — top customers ────────────────────────────────────────────
ax_bar = fig.add_subplot(gs[2, :2])
customers = ["Olivia Brown", "David Kim", "Emma Wilson", "James Taylor",
             "Maya Garcia", "Nick Smith", "Alice Jones", "Carol Davis",
             "Frank White", "Grace Miller"]
revenue   = [48200, 42800, 39600, 36100, 33400, 31200, 28700, 26500, 24300, 22100]
colors    = [ACCENT if i == 0 else PURPLE for i in range(10)]
ax_bar.barh(customers[::-1], revenue[::-1], color=colors[::-1], height=0.7, alpha=0.9)
ax_bar.set_facecolor(SURFACE)
ax_bar.tick_params(colors=MUTED, labelsize=7)
for sp in ax_bar.spines.values(): sp.set_edgecolor(BORDER)
ax_bar.set_title("Top 10 Customers by Revenue", color=TEXT, fontsize=9,
                 pad=6, fontfamily="monospace")
ax_bar.set_xlabel("Revenue ($)", color=MUTED, fontsize=7)

# ── AI Insight box ────────────────────────────────────────────────────────────
ax_ins = fig.add_subplot(gs[2, 2:])
ax_ins.set_facecolor(SURFACE)
for sp in ax_ins.spines.values(): sp.set_edgecolor(ACCENT)
ax_ins.set_xticks([]); ax_ins.set_yticks([])
insight = ("AI Insight:\n\n"
           "Top 10 customers generated $333K in\n"
           "revenue this year. Olivia Brown leads\n"
           "at $48.2K — 45% above the cohort avg.\n"
           "7 of 10 are Enterprise or Mid-Market.\n\n"
           "Follow-up: Which segment drives the\n"
           "highest avg order value?")
ax_ins.text(0.05, 0.92, insight, transform=ax_ins.transAxes,
            color=TEXT, fontsize=8, fontfamily="monospace",
            va="top", linespacing=1.6)

plt.savefig("preview.png", dpi=150, bbox_inches="tight", facecolor=BG, edgecolor="none")
plt.close()
print("Preview saved.")
