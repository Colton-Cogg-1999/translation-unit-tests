"""Static README figures, rendered in a light and a dark variant (GitHub picks one with <picture>)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

# Two categorical slots, validated for CVD separation and contrast on each surface (light and dark steps).
THEMES = {
    "light": {"surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
              "grid": "#e1e0d9", "axis": "#c3c2b7", "s1": "#2a78d6", "s2": "#eb6834"},
    "dark": {"surface": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781",
             "grid": "#2c2c2a", "axis": "#383835", "s1": "#3987e5", "s2": "#d95926"},
}
DPI = 200


def _style(ax, t):
    ax.set_facecolor(t["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(t["axis"])
    ax.tick_params(colors=t["ink2"], labelsize=9, length=0)
    ax.xaxis.grid(True, color=t["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def _fig(t, w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(t["surface"])
    _style(ax, t)
    return fig, ax


def _title(fig, ax, t, title, subtitle):
    h = fig.get_figheight()
    fig.text(0.01, 1 - 0.1 / h, title, ha="left", va="top", fontsize=12, fontweight="bold", color=t["ink"])
    fig.text(0.01, 1 - 0.36 / h, subtitle, ha="left", va="top", fontsize=9, color=t["ink2"])


def _hbar(ax, y, w, h, color):
    if w > 0:
        ax.barh(y, w, height=h, color=color, linewidth=0, zorder=2)


def _legend(fig, t, handles, y):
    leg = fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.005, y), ncol=len(handles),
                     frameon=False, fontsize=9, handlelength=1.6, columnspacing=1.6)
    for txt in leg.get_texts():
        txt.set_color(t["ink2"])


def _save(fig, out: Path, name: str, theme: str):
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / f"{name}-{theme}.png", dpi=DPI, facecolor=fig.get_facecolor(),
                metadata={"Software": None})   # no version stamp → reproducible bytes across matplotlib patches
    plt.close(fig)


def mode_effect(effects: list[dict], groups: list[dict], out: Path):
    """Dot + 95% CI per capability: document-minus-segment pass rate, pooled over the three engines.

    effects: [{"label", "cross_segment", "delta_pp", "ci_low", "ci_high"}], top to bottom.
    groups:  the two pooled rows, same keys, drawn bold at the top of their section."""
    for theme, t in THEMES.items():
        rows = []
        for cross in (True, False):
            g = next(x for x in groups if x["cross_segment"] == cross)
            rows.append({**g, "bold": True})
            rows += [{**e, "bold": False} for e in effects if e["cross_segment"] == cross]
            rows.append(None)  # spacer
        rows = rows[:-1]
        h = 0.32 * len(rows) + 1.7
        fig, ax = _fig(t, 8.6, h)
        fig.subplots_adjust(left=0.33, right=0.97, top=1 - 1.1 / h, bottom=0.6 / h)
        ax.axvline(0, color=t["axis"], linewidth=1.2, zorder=1)
        labels = []
        for i, r in enumerate(rows):
            y = len(rows) - 1 - i
            if r is None:
                labels.append((y, ""))
                continue
            c = t["s1"] if r["cross_segment"] else t["s2"]
            ax.plot([r["ci_low"], r["ci_high"]], [y, y], color=c, linewidth=2, solid_capstyle="round", zorder=2)
            ax.plot(r["delta_pp"], y, "o", color=c, markersize=9 if r["bold"] else 7,
                    markeredgecolor=t["surface"], markeredgewidth=2, zorder=3)
            if r["bold"]:
                ax.text(r["ci_high"] + 1.5, y, f"{r['delta_pp']:+.0f} pp", va="center", fontsize=9,
                        color=t["ink"], fontweight="bold")
            labels.append((y, r["label"]))
        ax.set_yticks([y for y, _ in labels], [lab for _, lab in labels])
        for tick, (_, lab) in zip(ax.get_yticklabels(), labels):
            if lab.startswith("All "):
                tick.set_fontweight("bold")
                tick.set_color(t["ink"])
        ax.set_ylim(-0.7, len(rows) - 0.3)
        lo = min(r["ci_low"] for r in rows if r) - 5
        hi = max(r["ci_high"] for r in rows if r) + 12
        ax.set_xlim(lo, hi)
        ax.set_xlabel("Pass rate, whole-document minus segment-by-segment translation (percentage points)",
                      color=t["ink2"], fontsize=9)
        handles = [Line2D([], [], marker="o", color=t["s1"], linewidth=2, markersize=7, label="cross-segment"),
                   Line2D([], [], marker="o", color=t["s2"], linewidth=2, markersize=7, label="segment-local (control)")]
        _legend(fig, t, handles, 1 - 0.62 / h)
        _title(fig, ax, t, "Document context helps the cross-segment capabilities",
               "Dot = pooled over Llama 4 Scout, GPT-5.4 nano and mini; line = 95% case-clustered bootstrap CI")
        _save(fig, out, "mode_effect", theme)


def qe_detection(rows: list[dict], out: Path):
    """Share of adjudicated-real errors that segment QE identified (any severity), by error type.

    rows: [{"label", "k", "n", "needs_context"}], top to bottom."""
    for theme, t in THEMES.items():
        h = 0.46 * len(rows) + 1.7
        fig, ax = _fig(t, 9.6, h)
        fig.subplots_adjust(left=0.42, right=0.95, top=1 - 1.15 / h, bottom=0.55 / h)
        for i, r in enumerate(rows):
            y = len(rows) - 1 - i
            pct = 100 * r["k"] / r["n"]
            ax.barh(y, 100, height=0.56, color=t["grid"], linewidth=0, zorder=1)   # track: 0 reads as empty
            _hbar(ax, y, pct, 0.56, t["s1"] if r["needs_context"] else t["s2"])
            ax.text(pct + 1.5, y, f"{r['k']} / {r['n']}", va="center", fontsize=9, color=t["ink"])
        ax.set_yticks(range(len(rows) - 1, -1, -1), [r["label"] for r in rows], color=t["ink"])
        ax.set_xlim(0, 112)
        ax.xaxis.grid(False)
        ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
        ax.set_ylim(-0.6, len(rows) - 0.4)
        ax.set_xlabel("Real errors that some segment-QE comment identified (any severity)", color=t["ink2"],
                      fontsize=9)
        _legend(fig, t, [Rectangle((0, 0), 1, 1, color=t["s1"], label="evidence is in another segment"),
                         Rectangle((0, 0), 1, 1, color=t["s2"], label="visible within the segment")], 1 - 0.62 / h)
        _title(fig, ax, t, "Segment QE finds what is visible inside the segment",
               "Errors adjudicated as real, all engines and modes; error types from results/mtunit/error_types.csv")
        _save(fig, out, "qe_detection", theme)


def artifact_rate(rows: list[dict], out: Path):
    """Share of unit-test failures that were test artifacts (not real errors), by capability.

    rows: [{"label", "artifacts", "failures"}], top to bottom."""
    for theme, t in THEMES.items():
        h = 0.34 * len(rows) + 1.35
        fig, ax = _fig(t, 8.6, h)
        fig.subplots_adjust(left=0.30, right=0.95, top=1 - 0.8 / h, bottom=0.55 / h)
        for i, r in enumerate(rows):
            y = len(rows) - 1 - i
            pct = 100 * r["artifacts"] / r["failures"]
            _hbar(ax, y, pct, 0.56, t["s1"])
            ax.text(pct + 1.5, y, f"{r['artifacts']} / {r['failures']}", va="center", fontsize=9, color=t["ink"])
        ax.set_yticks(range(len(rows) - 1, -1, -1), [r["label"] for r in rows], color=t["ink"])
        ax.set_xlim(0, 60)
        ax.set_xticks([0, 10, 20, 30, 40, 50], ["0%", "10%", "20%", "30%", "40%", "50%"])
        ax.set_ylim(-0.6, len(rows) - 0.4)
        ax.set_xlabel("Failures the adjudicator judged to be test artifacts (assertion wrong or over-specific)",
                      color=t["ink2"], fontsize=9)
        _title(fig, ax, t, "Where generated tests were wrong",
               "Unit-test failures by capability, all engines and modes")
        _save(fig, out, "artifact_rate", theme)


def bench_recall(rows: list[dict], models: list[tuple[str, str]], out: Path):
    """Two panels (cross-segment | segment-local errors): recall per detector, one dot + 95% CI per model.

    rows: [{"label", "cross": {model: ci-dict}, "local": {model: ci-dict}}], top to bottom.
    models: [(key, display name)] in series order."""
    for theme, t in THEMES.items():
        h = 0.78 * len(rows) + 1.75
        fig, axes = plt.subplots(1, 2, figsize=(9.6, h), sharey=True)
        fig.patch.set_facecolor(t["surface"])
        fig.subplots_adjust(left=0.27, right=0.97, top=1 - 1.25 / h, bottom=0.62 / h, wspace=0.08)
        colors = [t["s1"], t["s2"]]
        for ax, fam, title in ((axes[0], "cross", "Error evidence in another segment"),
                               (axes[1], "local", "Error visible in its own segment")):
            _style(ax, t)
            for i, r in enumerate(rows):
                y = len(rows) - 1 - i
                for j, (m, _) in enumerate(models):
                    d = r[fam].get(m)
                    if not d or d.get("rate") is None:
                        continue
                    yy = y + (0.14 if j == 0 else -0.14)
                    ax.plot([100 * d["ci_low"], 100 * d["ci_high"]], [yy, yy], color=colors[j], linewidth=2,
                            solid_capstyle="round", zorder=2)
                    ax.plot(100 * d["rate"], yy, "o", color=colors[j], markersize=8, markeredgecolor=t["surface"],
                            markeredgewidth=1.5, zorder=3)
                    above = j == 0
                    ax.text(100 * d["rate"], yy + (0.17 if above else -0.17), f"{100 * d['rate']:.0f}%", ha="center",
                            va="bottom" if above else "top", fontsize=8.5, color=t["ink"])
            ax.set_xlim(0, 104)
            ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
            ax.set_ylim(-0.6, len(rows) - 0.25)
            ax.set_title(title, fontsize=10, color=t["ink"], loc="left")
        axes[0].set_yticks(range(len(rows) - 1, -1, -1), [r["label"] for r in rows], color=t["ink"])
        fig.text(0.62, 0.2 / h, "Planted errors found and correctly described (recall)", ha="center", fontsize=9,
                 color=t["ink2"])
        _legend(fig, t, [Line2D([], [], marker="o", color=c, linewidth=2, markersize=7, label=name)
                         for c, (_, name) in zip(colors, models)], 1 - 0.62 / h)
        _title(fig, axes[0], t, "QE with context notices cross-segment errors but rates them minor",
               "108 planted errors in 20 real patient leaflets, gpt-5.4-mini; line = 95% CI resampling documents")
        _save(fig, out, "bench_recall", theme)

