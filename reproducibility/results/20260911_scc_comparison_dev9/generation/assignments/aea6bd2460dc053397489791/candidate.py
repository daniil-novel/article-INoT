import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def task_func(s1, s2):
    s1 = pd.Series(s1)
    s2 = pd.Series(s2)

    plot_data = pd.DataFrame({
        "Series": ["s1"] * len(s1) + ["s2"] * len(s2),
        "Value": pd.concat([s1, s2], ignore_index=True),
    })

    ax = sns.swarmplot(
        data=plot_data,
        x="Series",
        y="Value",
        order=["s1", "s2"],
    )

    values_1 = pd.Index(s1.dropna().unique())
    values_2 = pd.Index(s2.dropna().unique())
    intersections = values_1.intersection(values_2)

    for value in intersections:
        ax.axhline(value, color="red", linestyle="--")

    return ax, len(intersections)