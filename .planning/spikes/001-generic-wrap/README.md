---
spike: 001
name: generic-wrap
type: standard
validates: "Given the current Qdrant integration shape, when interception is moved into a configurable wrap() engine, then the existing wrapper behavior remains intact and a non-Qdrant client can reuse the same engine"
verdict: PARTIAL
related: []
tags: [wrappers, integrations, qdrant, async]
---

# Spike 001: Generic Wrap

## What This Validates
Given the current Qdrant integration shape, when interception is moved into a configurable `wrap()` engine, then the existing wrapper behavior remains intact and a non-Qdrant client can reuse the same engine.

## Research
No external library research was required. This spike is about internal response-shape regularity and whether the current wrapper logic can be extracted without losing lazy import guards or sync/async semantics.

## How to Run
```bash
pytest tests/test_generic_wrapper.py tests/test_qdrant_wrapper.py tests/test_import.py
```

## What to Expect
The generic wrapper tests should prove a sync and async client can both be instrumented through the same wrapping engine. The existing Qdrant tests should continue to pass, showing the public wrapper API still behaves the same.

## Investigation Trail
- Started from the current state: only Qdrant had dedicated wrappers, and both wrappers duplicated the same interception pattern.
- Noted the real variable part is not method interception itself, but response normalization and sync/async execution mode.
- Extracted a generic wrapper engine around configurable method specs and reused it from the Qdrant wrappers.
- Added a non-Qdrant fake client test to confirm the engine is not Qdrant-specific.

## Results
Verdict: `PARTIAL`

Evidence:
- Added a generic `wrap()` engine plus reusable `WrapMethod` specs.
- Refactored both Qdrant wrappers to use the shared engine without changing their public constructor shape.
- Added sync and async non-Qdrant tests proving the engine is reusable beyond Qdrant.
- Verified with `pytest tests/test_generic_wrapper.py tests/test_qdrant_wrapper.py tests/test_import.py`:
  `31 passed, 2 skipped`.

Key finding:
- A general wrapping mechanism is feasible with the current library state.
- Fully supporting "all databases in one shot" is not realistic without at least a small per-database normalization recipe, because each client returns different response shapes (`result.points`, `list[ScoredPoint]`, `hits`, payload conventions, vector fields, sync vs async methods).

Practical conclusion:
- Replace dedicated wrapper classes with a shared engine plus thin adapter specs.
- Do not aim for a zero-config universal wrapper unless the library first defines a stricter cross-database retrieval result contract.
