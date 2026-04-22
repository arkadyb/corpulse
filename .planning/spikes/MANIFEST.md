# Spike Manifest

## Idea
Validate whether corpulse can replace dedicated per-database wrapper classes with a single generic `wrap()` mechanism that intercepts retrieval methods, normalizes client-native results into `Corpulse.log_retrieval()` records, and preserves sync/async behavior.

## Requirements
- Must preserve the current Qdrant wrapper public API.
- Must support both sync and async clients.
- Must keep lazy optional-dependency behavior.
- Must prove the generic path with tests, not just a design sketch.

## Spikes

| # | Name | Type | Validates | Verdict | Tags |
|---|------|------|-----------|---------|------|
| 001 | generic-wrap | standard | Given the current Qdrant integration shape, when interception is moved into a configurable `wrap()` engine, then the existing wrapper behavior remains intact and a non-Qdrant client can reuse the same engine | PARTIAL | wrappers, integrations, qdrant, async |
