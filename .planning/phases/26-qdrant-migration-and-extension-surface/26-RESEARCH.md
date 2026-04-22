# Phase 26: Qdrant Migration And Extension Surface - Research

**Researched:** 2026-04-22
**Domain:** Qdrant compatibility migration, shared wrapper adoption, lazy optional dependency behavior, public extension documentation
**Confidence:** HIGH

## Summary

Phase 26 should sit directly on top of the Phase 25 engine and formalize the first real first-party migration onto that abstraction. The code already shows the intended shape: Qdrant-specific normalization stays in `corpulse.integrations.qdrant`, while interception and sync/async orchestration are delegated to the generic wrapper layer.

The safest Phase 26 outcome is:
- preserve `QdrantCorpulseClient` and `AsyncQdrantCorpulseClient` as public compatibility wrappers
- keep Qdrant-specific behavior limited to normalization helpers and lazy import guards
- verify the old Qdrant tests still pass after the migration
- make the README and exports explicit enough that maintainers can copy the pattern for the next integration

## User Constraints

- Existing Qdrant call sites must keep working without API changes.
- Qdrant-specific optional dependency behavior must remain lazy.
- The public docs must describe the generic extension path without implying zero-config support for every client.
- Phase 26 should finish the migration and documentation story, not redesign the wrapper engine again.

## Key Findings

### The migration pattern is already correct
- `corpulse.integrations.qdrant` now subclasses the shared sync/async wrapper base types.
- The Qdrant module still owns all response-shape semantics through `_normalize_points()` and `_qdrant_methods()`.
- Public helper functions such as `collection_name_for_user()`, `chunk_id()`, `delete_document_points()`, and `ensure_collection()` remain outside the generic wrapper layer, which is the correct architectural boundary.

### Compatibility must be verified at the Qdrant test level, not inferred from refactoring cleanliness
- The real acceptance surface is still `tests/test_qdrant_wrapper.py`.
- Qdrant compatibility includes passthrough behavior, payload-id handling, vector capture behavior, empty query handling, and async parity.
- If those tests pass, the migration can be treated as behavior-preserving.

### The extension surface is mostly a documentation problem now
- The package already exposes `wrap()` and `WrapMethod`.
- README language must be explicit that the generic engine removes wrapper boilerplate but still needs a normalization recipe per client.
- The public exports should make both the compatibility wrappers and the generic path discoverable.

## Recommended Implementation Shape

### Qdrant migration boundary
- Keep `QdrantCorpulseClient` and `AsyncQdrantCorpulseClient` as thin compatibility wrappers over the shared base classes.
- Keep lazy Qdrant import guards in the Qdrant module constructors.
- Keep normalization explicit in `_normalize_points()` and `_qdrant_methods()`.

### Verification strategy
- Run the Qdrant wrapper suite together with generic-wrapper and import tests for one coherent compatibility pass.
- Treat skipped `search()` tests from client-version differences as acceptable when the same skips existed before the migration.

### Documentation strategy
- Keep the README Qdrant quickstart as the first-class integration path.
- Document the generic wrapper API as the advanced extension path for future integrations.
- Make the limitation explicit: shared engine yes, universal automatic wrapping no.

## Risks and Pitfalls

### Pitfall 1: Phase 26 re-implements Phase 25 abstractions
If the Qdrant migration adds more generic behavior back into the Qdrant file, the boundary between engine and integration will erode. Keep the abstraction stable and focus this phase on adoption plus docs.

### Pitfall 2: lazy import regressions hidden by local environments
A developer with Qdrant installed can miss accidental eager imports. Keep import-safety tests in the verification path and rely on them rather than local intuition.

### Pitfall 3: docs overpromise universality
If the README implies that `wrap()` can instrument any client with no per-client work, future integrations will be planned on a false premise. State clearly that a normalizer recipe is still required.

## Validation Strategy

### Test layers
- `tests/test_qdrant_wrapper.py` for behavior-preserving migration coverage
- `tests/test_generic_wrapper.py` for the underlying shared engine assumptions
- `tests/test_import.py` for lazy optional-dependency guarantees

### Verification focus
- Qdrant public API compatibility
- lazy import behavior
- unchanged passthrough semantics
- discoverable but accurately-scoped extension docs

## Sources

### Primary
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/PROJECT.md`
- `.planning/phases/25-shared-wrapper-engine/25-01-SUMMARY.md`
- `corpulse/integrations/qdrant.py`
- `corpulse/integrations/wrapper.py`
- `corpulse/__init__.py`
- `README.md`
- `tests/test_qdrant_wrapper.py`
- `tests/test_generic_wrapper.py`
- `tests/test_import.py`

## Metadata

- Research date: 2026-04-22
- Valid until: a second first-party wrapper materially changes the public extension guidance
