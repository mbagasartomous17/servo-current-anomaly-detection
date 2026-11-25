# Release notes — 0.2.1

Version 0.2.1 is a maintenance patch for the 0.2.0 research prototype.

## Changes

- Resolved six Ruff lint findings identified by the first Python 3.10–3.13 CI run.
- Removed two redundant integer casts in evaluation metrics.
- Applied the import ordering and type-annotation formatting required by Ruff.
- No changes were made to the detector mathematics, input schema, thresholds, or evaluation definitions.

## Validation

- The 17-test local pytest suite passes after these corrections.
- The complete Python 3.10–3.13 CI matrix must be rerun after publishing this patch.
