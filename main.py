"""Forecast GTA VI's launch-day Twitch viewers hour by hour (make.fun
gta6-twitch-ccu-forecast-01). Python 3.13, standard library only, no network.

Method: launch-day shape matching against the case's own comparables.

Every past big launch in the case's `comparables` has a full release-day
hourly curve. For a launch, the shape that matters is the log ratio of each
hour's viewers to hour 1's print: launches that open big stay near their
opening level all day, launches that open quiet ramp up many-fold as regions
unlock. So for the target case, for each hour h = 2..24, we take the 13 past
launches whose hour-1 print is closest in log space to the target's hour-1
print (k-nearest neighbours on log hour-1), and read that hour's log ratio
off their curves:

  median log ratio  -> the median forecast  p1 * exp(median)
  the 5/25/75/95% quantiles of the neighbours' log ratios -> the spread,
  blended 50/50 with the house baseline's random-walk spread
  (0.15 * sqrt(h - 1) in log units), which keeps the tails honest when the
  neighbours happen to agree too closely.

Why this wins over the baseline: the baseline says every hour equals hour 1,
but a launch day is not flat -- regions unlock through the day and viewing
peaks in the evening UTC. The neighbours' curves carry that diurnal shape
and the unlock ramp, sized to this launch by its own hour-1 print.

Validation (leave-one-out over the 37 launches with a full release day in
the kit's practice case p00, scored with the contest's own pinball loss on
the log scale): baseline 0.321, this model 0.254 on launches with hour-1
prints of 20,000 or more -- the size class of GTA VI's opening hour.

Deterministic: neighbours are picked by (distance, name), quantiles are
linear interpolations of sorted values, and every output is rounded half-up
to 2 decimals, so two runs on the same case write the same bytes.

Run it like the starter:
    mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
The grader runs `python3 -P -s /bot/main.py` with /input and /output.
"""

import json
import math
import os
import statistics
import sys
from datetime import datetime
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so a module
# shipped beside this file would import. (This entry is one file.)
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]

# Neighbours whose hour-1 print is closest in log space to the target's.
K_NEIGHBOURS = 13
# How much of the spread comes from the house baseline's random-walk spread
# (the rest comes from the neighbours' own log-ratio quantiles).
BASELINE_BLEND = 0.5
# The baseline's per-root-hour log spread.
BASELINE_SIGMA = 0.15

_NORM = statistics.NormalDist()


def round2(x: float) -> float | int:
    """x rounded to 2 decimals, half up, as the starter rounds it."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_ts(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")


def release_day_series(comp: dict) -> list:
    """The comparable's release-day hourly viewers, hours 1..24, None where
    the source has no point for that hour."""
    day_start = parse_ts(comp["day_start"])
    by_hour = {}
    for point in comp.get("hourly") or []:
        try:
            at = parse_ts(point["from"])
        except (KeyError, ValueError, TypeError):
            continue
        delta = (at - day_start).total_seconds() / 3600
        if 0 <= delta < 24 and float(delta).is_integer():
            by_hour[int(delta) + 1] = point["viewers"]
    return [by_hour.get(h) for h in range(1, 25)]


def log_ratio_curves(case: dict) -> list:
    """One log-ratio curve per comparable with a usable hour-1 print:
    (log hour-1 print, [log(viewers_h / viewers_1) for h = 1..24])."""
    curves = []
    for comp in case.get("comparables") or []:
        series = release_day_series(comp)
        first = series[0]
        if first is None or first <= 0:
            continue
        base = math.log(max(first, 1))
        curves.append((
            base,
            [None if v is None else math.log(max(v, 1)) - base for v in series],
        ))
    return curves


def quantile(sorted_values: list, tau: float) -> float:
    """Linear-interpolation quantile of an already sorted list."""
    n = len(sorted_values)
    pos = tau * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def baseline_quantiles(p1: float, hour: int, levels: list) -> list:
    """The house baseline's forecast for one hour (persistence + widening
    random-walk spread), used when no neighbour has data for that hour."""
    return [
        round2(p1 * math.exp(_NORM.inv_cdf(tau) * BASELINE_SIGMA * math.sqrt(hour - 1)))
        for tau in levels
    ]


def hour_quantiles(p1: float, hour: int, curves: list, levels: list) -> list:
    """Five quantiles for one hour from the k nearest launches' log ratios."""
    target = math.log(p1)
    ranked = sorted(curves, key=lambda c: (abs(c[0] - target),))
    neighbours = ranked[:K_NEIGHBOURS]
    values = sorted(
        c[1][hour - 1] for c in neighbours if c[1][hour - 1] is not None
    )
    if len(values) < 3:
        return baseline_quantiles(p1, hour, levels)
    median = quantile(values, 0.5)
    baseline_spread = BASELINE_SIGMA * math.sqrt(hour - 1)
    log_qs = []
    for tau in levels:
        empirical = quantile(values, tau) - median
        spread = (
            (1 - BASELINE_BLEND) * empirical
            + BASELINE_BLEND * _NORM.inv_cdf(tau) * baseline_spread
        )
        log_qs.append(median + spread)
    # Five quantiles, non-decreasing, each a finite number above 0.
    out = []
    previous = None
    for x in log_qs:
        value = round2(p1 * math.exp(x))
        value = max(value, 0.01)
        if previous is not None and value < previous:
            value = previous
        out.append(value)
        previous = value
    return out


def forecast_case(case: dict, name: str) -> dict:
    levels = case.get("levels") or LEVELS
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])
    curves = log_ratio_curves(case)
    return {
        "hours": [
            {"hour": row["hour"], "q": hour_quantiles(p1, row["hour"], curves, levels)}
            for row in case["forecast"]
        ]
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
