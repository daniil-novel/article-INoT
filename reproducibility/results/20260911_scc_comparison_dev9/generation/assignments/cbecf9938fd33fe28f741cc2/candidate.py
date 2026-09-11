import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def task_func(s1, s2):
    s1 = pd.Series(s1)
    s2 = pd.Series(s2)

    values1 = set(s1.dropna().tolist())
    values2 = set(s2.dropna().tolist())
    intersections = values1 & values2

    data = pd.DataFrame({
        "value": pd.concat([s1, s2], ignore_index=True),
        "series": (["s1"] * len(s1)) + (["s2"] * len(s2)),
    })

    fig, ax = plt.subplots()
    sns.swarmplot(data=data, x="series", y="value", ax=ax)

    for value in intersections:
        ax.axhline(value, color="red", linestyle="--")

    return ax, len(intersections)