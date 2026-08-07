#!/usr/bin/env python3
"""Compare stock and candidate Home Assistant history CSV exports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ALIASES = {
    "sensor.gw2000c_outdoor_temperature": "outdoor",
    "sensor.srne_inverter_battery_power": "battery",
    "sensor.srne_inverter_heatsink_temperature_a": "temp_a",
    "sensor.srne_inverter_heatsink_temperature_b": "temp_b",
    "sensor.srne_inverter_heatsink_temperature_c": "temp_c",
    "sensor.srne_inverter_load_total_active_power": "load",
    "sensor.srne_inverter_pv2_power": "pv2",
}


def reconstruct(path: Path, timezone: str) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype={"entity_id": "string", "state": "string"})
    required = {"entity_id", "state", "last_changed"}
    if not required.issubset(raw.columns):
        raise ValueError(f"{path} must contain {sorted(required)}")
    raw["time"] = pd.to_datetime(raw["last_changed"], utc=True)
    grid = pd.date_range(
        raw.time.min().ceil("min"), raw.time.max().floor("min"), freq="1min", tz="UTC"
    )
    out = pd.DataFrame(index=grid)
    missing = sorted(set(ALIASES) - set(raw.entity_id.unique()))
    if missing:
        raise ValueError(f"{path} is missing entities: {', '.join(missing)}")
    for entity, alias in ALIASES.items():
        series = (
            raw.loc[raw.entity_id == entity, ["time", "state"]]
            .sort_values("time")
            .drop_duplicates("time", keep="last")
            .set_index("time")["state"]
        )
        # HA history is change-based. Expand string states first so explicit
        # unavailable/unknown periods remain invalid after numeric conversion.
        expanded = series.reindex(series.index.union(grid)).sort_index().ffill().reindex(grid)
        out[alias] = pd.to_numeric(expanded, errors="coerce")
    out.index = out.index.tz_convert(timezone)
    return out


def stats(data: pd.DataFrame) -> dict[str, object]:
    complete = data.dropna()
    regimes = {
        "all": complete,
        "night_pv_le_10w": complete[complete.pv2 <= 10],
        "solar_pv_gt_100w": complete[complete.pv2 > 100],
        "low_load_le_1000w": complete[complete.load <= 1000],
    }
    result: dict[str, object] = {
        "start": str(data.index.min()),
        "end": str(data.index.max()),
        "complete_minutes": int(len(complete)),
        "regimes": {},
    }
    for name, frame in regimes.items():
        values: dict[str, object] = {"minutes": int(len(frame))}
        for column in ["outdoor", "load", "pv2", "battery", "temp_a", "temp_b", "temp_c"]:
            series = frame[column]
            values[column] = {
                "mean": float(series.mean()),
                "p95": float(series.quantile(0.95)),
                "min": float(series.min()),
                "max": float(series.max()),
            }
        for sensor in ["a", "b", "c"]:
            delta = frame[f"temp_{sensor}"] - frame.outdoor
            values[f"temp_{sensor}_minus_outdoor_mean"] = float(delta.mean())
        values["minutes_at_or_above_50c"] = {
            sensor: int((frame[f"temp_{sensor}"] >= 50).sum()) for sensor in ["a", "b", "c"]
        }
        result["regimes"][name] = values
    return result


def compare(stock: dict[str, object], candidate: dict[str, object]) -> dict[str, object]:
    """Return candidate-minus-stock deltas for the main thermal metrics."""
    result: dict[str, object] = {}
    stock_regimes = stock["regimes"]
    candidate_regimes = candidate["regimes"]
    for name in stock_regimes.keys() & candidate_regimes.keys():
        before = stock_regimes[name]
        after = candidate_regimes[name]
        row: dict[str, object] = {}
        for column in ["outdoor", "load", "pv2", "battery", "temp_a", "temp_b", "temp_c"]:
            row[f"{column}_mean_delta"] = float(
                after[column]["mean"] - before[column]["mean"]
            )
        for sensor in ["a", "b", "c"]:
            key = f"temp_{sensor}_minus_outdoor_mean"
            row[f"{key}_delta"] = float(after[key] - before[key])
            row[f"temp_{sensor}_minutes_at_or_above_50c_delta"] = int(
                after["minutes_at_or_above_50c"][sensor]
                - before["minutes_at_or_above_50c"][sensor]
            )
        result[name] = row
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--timezone", default="Asia/Tokyo")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stock = stats(reconstruct(args.stock, args.timezone))
    candidate = stats(reconstruct(args.candidate, args.timezone))
    report = {"stock": stock, "candidate": candidate, "candidate_minus_stock": compare(stock, candidate)}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
