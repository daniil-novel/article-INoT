import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def task_func(s1, s2):
    if not isinstance(s1, pd.Series) or not isinstance(s2, pd.Series):
        raise TypeError("s1 and s2 must be pandas Series")

    values1 = s1.dropna().unique()
    values2 = s2.dropna().unique()
    intersection = set(values1).intersection(values2)

    data = pd.DataFrame({
        "value": pd.concat([s1, s2], ignore_index=True),
        "series": ["s1"] * len(s1) + ["s2"] * len(s2),
    }).dropna(subset=["value"])

    _, ax = plt.subplots()

    if not data.empty:
        sns.swarmplot(
            data=data,
            x="series",
            y="value",
            ax=ax,
        )

    for value in intersection:
        ax.axhline(value, color="red", linestyle="--")

    return ax, len(intersection)
