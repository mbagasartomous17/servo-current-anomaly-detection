# Data format

The toolkit consumes one row per sample. CSV is used in the tutorial for portability;
Parquet can be read with pandas when an optional Parquet engine is installed.

| Column | Type | Meaning |
|---|---|---|
| `cycle_id` | string | Unique movement/cycle identifier within a station |
| `station_id` | string | An anonymized station or operating-context identifier |
| `progress` | float | Normalized movement progress in the inclusive range 0 to 1 |
| `current_j1_pct` … `current_j6_pct` | float | Six current channels as percent of each channel's rated current |
| `label` | integer | Cycle label: 0 normal, 1 anomalous; constant within each cycle |
| `time_ms` | float | Optional elapsed time within a cycle, in milliseconds; non-decreasing with progress |
| `event_onset_time_ms` | float or empty | Optional ground-truth onset time for anomalous cycles; one constant value per anomalous cycle, empty for normal cycles |

The fitting partitions (`training`, `scale`, and `calibration`) must contain normal
cycles only. The `test` partition must contain cycle-constant labels. Each partition
should be created by a time- or day-based split before fitting; do not randomly split
adjacent samples from the same cycle across partitions.

`event_onset_time_ms` is required only when event-level detection delay is to be
reported. It must be supplied from an independently defined ground-truth event
annotation; the detector does not estimate or infer the onset. When a table is cropped
to a partial cycle, the event onset may be outside the retained time window.

The six channel names are a generic example schema. Rename or map the columns in a
preprocessing step for other numbers of channels or different measurement units.
