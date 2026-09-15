"""EDAVisualizer: shared plotting utilities for exploratory data analysis."""

import pandas as pd


class EDAVisualizer:
    def plot_missingness(self, df: pd.DataFrame):
        raise NotImplementedError
