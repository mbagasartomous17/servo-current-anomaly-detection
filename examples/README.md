# Synthetic Examples

This directory contains a reproducible, process-agnostic synthetic-data walkthrough.
It does not contain industrial telemetry.

After installing the package with `python -m pip install -e ".[dev]"`, run the full
example on Windows PowerShell from the repository root:

```powershell
.\examples\run_synthetic_demo.ps1
```

The script writes generated CSV files to `examples/synthetic_data/`, the fitted model
to `artifacts/`, and evaluation metrics to `results/`. Those generated outputs are
excluded by `.gitignore` so they are not accidentally committed.

For manual or non-Windows execution, follow the commands in the main README.
