"""Keep the offline SWE launcher regression suite in the repository CI path."""

from reproducibility.swe_smoke import test_evaluate_predictions as _suite


class TestSweSmokeLauncher(_suite.LauncherTests):
    pass
