$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$DataDir = Join-Path $RepoRoot "examples/synthetic_data"
$ResultsDir = Join-Path $RepoRoot "results/benchmark"

Write-Host "Generating deterministic synthetic partitions..."
servo-current-detector make-synthetic --output $DataDir --seed 2026

Write-Host "Running the six-method cycle-level benchmark..."
servo-current-detector benchmark `
  --training (Join-Path $DataDir "training.csv") `
  --scale (Join-Path $DataDir "scale.csv") `
  --calibration (Join-Path $DataDir "calibration.csv") `
  --test (Join-Path $DataDir "test.csv") `
  --output-dir $ResultsDir `
  --alpha 0.05 `
  --consecutive 3 `
  --seed 2026

Write-Host "Benchmark complete. Results saved to: $ResultsDir"
Write-Warning "This workflow uses synthetic signals only; it is not evidence of industrial performance."
