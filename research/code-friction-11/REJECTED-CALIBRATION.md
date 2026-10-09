# Superseded v1 calibration

The files in this v1 tree preserve the original issue #11 packet, freeze
record, evaluator arrays, aggregate, report, validator, and tests. They remain
available for audit and comparison, but are rejected calibration data and must
not be supplied to blind v2 evaluators.

The v1 calibration was superseded because S3 did not actually exhibit the
requested slash behavior, S7 before/after already implemented the requested
option, and deduplication discarded source attempt and parent metadata. The
corrected neutral packet is under `research/code-friction-11-v2/`.
