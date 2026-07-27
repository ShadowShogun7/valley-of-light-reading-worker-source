# Paid V1 Precision Layer Boundary Contract

Status: active contract for the Western-only paid V1 result.

This contract covers the remaining advanced layers that should not be quietly
promoted into visible interpretation until both source evidence and runtime
calculation support exist.

## Boundary Rules

### House Overlays

- Birth time and birth place must both be reliable for both people before
  angles, houses, or house overlays can even be considered.
- Reliable precision is necessary but not sufficient: paid V1 still blocks
  house overlays until the Western case file includes a productized overlay
  calculation with source-backed runtime traces.
- Current paid V1 may show natal relationship house factors only when the
  existing precision gate allows houses.
- Weak precision must return `blocked_by_birth_time` or `blocked_by_location`.
- High precision without overlay calculation must return `not_available`, not
  an invented interpretation.

### Composite And Davison

- Composite, Davison, and relationship-chart stories must stay absent from
  paid V1 visible copy and final conclusions until the calculation layer is
  explicitly built.
- The runtime boundary must be source-traced to the relationship-chart reserve
  claims, but its status remains `not_calculated`.
- Optional engine probes are not product evidence.

### Saturn Body Depth

- The current Saturn source text is enough only for a broad nonfatal process
  boundary: pressure, limits, responsibility, maturity, delay, and not treating
  Saturn as fate.
- Deeper Saturn relationship body extraction remains blocked while the local
  source file contains front matter, layout markers, and missing chapter body
  text.
- If the source text improves, the smoke should fail and force real extraction
  before any new Saturn claims enter paid output.

## Runtime Proof

The boundary is enforced by:

```bash
.venv/bin/python scripts/smoke_western_precision_layer_boundaries.py
```

The full paid stack verifier also runs this smoke:

```bash
.venv/bin/python scripts/verify_paid_v1_reading_stack.py --include-web
```

## Allowed Future Promotion Path

An advanced layer may move from blocked to paid V1 only after all of these are
true:

1. A raw source passage supports the claim.
2. A method claim is added with source location and `must_not_claim` boundaries.
3. Structured atoms/rules/selectors/guardrails are added.
4. Runtime traces prove the layer is used.
5. Scenario tests prove variation and precision blocking.
6. Visible Traditional Chinese output stays everyday, bounded, and nonfatal.
7. Reports and the paid V1 verifier pass.
