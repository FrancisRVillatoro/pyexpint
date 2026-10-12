#!/usr/bin/env python3
"""Regenerate the figures of the paper and supplement from archived data.

One typeface for all panels, no panel labels inside the figures (panels are
identified by position in the captions), reference slopes on convergence plots.
Usage: python make_figures.py DATA_DIR OUT_DIR  (DATA_DIR holds the archived
JSON/CSV records; fusion_ablation.json is produced by benchmarks/fusion_ablation.py).
"""
import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

DATA, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "STIXGeneral", "mathtext.fontset": "stix", "font.size": 9,
                     "axes.labelsize": 9, "legend.fontsize": 7.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
                     "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False})
W, H = 5.3, 2.55
MARK = ["o", "s", "^", "D", "v", "P", "X", "*", "<", ">", "h", "p", "d", "8", "H", "1", "2", "3", "4", "+", "x", "|", "_", ".", ",", "o", "s"]


def save(fig, name):
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT / f"{name}.pdf")
    plt.close(fig)


def slope_guide(ax, x0, y0, order, length=2.0, label=None):
    x = np.array([x0, x0 * length])
    y = y0 * (x / x0) ** order
    ax.plot(x, y, color="0.35", lw=0.8, ls="-")
    ax.annotate(label or f"slope {order}", (x[-1], y[-1]), xytext=(3, -2), textcoords="offset points",
                fontsize=7, color="0.35")


# ---------------------------------------------------------------- Fig. 2
cl = json.load(open(DATA / "classical_selected.json"))
fig, ax = plt.subplots(figsize=(W, H))
hs = np.array(cl["hs"])
for k, (m, e) in enumerate(cl["errors"].items()):
    ax.loglog(hs, e, marker=MARK[k], ms=4, lw=1, label=m)
slope_guide(ax, 0.06, 7e-10, 4, label="slope 4")
slope_guide(ax, 0.06, 2e-8, 5, label="slope 5")
ax.set_xlabel("time step $h$"); ax.set_ylabel("final absolute error"); ax.legend(ncol=2)
save(fig, "fig02a_classical_order")

st = json.load(open(DATA / "stiff_order.json"))
hs = np.array(st["hs"])
for key, name in (("local", "fig02b_stiff_local"), ("nonlocal", "fig02c_stiff_nonlocal")):
    fig, ax = plt.subplots(figsize=(W, H))
    for k, (m, e) in enumerate(st[key].items()):
        ax.loglog(hs, e, marker=MARK[k], ms=4, lw=1, label=m)
    slope_guide(ax, 0.004, 3e-11, 4, label="slope 4")
    slope_guide(ax, 0.004, 3e-6, 2, label="slope 2")
    ax.set_xlabel("time step $h$"); ax.set_ylabel(r"final error $\|u_h-u_*\|_\infty$"); ax.legend(ncol=3)
    ax.set_xticks([1 / 640, 1 / 160, 1 / 40]); ax.set_xticklabels(["1/640", "1/160", "1/40"])
    save(fig, name)

# ---------------------------------------------------------------- Fig. 3
fu = json.load(open(DATA / "fusion_ablation.json"))["rows"]
fig, ax = plt.subplots(figsize=(W, 3.0))
names = [r["method"] for r in fu]; y = np.arange(len(names))
series = [("arnoldi_matvecs_unfused", "full Arnoldi, unfused", "0.70"), ("arnoldi_matvecs_fused", "full Arnoldi, fused", "0.35"),
          ("kiops_matvecs_unfused", "KIOPS-type, unfused", "#9ecae1"), ("kiops_matvecs_fused", "KIOPS-type, fused", "#3182bd")]
bh = 0.2
for i, (key, lab, col) in enumerate(series):
    vals = [r[key] for r in fu]
    ax.barh(y + (i - 1.5) * bh, vals, height=bh, color=col, label=lab)
for j, r in enumerate(fu):
    for i, b in ((1, "arnoldi"), (3, "kiops")):
        red = 100 * (1 - r[f"{b}_matvecs_fused"] / r[f"{b}_matvecs_unfused"])
        ax.annotate(f"{red:.1f}%", (r[f"{b}_matvecs_fused"], y[j] + (i - 1.5) * bh), xytext=(3, -2.5),
                    textcoords="offset points", fontsize=6.5)
ax.set_yticks(y); ax.set_yticklabels(names); ax.invert_yaxis()
ax.set_xlabel("matrix-vector products"); ax.legend(loc="upper right")
save(fig, "fig03_fusion_ablation")

# ---------------------------------------------------------------- Fig. 4 and Fig. S2 c, d
rows = list(csv.DictReader(open(DATA / "method_wp_replay2341311_all.csv")))
for r in rows:
    for k in ("h", "error_inf", "matvecs", "nonlinear_evals"):
        r[k] = float(r[k])
    r["floor"] = r["error_inf"] <= 5e-12
methods_all = []
for r in rows:
    if r["method"] not in methods_all:
        methods_all.append(r["method"])
sel8 = ["ETD4RK", "Krogstad", "HochOst4", "ABNorsett4", "PEC625", "PEC726", "PECEC635", "PECEC736"]


def nondominated(rs, work):
    pts = sorted((r for r in rs if not r["floor"]), key=lambda r: (r[work], r["error_inf"]))
    front, best = [], np.inf
    for r in pts:
        if r["error_inf"] < best:
            front.append(r); best = r["error_inf"]
    return front


def wp_panel(methods, work, xlabel, name, big):
    fig, ax = plt.subplots(figsize=(4.0 if big else W, 3.3 if big else H))
    for k, m in enumerate(methods):
        rs = sorted((r for r in rows if r["method"] == m), key=lambda r: -r["h"])
        ax.loglog([r[work] for r in rs], [r["error_inf"] for r in rs], marker=MARK[k % len(MARK)], ms=3.5, lw=0.9, label=m)
        fl = [r for r in rs if r["floor"]]
        if fl:
            ax.loglog([r[work] for r in fl], [r["error_inf"] for r in fl], ls="none", marker="o", ms=8, mfc="none", mec="k", mew=0.6)
    fr = nondominated([r for r in rows if r["method"] in methods], work)
    ax.loglog([r[work] for r in fr], [r["error_inf"] for r in fr], "k:", lw=1.2, label="non-dominated set")
    ax.axhline(5e-12, color="0.5", lw=0.7, ls="--")
    ax.set_xlabel(xlabel); ax.set_ylabel(r"final error $\|u_h-u_*\|_\infty$")
    if not big:
        ax.legend(ncol=2, loc="lower left")
    save(fig, name)
    return ax.get_legend_handles_labels()


wp_panel(sel8, "matvecs", "matrix-vector products", "fig04a_method_matvecs", False)
wp_panel(sel8, "nonlinear_evals", "nonlinear evaluations", "fig04b_method_nonlinear", False)
handles, labels = wp_panel(methods_all, "matvecs", "matrix-vector products", "figS02c_replay_all_matvecs", True)
wp_panel(methods_all, "nonlinear_evals", "nonlinear evaluations", "figS02d_replay_all_nonlinear_evals", True)
# one legend for both 27-method panels, as a separate file placed beside them
fig = plt.figure(figsize=(1.45, 4.6))
fig.legend(handles, labels, loc="center", ncol=1, frameon=False, fontsize=7.5, handlelength=2.2, labelspacing=0.55)
fig.savefig(OUT / "figS02e_replay_legend.pdf")
plt.close(fig)

# ---------------------------------------------------------------- Fig. 5
pr = list(csv.DictReader(open(DATA / "canonical_paired_ratios.csv")))
cases = sorted({(int(r["n_side"]), float(r["rtol"])) for r in pr})
reps = sorted({r["replica"] for r in pr})
for backend, name in (("leja", "fig05a_picasso_leja"), ("hybrid", "fig05b_picasso_hybrid"), ("auto", "fig05c_picasso_auto")):
    fig, ax = plt.subplots(figsize=(W, H))
    for i, rep in enumerate(reps):
        xs, ys, lo, hi = [], [], [], []
        for c, (n, tol) in enumerate(cases):
            r = next(r for r in pr if r["backend"] == backend and r["replica"] == rep and int(r["n_side"]) == n and float(r["rtol"]) == tol)
            med = float(r["paired_ratio_median"]); q1, q3 = float(r["paired_ratio_q1"]), float(r["paired_ratio_q3"])
            xs.append(c + (i - 1) * 0.18); ys.append(med); lo.append(med - q1); hi.append(q3 - med)
        ax.errorbar(xs, ys, yerr=[lo, hi], fmt=MARK[i], ms=4, lw=0.8, capsize=2, label=f"replica {i + 1}")
    ax.axhline(1.0, color="0.4", lw=0.7, ls=":")
    ax.set_xticks(range(len(cases))); ax.set_xticklabels([f"${n}^2$\n$10^{{{int(np.log10(t))}}}$" for n, t in cases])
    ax.set_ylabel(r"$t_{\mathrm{backend}}/t_{\mathrm{KIOPS}}$"); ax.set_xlabel("grid and requested rtol"); ax.legend(loc="upper left")
    save(fig, name)

# ---------------------------------------------------------------- Fig. S3
at = json.load(open(DATA / "action_tolerance.json"))
for key, ylabel, name in (("error_inf", "achieved error", "figS03a_action_error_inf"), ("matvecs", "matrix-vector products", "figS03b_action_matvecs")):
    fig, ax = plt.subplots(figsize=(W, H))
    combos = sorted({(r["backend"], r["rtol"]) for r in at["rows"]}, key=lambda c: (c[0], -c[1]))
    for k, (b, tol) in enumerate(combos):
        rs = sorted((r for r in at["rows"] if r["backend"] == b and r["rtol"] == tol), key=lambda r: r["action_fraction"])
        ax.loglog([r["action_fraction"] for r in rs], [r[key] for r in rs], marker=MARK[k], ms=4, lw=1, label=f"{b}, rtol $10^{{{int(np.log10(tol))}}}$")
    ax.set_xlabel("action-tolerance fraction $f$"); ax.set_ylabel(ylabel); ax.legend(ncol=2)
    save(fig, name)
print("figures written to", OUT)

# ---------------------------------------------------------------- Fig. S1 (development crossovers)
cr = json.load(open(DATA / "crossover_phase5.json"))
cases = sorted({(r["n"], r["scaled_width"]) for r in cr["rows"]})
fig, ax = plt.subplots(figsize=(W, H))
for k, b in enumerate(("arnoldi", "leja")):
    ys = []
    for n, w in cases:
        tb = next(r["median_s"] for r in cr["rows"] if r["n"] == n and r["scaled_width"] == w and r["backend"] == b)
        tk = next(r["median_s"] for r in cr["rows"] if r["n"] == n and r["scaled_width"] == w and r["backend"] == "kiops")
        ys.append(tb / tk)
    ax.plot(range(len(cases)), ys, marker=MARK[k], ms=4, lw=0.9, label="full Arnoldi" if b == "arnoldi" else "real Leja")
ax.axhline(1.0, color="0.4", lw=0.7, ls=":")
ax.set_xticks(range(len(cases))); ax.set_xticklabels([f"$n={n}$\nwidth {w}" for n, w in cases])
ax.set_ylabel(r"$t_{\mathrm{backend}}/t_{\mathrm{KIOPS}}$"); ax.legend()
save(fig, "figS01a_crossover_1d")

hy = json.load(open(DATA / "hybrid_phase6.json"))["rows"]
cases = sorted({(r["n"], r["method"]) for r in hy})
fig, ax = plt.subplots(figsize=(W, H))
for k, b in enumerate(("leja", "hybrid")):
    ys = [next(r["seconds"] for r in hy if r["n"] == n and r["method"] == m and r["backend"] == b)
          / next(r["seconds"] for r in hy if r["n"] == n and r["method"] == m and r["backend"] == "kiops") for n, m in cases]
    ax.plot(range(len(cases)), ys, marker=MARK[k], ms=4, lw=0.9, label="real Leja" if b == "leja" else "SciPy/KIOPS hybrid")
ax.axhline(1.0, color="0.4", lw=0.7, ls=":")
ax.set_xticks(range(len(cases))); ax.set_xticklabels([f"$n={n}$\n{m}" for n, m in cases])
ax.set_ylabel(r"$t_{\mathrm{backend}}/t_{\mathrm{KIOPS}}$"); ax.legend()
save(fig, "figS01b_hybrid_development")

pre = json.load(open(DATA / "prerelease_2d_selected_fields.json"))["rows"]
cases = sorted({(r["n_side"], r["rtol"]) for r in pre})
fig, ax = plt.subplots(figsize=(W, H))
for k, b in enumerate(("leja", "hybrid")):
    ys = [next(r["median_s"] for r in pre if r["n_side"] == n and r["rtol"] == t and r["backend"] == b)
          / next(r["median_s"] for r in pre if r["n_side"] == n and r["rtol"] == t and r["backend"] == "kiops") for n, t in cases]
    ax.semilogy(range(len(cases)), ys, marker=MARK[k], ms=4, lw=0.9, label="real Leja" if b == "leja" else "SciPy/KIOPS hybrid")
ax.axhline(1.0, color="0.4", lw=0.7, ls=":")
ax.set_xticks(range(len(cases))); ax.set_xticklabels([f"${n}^2$\n$10^{{{int(np.log10(t))}}}$" for n, t in cases])
ax.set_ylabel(r"$t_{\mathrm{backend}}/t_{\mathrm{KIOPS}}$"); ax.set_xlabel("grid and requested rtol"); ax.legend(loc="upper left")
save(fig, "figS01c_prerelease_2d")
print("supplementary crossover panels written")


# ---------------------------------------------------------------- Fig. 6 (broadband Allen-Cahn)
bb = json.load(open(DATA / "broadband_allen_cahn.json"))["rows"]
series = (("etd34", "kiops", "ETD34, KIOPS-type"), ("etd34", "leja", "ETD34, real Leja"),
          ("step_doubling_krogstad", "kiops", "step doubling, Krogstad, KIOPS-type"))
for key, xlabel, name in (("matvecs", "matrix-vector products", "fig06a_broadband_matvecs"),
                          ("wall_median_s", "median wall time of five solves (s)", "fig06b_broadband_time")):
    fig, ax = plt.subplots(figsize=(W, H))
    for k, (ctrl, backend, label) in enumerate(series):
        rs = sorted((r for r in bb if r["controller"] == ctrl and r["backend"] == backend), key=lambda r: -r["rtol"])
        ax.loglog([r[key] for r in rs], [r["error_inf"] for r in rs], marker=MARK[k], ms=4, lw=1, label=label)
    ax.set_xlabel(xlabel); ax.set_ylabel(r"final error $\|u_h-u_{\mathrm{ref}}\|_\infty$"); ax.legend(loc="lower left")
    save(fig, name)
print("broadband panels written")
