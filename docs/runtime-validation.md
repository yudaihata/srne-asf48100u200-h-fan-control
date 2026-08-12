# Runtime validation

## Test context

Evidence metadata retained for this historical comparison:

| Field | Recorded value |
|---|---|
| Product family | ASF48100U200-H |
| Source firmware | `ASF48100SU200_V8.16.9.bin` |
| Candidate profile | `fan35C_max60C_off32C` (legacy alias `fan35C_off32C`) |
| Hardware revision | not recorded |
| Device identifier | not retained |
| Updater and updater version | not recorded |
| Observation duration | one 24-hour stock day and one 24-hour candidate day |
| Recovery procedure verification | not recorded |

The missing fields limit this result to a historical observation; they must not
be silently inferred for another device.

The aggressive `fan35C_max60C_off32C` candidate was installed on a test inverter and
reported to operate normally, with increased audible fan activity. A 24-hour
Home Assistant history export was then compared with a stock-firmware day.

The logs contained:

- heatsink temperatures A, B, and C;
- total active load;
- PV2 power;
- battery power;
- outdoor temperature.

Home Assistant records state changes rather than fixed samples. The analysis
reconstructed each sensor as a step function on a one-minute grid, preserving
explicit `unknown` and `unavailable` intervals as missing values.

## Observed result

| 24-hour mean | Stock | 35/32 °C | Difference |
|---|---:|---:|---:|
| Outdoor temperature | 30.12 °C | 30.29 °C | +0.17 °C |
| Load | 1,293 W | 1,270 W | −23 W |
| Heatsink A | 42.67 °C | 41.21 °C | **−1.46 °C** |
| Heatsink B | 48.93 °C | 45.85 °C | **−3.08 °C** |
| Heatsink C | 50.81 °C | 48.75 °C | **−2.06 °C** |

After subtracting outdoor temperature, the reductions were 1.63 °C for A,
3.25 °C for B, and 2.23 °C for C.

The strongest evidence was at night (`PV <= 10 W`). The candidate day was
0.56 °C warmer outdoors and averaged 116 W more load, yet B was 3.84 °C cooler
and C was 2.62 °C cooler. Outdoor-adjusted reductions were 4.40 °C and 3.17 °C.

Time at or above 50 °C also decreased:

| Sensor | Stock | 35/32 °C | Reduction |
|---|---:|---:|---:|
| B | 579 min | 352 min | 227 min |
| C | 695 min | 538 min | 157 min |

During PV production, mean improvement was smaller: approximately 1.5 °C for B
and 0.9 °C for C. Daily maximum and 95th-percentile temperatures were not
meaningfully reduced. The observed benefit is therefore strongest in the
nighttime and low-to-medium thermal-demand region that motivated the patch.

## Repeating the analysis

Install the optional dependency and run:

```bash
python3 -m pip install -r requirements-analysis.txt
python3 tools/analyze_history.py \
  --stock history-stock.csv \
  --candidate history-candidate.csv \
  --output comparison.json
```

The entity IDs expected by the tool are defined in `tools/analyze_history.py`
and can be adapted for another Home Assistant installation.

## Limitations

- This comparison contains one day per profile.
- Outdoor temperature is only a proxy for the inverter-room temperature.
- Fan command/duty and lock-signal state were not logged.
- Weather, PV production, battery power, and thermal history cannot be matched
  perfectly between different days.

For stronger validation, collect several alternating stock/candidate days and
add inverter-room temperature plus fan command or lock-signal logging.
