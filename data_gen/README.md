# data_gen

Scripts that generate the synthetic dataset for the Layer 1 schema: ~3 years
of vehicles, inspections, defects, repairs, weapons, range sessions, ammo
lots, exercises, movements, orders and weather readings.

Synthetic anomalies are injected on purpose and logged in
`synthetic_anomaly_log`, so later models can be scored with real
precision/recall instead of guesswork.
