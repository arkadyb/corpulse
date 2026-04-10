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
