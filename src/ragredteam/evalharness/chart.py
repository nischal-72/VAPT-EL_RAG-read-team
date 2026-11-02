"""Bar chart of attack success rate (ASR) by defense configuration."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

_ORDER = ["none", "input", "output", "both"]
_LABELS = {
    "none": "No defense",
    "input": "Input\nsanitizer",
    "output": "Output\nguard",
    "both": "Both",
}


def asr_bar_chart(asr_by_config: dict[str, float], out_path: str, model: str = "") -> None:
    configs = [c for c in _ORDER if c in asr_by_config]
    values = [asr_by_config[c] * 100 for c in configs]
    colors = ["#d6453d", "#e8a33d", "#e8a33d", "#15a34a"][: len(configs)]

    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    bars = ax.bar([_LABELS[c] for c in configs], values, color=colors, width=0.62)
    ax.set_ylabel("Attack success rate (%)")
    ax.set_ylim(0, 115)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    title = "ASR by defense configuration"
    if model:
        title += f"  ·  {model}"
    ax.set_title(title, fontsize=11, pad=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 2, f"{v:.0f}%",
                ha="center", va="bottom", fontsize=10, fontweight="bold")

    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
