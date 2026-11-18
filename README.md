# gta6-twitch-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/simpson007/gta6-twitch-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/simpson007/gta6-twitch-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecasts how many people will be watching Grand Theft Auto VI live on Twitch in each hour of its release day, from the first hour's viewer count and the release-day curves of 38 past big launches.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## Method

`main.py` (Python 3.13, standard library only) reads the case's `comparables` — past big launches' hourly Twitch curves — and, for each hour 2–24, takes the 13 launches whose hour-1 print is closest in log space to this launch's hour-1 print. The median of their log ratios to hour 1 sets the median forecast; their 5/25/75/95% log-ratio quantiles set the spread, blended 50/50 with the house baseline's random-walk spread (0.15·√(h−1) in log units) so the tails stay honest.

Validation: leave-one-out over the 37 launches with a full release day in the kit's practice case, scored with the contest's own pinball loss on the log scale — 0.254 on launches with hour-1 prints of 20,000 or more, against 0.321 for the house baseline (−21%); 0.480 against 0.930 over all 37 launches. Runs in under a second per case, deterministic (two runs write the same bytes).

---

<sub>Entered on [make.fun](https://make.fun/?ref=ngqr1ydj&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
