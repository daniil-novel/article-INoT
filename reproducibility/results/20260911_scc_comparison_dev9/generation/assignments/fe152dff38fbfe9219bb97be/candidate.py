import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def task_func(s1, s2):
    if not isinstance(s1, pd.Series) or not isinstance(s2, pd.Series):
        raise TypeError("s1 and s2 must be pandas Series.")

    values1 = s1.dropna()
    values2 = s2.dropna()

    intersection = pd.Index(values1.unique()).intersection(
        pd.Index(values2.unique()),
        sort=False,
    )

    plot_data = pd.DataFrame(
        {
            "value": pd.concat([values1, values2], ignore_index=True),
            "series": (
                ["s1"] * len(values1)
                + ["s2"] * len(values2)
            ),
        }
    )

    _, ax = plt.subplots()

    sns.swarmplot(
        data=plot_data,
        x="series",
        y="value",
        ax=ax,
    )

    for value in intersection:
        ax.axhline(
            y=value,
            color="red",
            linestyle="--",
            linewidth=1,
        )

    return ax, len(intersection)
