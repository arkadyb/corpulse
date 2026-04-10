# Service Repo Strategy

## Recommendation

Create the dedicated service repo now.

`corpulse` should remain library-first while the new repo owns the REST service that sits in front of it. That recommendation matches the documented product boundary in `.planning/PROJECT.md`: the library stays focused on corpus-health analysis, backend injection, and wrapper integrations, while a separate service repo exposes the APIs.

The first service slice should be sync-first by default. The current sync `Corpulse` surface already exposes the analysis methods a first service needs, including `get_ghosts()`, `get_duplicates()`, `get_obsolete()`, `get_stale_embeddings()`, `get_suspects()`, `corpus_health()`, and `to_dataframe()`. That means the service repo can start immediately without broadening `corpulse` preemptively.

Do not make the first slice async-first unless there is a hard requirement already known. The shipped async path is intentionally narrow: `AsyncCorpulse` covers ingestion and `get_ghosts()`, not the broader analysis surface. If the service is explicitly async-first, the one justified exception is to add only the minimum missing `AsyncCorpulse` analysis methods required by the first endpoints being built.

## Why The Current State Supports This

- `corpulse` already ships the core analysis engine and the sync methods a service would call directly.
- The library already supports local SQLite defaults plus explicit sync and async Postgres backends for service environments.
- Qdrant wrappers already auto-log retrieval activity, so a service-backed demo can rely on real ingestion and analysis flows.
- The missing work is service-oriented, not analytics-oriented: HTTP contracts, auth, deployment, operator controls, and browser-facing concerns do not belong in this repo.

This makes the repo split low-risk now: the service repo can start from shipped capabilities, and `corpulse` only needs follow-up work if real integration friction appears.

## Boundary Rules

### Required in corpulse now

- No new service-layer feature is required in `corpulse` for a sync-first service repo. The shipped sync analysis surface is enough to start.
- If the service is mandated to be async-first, add only the minimum `AsyncCorpulse` analysis surface needed by the first endpoints. Keep that work limited to concrete endpoint needs rather than broad parity.

### Defer until service repo proves the need

- Defer speculative structured payload helpers until the service repo proves the actual response shapes it needs.
- Defer broader async ergonomics until the service repo shows real friction beyond the narrow first endpoint set.
- Defer pagination-friendly helpers, bundled snapshots, or other API-shaped conveniences unless service implementation shows they are repeatedly needed.

### Keep out of corpulse entirely

- REST contracts, routing, and HTTP request validation stay in the service repo.
- Auth posture, deployment configuration, and service operations stay in the service repo.
- Demo controls, curated demo-data workflows, and browser or UI concerns stay in the service repo.
- No pre-emptive service-layer features should be added to `corpulse` just to make the future service feel cleaner on paper.
