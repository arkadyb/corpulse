## Current shipped assets

corpulse is a shipped Python library for corpus health analytics in RAG pipelines. The core value is already validated: teams can point the library at retrieval activity and quickly see ghost documents, near-duplicates, obsolete versions, stale embeddings, low-engagement suspects, and an overall corpus health score.

The current library surface already covers the analytics engine and the persistence layer needed for a service backend. It ships with manual ingestion APIs, human-readable reports, DataFrame export, and a working Qdrant wrapper that can capture query activity automatically.

The v1.1 milestone added the production-oriented storage base that a hosted service will need. `Corpulse` now supports explicit backend injection, while `AsyncCorpulse` and async Postgres support provide a narrow async path for service integration. SQLite remains the default local path, and Postgres is the production backend target.

The project documentation also already defines an important architectural boundary: the library is expected to sit behind a separate service repo that exposes REST APIs. That means corpulse itself does not need to become the web product; it needs to remain the analytics engine that a public-facing service can call.

## Constraints that remain in force

The project is still library-first today. The current roadmap and project state explicitly say there is no active milestone yet, and the next decision should choose the next milestone after v1.1 rather than retrofitting roadmap changes inside this quick task.

GitHub-only distribution remains the v1.x decision. Nothing in the current project docs supports a PyPI push or a packaging pivot as the immediate next move, so the recommendation should not depend on broader distribution changes to reach a hosted demo.

Qdrant remains the first wrapper target. The next milestone sequence can build on that proven integration path, but it should not assume Chroma, Pinecone, or framework plugins arrive first.

The existing async surface is intentionally narrow. The project state still needs a decision on whether async parity should expand, so the next milestone should avoid hinging the public demo on a full async library redesign unless the service path proves it is necessary.

The service boundary also remains in force: a separate service repo is expected to expose REST APIs. A hosted public demo therefore needs to treat corpulse as backend capability inside that service, not as a monolithic library-plus-UI package.

## Public demo service requirements

A hosted public demo needs a service layer that can expose a small, stable API over corpulse analysis results. The minimum useful capability is not raw library access; it is a demo-oriented flow that can ingest or load corpus activity, run the existing analytics, and return results that a browser can render.

The demo also needs curated demo data flow. A public web UI is only convincing if it can show before-and-after corpus health signals, meaningful suspect documents, and a readable cleanup narrative without relying on a user to instrument a live production vector database on day one.

A user-facing web UI narrative is required. The existing library can print reports, but a public demo needs a browser journey that explains the problem, shows the health findings, and makes the value legible to someone evaluating corpulse in a few minutes.

Operationally, the hosted path needs environment and deployment decisions that the library alone does not answer: API host shape, Postgres-backed runtime, demo dataset lifecycle, and how the service seeds or refreshes the example corpus.

## Gaps between current state and public demo

The main gap is service/API exposure. corpulse already computes the underlying analytics, but there is no shipped REST layer that turns those capabilities into browser-consumable endpoints for summaries, findings, or cleanup views.

The second gap is curated demo data flow. The project has manual ingestion and a Qdrant wrapper, but there is no defined public-demo path that loads a representative corpus, captures retrieval and engagement events, and guarantees the UI can show stable, intelligible results.

The third gap is the web UI itself. The project explicitly lists web dashboard/UI as out of scope for the library-first phase, so there is no browser interface, no demo storyline, and no user-facing explanation layer yet.

There is also a sequencing gap around service hardening. The v1.1 storage work makes a service feasible, but the project has not yet committed to which API shape, auth posture for a public demo, or async breadth is needed before a hosted service is credible.

Finally, there is a milestone-definition gap. The roadmap is intentionally blank after v1.1, so the immediate need is to choose a milestone order that uses the current library as backend capability and then layers in service and UI milestones in a controlled way.

## Non-goals for the next milestone

The next milestone should not expand into broad new vector DB integrations before a hosted-demo path exists. More wrappers may matter later, but they do not by themselves create a public-facing service or a browser narrative.

The next milestone should not attempt a full productization push across packaging, CLI, and generic dashboard work at once. That would sprawl past the quick task's goal and violate the current planning guardrails.

The next milestone should not rewrite the core analytics engine or the pluggable storage architecture shipped in v1.1. Those capabilities are the base that the future service will stand on.

The next milestone should also not revise the GitHub-only v1.x distribution decision unless a later milestone explicitly reopens that question. A hosted public demo can be achieved through a separate service repo without changing how the library itself is distributed.
