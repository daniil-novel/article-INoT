"""Draw the vector figure for the two ways of calling the model."""

from pathlib import Path

import matplotlib

matplotlib.use("pdf")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.path import Path as DrawingPath


WIDTH, HEIGHT = 540, 315
INK = "#172433"
MUTED = "#425467"
NEUTRAL_FILL, NEUTRAL_EDGE = "#f5f7fa", "#708196"
BLUE_FILL, BLUE_EDGE = "#edf3fb", "#355881"
GREEN_FILL, GREEN_EDGE = "#ecf6f1", "#366550"


def draw(destination: Path) -> None:
    with plt.rc_context({"font.family": "DejaVu Sans", "pdf.fonttype": 42}):
        figure = plt.figure(figsize=(WIDTH / 72, HEIGHT / 72), facecolor="white")
        canvas = figure.add_axes([0, 0, 1, 1], xlim=(0, WIDTH), ylim=(HEIGHT, 0))
        canvas.set_axis_off()

        def box(x, y, width, height, fill, edge, radius=7):
            canvas.add_patch(
                FancyBboxPatch(
                    (x, y),
                    width,
                    height,
                    boxstyle=f"round,pad=0,rounding_size={radius}",
                    facecolor=fill,
                    edgecolor=edge,
                    linewidth=1.1,
                    zorder=2,
                )
            )

        def label(x, y, content, size, *, align="center", weight="normal", color=INK):
            canvas.text(
                x, y, content, fontsize=size, ha=align, va="center",
                fontweight=weight, color=color, zorder=5,
            )

        def arrow(start, end, color, *, route=None):
            geometry = {"posA": start, "posB": end} if route is None else {"path": route}
            canvas.add_patch(
                FancyArrowPatch(
                    **geometry, arrowstyle="-|>", mutation_scale=10.5,
                    shrinkA=0, shrinkB=0, linewidth=1.25, color=color,
                    capstyle="round", joinstyle="round", zorder=4,
                )
            )

        title_x = 14
        label(title_x, 16, "Последовательные вызовы (MultiCall-Role)", 15,
              align="left", weight="semibold", color=BLUE_EDGE)
        box(205, 35, 130, 29, NEUTRAL_FILL, NEUTRAL_EDGE)
        label(270, 49.5, "Контекст C", 13)

        stages = ["Планирование", "Написание кода", "Рецензирование"]
        call_centers = [91, 270, 449]
        for index, (x, stage) in enumerate(zip(call_centers, stages), start=1):
            box(x - 77, 98, 154, 52, BLUE_FILL, BLUE_EDGE)
            label(x, 112, f"Вызов {index}", 11.5, color=MUTED)
            label(x, 132.5, stage, 14)
            arrow((x, 79), (x, 97), NEUTRAL_EDGE)
        canvas.plot([91, 449], [79, 79], color=NEUTRAL_EDGE, lw=1.25, zorder=3)
        canvas.plot([270, 270], [64, 79], color=NEUTRAL_EDGE, lw=1.25, zorder=3)
        canvas.scatter([270], [79], s=9, color=NEUTRAL_EDGE, zorder=4)
        arrow((168, 124), (191, 124), BLUE_EDGE)
        arrow((347, 124), (370, 124), BLUE_EDGE)
        first_to_third = DrawingPath(
            [(91, 150), (91, 168), (91, 176), (100, 176),
             (440, 176), (449, 176), (449, 168), (449, 151)],
            [DrawingPath.MOVETO, DrawingPath.LINETO, DrawingPath.CURVE3,
             DrawingPath.CURVE3, DrawingPath.LINETO, DrawingPath.CURVE3,
             DrawingPath.CURVE3, DrawingPath.LINETO],
        )
        arrow(None, None, BLUE_EDGE, route=first_to_third)

        canvas.plot([14, 526], [195, 195], color="#c4cdd7", lw=0.75)
        label(title_x, 214, "Интроспективный вызов (SR)", 15,
              align="left", weight="semibold", color=GREEN_EDGE)
        box(14, 264, 101, 29, NEUTRAL_FILL, NEUTRAL_EDGE)
        label(64.5, 278.5, "Контекст C", 13)
        box(140, 232, 386, 72, GREEN_FILL, GREEN_EDGE)
        label(333, 245.5, "Вызов 1", 11.5, weight="semibold", color=GREEN_EDGE)
        stage_centers = [204, 333, 462]
        for x, stage in zip(stage_centers, stages):
            box(x - 54, 263, 108, 31, "white", GREEN_EDGE, radius=5)
            label(x, 278.5, stage, 11.5)
        arrow((115, 278.5), (139, 278.5), NEUTRAL_EDGE)
        arrow((258, 278.5), (278, 278.5), GREEN_EDGE)
        arrow((387, 278.5), (407, 278.5), GREEN_EDGE)

        figure.savefig(destination, metadata={"Title": "Схема вызовов LLM", "CreationDate": None})
        plt.close(figure)


if __name__ == "__main__":
    draw(Path(__file__).with_name("context-flow.pdf"))
