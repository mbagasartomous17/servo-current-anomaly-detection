# Contributing

Contributions are welcome. Please open an issue before substantial changes so the
scientific scope and evaluation protocol can be discussed first.

## Development setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

## Contribution principles

- Do not submit proprietary telemetry, robot programs, controller exports, IP
  addresses, credentials, operator identifiers, CCTV, or other restricted data.
- Use synthetic or independently licensed datasets in examples and tests.
- Keep model training, residual-scale estimation, calibration, and test partitions
  separate. Do not tune thresholds on the test set.
- Report negative results and limitations; do not make unsupported performance claims.
- Add tests for new algorithms and document assumptions and expected input schemas.
