# Security and responsible use

This repository is a research prototype. It is not a safety-rated device, robot
protective stop, collision-protection system, or production control system.

Never connect this package to a robot controller in a way that sends commands or
changes controller state. It is intended for offline analysis and read-only
monitoring experiments only. A qualified engineer must independently assess any
industrial deployment.

Do not publish secrets, credentials, private telemetry, industrial network details,
robot programs, or personal data. Report suspected vulnerabilities privately to the
repository maintainer rather than publishing exploit details.

Benchmark input and output files may contain sensitive operational patterns even after
names are removed. Keep real production data and derived sample-level predictions in
approved private storage. Do not commit real-data score traces, thresholds, cycle IDs,
or diagnostic plots to this public repository without explicit data-owner approval.
