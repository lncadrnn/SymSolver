# Validation Rules Covered by Unit Tests

## Required fields

- Solver result includes: `equation`, `given`, `method`, `steps`, `final_answer`, `verification_steps`, `summary`
- Summary includes `runtime_ms`, `total_steps`, `verification_steps`, `validation_status`

## Type checks

- `runtime_ms` is numeric
- `total_steps` and `verification_steps` are integers
- `validation_status` is a string (`pass`/`fail`)

## Range checks

- `runtime_ms >= 0`
- `total_steps >= 0`
- `verification_steps >= 0`

## Invalid input tests (documented)

1. Missing equal sign: `2x + 3`
2. Multiple equal signs: `x = 1 = 2`
3. Invalid character: `2x + 3 = 7$`
4. Username too short in storage validation
5. Password too short in storage validation
