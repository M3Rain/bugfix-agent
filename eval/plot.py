from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

R = Path("eval/results")


def plot_headline():
    df = pd.read_csv(R / "headline.csv")
    fig, ax = plt.subplots(figsize=(8, 4))
    df_sorted = df.sort_values("attempts")
    ax.bar(df_sorted["bug"], df_sorted["attempts"],
           color=["#2ca02c" if p else "#d62728" for p in df_sorted["passed"]])
    ax.set_ylabel("Attempts used")
    ax.set_title(f"Headline — pass rate {df['passed'].mean():.0%}")
    plt.xticks(rotation=90, fontsize=7)
    plt.tight_layout()
    plt.savefig(R / "headline.png", dpi=150)


def plot_ablation():
    df = pd.read_csv(R / "ablation.csv")
    with_rate = df["with_passed"].mean()
    without_rate = df["without_passed"].mean()
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.bar(["ReAct only", "ReAct + Reflexion"], [without_rate, with_rate])
    ax.set_ylabel("Pass rate")
    ax.set_ylim(0, 1)
    for i, v in enumerate([without_rate, with_rate]):
        ax.text(i, v + 0.02, f"{v:.0%}", ha="center")
    ax.set_title("Ablation")
    plt.tight_layout()
    plt.savefig(R / "ablation.png", dpi=150)


def plot_accumulation():
    df = pd.read_csv(R / "accumulation.csv")
    df["cum_pass_rate"] = df["passed"].expanding().mean()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df["i"], df["cum_pass_rate"], label="Cumulative pass rate")
    ax.plot(df["i"], df["mem_size_before"] / df["mem_size_before"].max(),
            label="Memory size (normalised)", linestyle="--")
    ax.set_xlabel("Bug # (in run order)")
    ax.set_ylabel("Rate / normalised size")
    ax.legend()
    ax.set_title("Memory accumulation")
    plt.tight_layout()
    plt.savefig(R / "accumulation.png", dpi=150)


if __name__ == "__main__":
    # Only plot the modes whose CSV has actually been generated, so running
    # this after just `--mode headline` doesn't crash on the missing files.
    for csv_name, fn in [
        ("headline.csv", plot_headline),
        ("ablation.csv", plot_ablation),
        ("accumulation.csv", plot_accumulation),
    ]:
        if (R / csv_name).exists():
            fn()
            print(f"wrote plot for {csv_name}")
        else:
            print(f"skipped {csv_name} (not generated yet)")
    print("done — output in", R)