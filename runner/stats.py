"""Binomial pass-rate statistics for eval aggregation."""
from math import sqrt


def wilson_ci(passes: int, n: int, z: float = 1.96):
    """Wilson score interval for a binomial pass rate (95% by default).

    Preferred over the normal approximation at small n and extreme rates,
    which is exactly the eval regime (n=20, rates near 0 or 1).
    """
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = passes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (p, max(0.0, center - half), min(1.0, center + half))


def verdict(passes: int, n: int, threshold: float):
    """A case PASSES if its point-estimate pass rate meets the threshold (the
    same convention as the Phase-1 seed grades). The Wilson 95% interval is
    reported alongside for transparency and is what the Session-19 ablation
    compares between the bundle-on and bundle-off arms."""
    rate, lo, hi = wilson_ci(passes, n)
    return {
        "passes": passes, "trials": n, "rate": round(rate, 3),
        "ci95": [round(lo, 3), round(hi, 3)], "threshold": threshold,
        "pass": rate >= threshold,
    }
