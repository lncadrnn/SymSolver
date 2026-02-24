# Required Outputs — Validation & Testing

---

## ☑ Validation Rules List (Required Fields, Type Checks, Range Checks)

### Required fields (top-level trail keys)

| Field                | Type       | Required |
| -------------------- | ---------- | -------- |
| `equation`           | string     | ✓        |
| `given`              | dict       | ✓        |
| `method`             | dict       | ✓        |
| `steps`              | list[dict] | ✓        |
| `final_answer`       | string     | ✓        |
| `verification_steps` | list[dict] | ✓        |
| `summary`            | dict       | ✓        |

### Required fields (summary)

| Field                | Type    | Required |
| -------------------- | ------- | -------- |
| `runtime_ms`         | float   | ✓        |
| `total_steps`        | integer | ✓        |
| `verification_steps` | integer | ✓        |
| `validation_status`  | string  | ✓        |
| `timestamp`          | string  | ✓        |
| `library`            | string  | ✓        |

### Full trail type map

| Path                         | Type                                 |
| ---------------------------- | ------------------------------------ |
| `equation`                   | string                               |
| `given.problem`              | string                               |
| `given.inputs.*`             | string (all values)                  |
| `method.name`                | string                               |
| `method.description`         | string                               |
| `method.parameters.*`        | string (all values)                  |
| `steps[].step_number`        | integer                              |
| `steps[].description`        | string                               |
| `steps[].expression`         | string                               |
| `steps[].explanation`        | string                               |
| `final_answer`               | string                               |
| `nonlinear_education`        | boolean (only on non-linear results) |
| `verification_steps[].*`     | same shape as `steps[]`              |
| `summary.runtime_ms`         | float                                |
| `summary.total_steps`        | integer                              |
| `summary.verification_steps` | integer                              |
| `summary.validation_status`  | string (`"pass"` / `"fail"`)         |
| `summary.timestamp`          | string                               |
| `summary.library`            | string                               |

### Type checks (tested)

- `runtime_ms` is numeric (float)
- `total_steps` and `verification_steps` are integers
- `validation_status` is a string (`"pass"` or `"fail"`)

### Range checks (tested)

- `runtime_ms >= 0`
- `total_steps >= 0`
- `verification_steps >= 0`

---

## ☑ At Least 3 Invalid Input Tests Documented

| #   | Invalid Input | Expected Error      | Test Function                             |
| --- | ------------- | ------------------- | ----------------------------------------- |
| 1   | `2x + 3`      | `must contain '='`  | `test_invalid_input_missing_equal_sign`   |
| 2   | `x = 1 = 2`   | `exactly one '='`   | `test_invalid_input_multiple_equal_signs` |
| 3   | `2x + 3 = 7$` | `Invalid character` | `test_invalid_input_bad_characters`       |

All five tests raise or return the expected error and are located in `tests/test_engine_unit.py` and `tests/test_storage_unit.py`.

---

## ☑ UI Shows Errors Without Crashing

- **Test:** `test_show_error_ui_path_does_not_crash` in `tests/test_app_and_main_unit.py`
- **What it does:** Calls `_show_error()` with a mocked Tk environment, verifying:
  - The loading indicator is destroyed
  - Input state is re-enabled (`True`)
  - The entry field regains focus
  - No exception is raised

---

## ☑ Trail Logs Validation Status (Pass/Fail)

- **Pass case:** `test_solve_linear_equation_required_fields_type_and_range_checks` and `test_system_solution_trail_logs_validation_pass` confirm `summary.validation_status == "pass"` for valid linear equations.
- **Fail case:** `test_nonlinear_trail_logs_validation_fail` confirms `summary.validation_status == "fail"` when a non-linear equation (e.g. `x^2 + 1 = 0`) is submitted.
- The `validation_status` field is set in `solver/engine.py` across all return paths (single-var, multi-var, system, and non-linear education).
