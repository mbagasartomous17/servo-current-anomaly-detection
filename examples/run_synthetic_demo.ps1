$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$DataDir = Join-Path $RepoRoot "examples/synthetic_data"
$ModelPath = Join-Path $RepoRoot "artifacts/demo_detector.joblib"
$MetricsPath = Join-Path $RepoRoot "results/synthetic_metrics.csv"

Write-Host "Generating deterministic synthetic partitions..."
servo-current-detector make-synthetic --output $DataDir --seed 2026

Write-Host "Fitting the exploratory GPR detector..."
servo-current-detector fit `
  --training (Join-Path $DataDir "training.csv") `
  --scale (Join-Path $DataDir "scale.csv") `
  --calibration (Join-Path $DataDir "calibration.csv") `
  --model-out $ModelPath `
  --alpha 0.05

Write-Host "Evaluating the labelled synthetic test partition..."
servo-current-detector evaluate `
  --model $ModelPath `
  --test (Join-Path $DataDir "test.csv") `
  --output $MetricsPath

Write-Host "Demo complete. Metrics saved to: $MetricsPath"
Write-Warning "These metrics use synthetic signals only; they are not evidence of industrial performance."
