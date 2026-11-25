# Data format

The toolkit consumes one row per sample. CSV is used in the tutorial for portability;
Parquet can be read with pandas when the optional Parquet engine is installed.

| Column | Type | Meaning |
|---|---|---|
| `cycle_id` | string | Unique movement/cycle identifier within a station |
| `station_id` | string | An anonymized station or operating context identifier |
| `progress` | float | Normalized movement progress in the inclusive range 0 to 1 |
| `current_j1_pct` … `current_j6_pct` | float | Six current channels expressed as percent of each channel's rated current |
| `label` | integer | Optional cycle label: 0 normal, 1 anomalous |
| `time_ms` | float | Optional elapsed time within a cycle, in milliseconds |

The fitting partitions (`training`, `scale`, and `calibration`) must contain normal
cycles only. The `test` partition may contain normal and labelled anomalous cycles.
Each partition should be created by a time- or day-based split before fitting; do not
randomly split adjacent samples from the same cycle across partitions.

The six channel names are a generic example schema. Rename or map the columns in a
preprocessing step for other numbers of channels or different measurement units.
