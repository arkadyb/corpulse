# Phase 25: Shared Wrapper Engine - Research

**Researched:** 2026-04-22
**Domain:** generic retrieval-client wrapping, sync/async interception, normalized retrieval logging, optional dependency preservation
**Confidence:** HIGH

## Summary

Phase 25 should extract the reusable mechanics of integration wrappers into one shared engine rather than continuing to hand-write proxy classes per client. The spike already validated the crucial distinction: interception is generic, while result normalization remains integration-specific. That means the phase should ship a small public abstraction for configured method interception and keep backend-specific extraction logic explicit.

The lowest-risk implementation shape is:
- one generic wrapper module under `corpulse/integrations/`
- one method-spec type that captures normalization and query-text handling
- one sync wrapper path and one async wrapper path sharing the same public construction API
- tests that prove the engine works for a non-Qdrant client shape
- no behavior change to existing `Corpulse` retrieval logging semantics

## User Constraints

- Preserve the current Qdrant public API as a compatibility layer in the follow-on phase.
- Keep the distinction explicit between generic interception and backend-specific normalization.
- Support both sync and async clients without splitting the public extension surface into unrelated APIs.
- Preserve optional dependency boundaries; the generic layer must not eagerly import Qdrant-specific code.

## Key Findings

### The existing wrappers duplicate the same orchestration pattern
- The current integration shape is composition over a client plus transparent delegation via `__getattr__`.
- Both sync and async Qdrant wrappers do three reusable things: call the upstream method, normalize the native result into Corpulse records, and pass those records to `log_retrieval()`.
- That orchestration is portable across clients; only the native-result normalization differs.

### Sync and async differ mainly in logging execution, not in API shape
- The real async-specific concern is whether `corpulse.log_retrieval()` is sync or async and how to call it safely.
- A shared config model with two execution backends is sufficient; the abstraction does not need separate method-spec formats for sync vs async.

### Zero-config universal wrapping is still the wrong target
- Clients expose different method names, result containers, payload conventions, and vector shapes.
- The library should expose explicit normalization recipes, not attempt runtime inference of all possible client schemas.

## Recommended Implementation Shape

### Public abstraction
- Add a small public `WrapMethod` spec that defines how one upstream method is normalized into Corpulse retrieval records.
- Add a public `wrap(client, corpulse, *, methods, async_mode=None)` entry point that returns either a sync or async proxy.

### Internal engine behavior
- Intercept only configured methods; delegate all other attributes transparently.
- Remove the query-text kwarg before calling the upstream method, then call `log_retrieval()` with the normalized records.
- Raise a clear error if the sync wrapper encounters an awaitable `log_retrieval()` result; async mode should handle both sync and async logging implementations.

### Validation strategy
- Generic tests should use a non-Qdrant fake client to prove the engine is not tied to Qdrant’s result shape.
- Existing Qdrant tests should remain green once Phase 26 migrates the compatibility wrappers to the shared engine.

## Risks and Pitfalls

### Pitfall 1: leaking integration-specific assumptions into the generic layer
If the generic engine starts assuming `.points`, `payload`, or Qdrant-specific vector behavior, the abstraction collapses back into a Qdrant helper. Keep all response-shape knowledge in the normalizer functions.

### Pitfall 2: async drift between wrappers
If sync and async wrappers implement separate normalization or query-text logic, parity will drift. Keep configuration shared and isolate only the invocation strategy.

### Pitfall 3: breaking lazy optional dependency behavior
If the generic layer imports Qdrant or other optional clients at module import time, `import corpulse` will regress. The generic engine must stay dependency-agnostic.

## Validation Strategy

### Test layers
- `tests/test_generic_wrapper.py` for sync and async generic wrapper behavior
- `tests/test_import.py` as a regression check for lazy imports
- Qdrant integration tests continue to matter, but the Phase 25 focus is the shared engine itself

### Verification focus
- configured interception only
- sync/async logging safety
- transparent attribute delegation
- generic behavior with non-Qdrant client result shapes
- no optional-dependency coupling

## Sources

### Primary
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/PROJECT.md`
- `.planning/spikes/001-generic-wrap/README.md`
- `corpulse/integrations/qdrant.py`
- `corpulse/__init__.py`
- `tests/test_qdrant_wrapper.py`
- `tests/test_import.py`

## Metadata

- Research date: 2026-04-22
- Valid until: wrapper architecture changes materially or a second first-party wrapper introduces new abstraction pressure
