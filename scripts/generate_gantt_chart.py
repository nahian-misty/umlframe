"""Generates the UMLFrame project timeline Gantt chart (umlframe_gantt_chart.png).

Row labels are drawn as y-axis tick labels (outside the plotted date range)
rather than as text anchored inside the axes near each bar. Anchoring labels
inside the axes was what let a long label (M6) drift far enough right to
collide with the "Today" marker line; tick labels live in the margin and can
never overlap anything drawn on the timeline itself.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from matplotlib.patches import Patch

PHASE_COLORS = {
    "Research": "#9e9e9e",
    "Design": "#3b82f6",
    "Code": "#1a9e6d",
    "Testing": "#f2a900",
    "Deploy": "#8b5cf6",
}

@dataclass
class Segment:
    start: dt.date
    end: dt.date
    done: bool


@dataclass
class Task:
    label: str
    phase: str
    segments: list[Segment]


def _task(label: str, phase: str, start: dt.date, end: dt.date, done: bool) -> Task:
    return Task(label, phase, [Segment(start, end, done)])


TASKS = [
    _task("Literature review & paper study", "Research",
          dt.date(2026, 5, 1), dt.date(2026, 5, 15), True),
    _task("Requirement analysis", "Research",
          dt.date(2026, 5, 16), dt.date(2026, 5, 24), True),
    _task("System & architecture design\n(Unified UML JSON, pipeline shape)", "Design",
          dt.date(2026, 5, 25), dt.date(2026, 6, 10), True),
    _task("Frontend UML Editor\n(canvas, shapes, class box, relationships) — M1", "Code",
          dt.date(2026, 6, 1), dt.date(2026, 6, 20), True),
    # Image processing (M2) is marked "Done" in CLAUDE.md's status table, but
    # CV/OCR accuracy is still being refined in practice — shown here as an
    # initial completed pass followed by an ongoing/planned continuation
    # rather than a block that closes off in June.
    Task("Image Processing Pipeline\n(CV + OCR) — M2", "Code", [
        Segment(dt.date(2026, 6, 8), dt.date(2026, 6, 25), True),
        Segment(dt.date(2026, 6, 25), dt.date(2026, 8, 15), False),
    ]),
    _task("Unified UML JSON Schema\nimplementation — M3", "Code",
          dt.date(2026, 6, 12), dt.date(2026, 6, 28), True),
    _task("Code Generation engine\n(Python/Java/JS templates) — M4", "Code",
          dt.date(2026, 6, 20), dt.date(2026, 7, 8), True),
    _task("Auth & Projects\n(DB, JWT, CRUD, routing) — M8", "Code",
          dt.date(2026, 6, 28), dt.date(2026, 7, 20), True),
    _task("Forward-pipeline\nintegration testing", "Testing",
          dt.date(2026, 7, 15), dt.date(2026, 7, 31), True),
    _task("Reverse Engineering: AST parsers\n(Python/Java/JS) — M5", "Code",
          dt.date(2026, 8, 1), dt.date(2026, 8, 20), False),
    _task("Mermaid diagram generator\n(class + activity flowchart) — M6", "Code",
          dt.date(2026, 8, 10), dt.date(2026, 8, 28), False),
    _task("Full pipeline integration\n(reverse e2e, consistency check) — M7", "Testing",
          dt.date(2026, 8, 25), dt.date(2026, 9, 8), False),
    _task("System-wide testing\n& bug fixing", "Testing",
          dt.date(2026, 9, 5), dt.date(2026, 9, 18), False),
    _task("Frontend Mermaid preview panel\n& UI polish", "Code",
          dt.date(2026, 9, 12), dt.date(2026, 9, 25), False),
    _task("Deployment, docs\n& final demo", "Deploy",
          dt.date(2026, 9, 22), dt.date(2026, 9, 30), False),
]


def build_chart(output_path: str) -> None:
    fig, ax = plt.subplots(figsize=(18.2, 13.3), dpi=100)

    y_positions = list(range(len(TASKS), 0, -1))

    for y, task in zip(y_positions, TASKS):
        color = PHASE_COLORS[task.phase]

        for seg in task.segments:
            width = mdates.date2num(seg.end) - mdates.date2num(seg.start)
            start_num = mdates.date2num(seg.start)

            if seg.done:
                ax.barh(
                    y, width, left=start_num, height=0.6,
                    color=color, edgecolor="black", linewidth=1.2, zorder=3,
                )
                ax.text(
                    start_num + width / 2, y, "✓",
                    ha="center", va="center", color="white",
                    fontsize=13, fontweight="bold", zorder=4,
                )
            else:
                ax.barh(
                    y, width, left=start_num, height=0.6,
                    color=color, alpha=0.35, edgecolor="black", linewidth=1.2,
                    hatch="///", zorder=3,
                )

    # Row labels as y-tick labels: they live in the margin outside the axes'
    # data area, so they can never collide with anything drawn on the timeline
    # (bars, gridlines, the Today marker) regardless of label length.
    ax.set_yticks(y_positions)
    ax.set_yticklabels([t.label for t in TASKS], fontsize=11.5, ha="right")
    ax.tick_params(axis="y", length=0, pad=10)
    ax.set_ylim(0.3, len(TASKS) + 0.7)

    month_starts = [dt.date(2026, m, 1) for m in range(5, 10)]
    ax.set_xlim(mdates.date2num(dt.date(2026, 5, 1)), mdates.date2num(dt.date(2026, 10, 1)))
    for m_start in month_starts:
        ax.axvline(mdates.date2num(m_start), color="lightgray", linestyle=":", linewidth=1, zorder=1)

    # Use a fixed English month-name map rather than a locale-aware strftime
    # formatter: the host's LC_TIME can be set to a non-English locale (e.g.
    # bn_BD), which silently makes "%b" render month names in that locale's
    # script instead of English.
    english_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: english_months[mdates.num2date(x).month - 1])
    )
    ax.tick_params(axis="x", which="major", labeltop=True, labelbottom=False,
                    top=False, bottom=False, labelsize=15)
    for lbl in ax.get_xticklabels():
        lbl.set_fontweight("bold")

    ax.set_title("UMLFrame — Project Timeline (May – September 2026)",
                  fontsize=22, fontweight="bold", pad=40)

    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_visible(False)

    phase_handles = [Patch(facecolor=c, edgecolor="black", label=p) for p, c in PHASE_COLORS.items()]
    status_handles = [
        Patch(facecolor="black", edgecolor="black", label="Completed"),
        Patch(facecolor="white", edgecolor="black", hatch="///", label="Planned"),
    ]

    legend1 = ax.legend(
        handles=phase_handles, title="Phase", loc="upper left",
        bbox_to_anchor=(0.0, -0.03), ncol=5, frameon=False, fontsize=12, title_fontsize=13,
    )
    ax.add_artist(legend1)
    ax.legend(
        handles=status_handles, title="Status", loc="upper right",
        bbox_to_anchor=(1.0, -0.03), ncol=2, frameon=False, fontsize=12, title_fontsize=13,
    )

    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    build_chart("umlframe_gantt_chart.png")
