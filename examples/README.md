# Examples

Run the deterministic synthetic comparison benchmark from the repository root:

```powershell
.\examples\run_synthetic_demo.ps1
```

Or use the `make-synthetic` and `benchmark` commands shown in the main README and
[`docs/benchmarking.md`](../docs/benchmarking.md).

Generated CSV datasets and benchmark outputs are written to `examples/synthetic_data/`
and `results/benchmark/`. Those generated files are git-ignored by default. The
included generator contains synthetic signals only; do not replace them with proprietary
production telemetry in a public commit.
