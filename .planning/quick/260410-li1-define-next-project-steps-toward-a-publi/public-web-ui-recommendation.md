## Recommendation

Adopt the sequence `Service-ready corpulse API foundation` -> `Hosted demo service with curated corpus flows` -> `Public web UI for corpus health storytelling`.

The immediate next milestone should be `Service-ready corpulse API foundation`. Its purpose is to turn the shipped library into a dependable backend capability for a separate service repo by defining a narrow REST contract, validating the minimum async/service path, and proving that curated demo data can drive stable analysis outputs.

The two follow-on milestones should then be `Hosted demo service with curated corpus flows` and `Public web UI for corpus health storytelling`. Together, these milestones move corpulse from a library consumed by developers to a hosted public demo that non-library evaluators can understand in a browser.

## Why this sequence fits corpulse now

This sequence uses the strongest part of the current project state: the analytics engine and the newly shipped storage backends are already good enough to serve as backend capability. What is missing is not more core analytics; it is a service boundary and a public-facing narrative.

Starting with API foundation respects the existing decision that a separate service repo should expose REST APIs. It also avoids prematurely building UI against unstable service assumptions.

Compared with a broader library expansion milestone, this sequence keeps the project focused on the hosted-demo goal that motivated the quick task. It preserves the GitHub-only v1.x library decision, keeps Qdrant as the first wrapper, and does not force a full async parity rewrite before a public demo exists.

## Proposed next three milestones

1. `Service-ready corpulse API foundation`
Minimum proof: a separate service repo can call corpulse through a narrow API contract, persist to the intended backend path, and return stable demo-oriented analysis payloads from curated corpus activity.

2. `Hosted demo service with curated corpus flows`
Minimum proof: a hosted environment can load or refresh a curated demo corpus, run the analysis pipeline end to end, and expose a reliable public demo service surface without manual local setup.

3. `Public web UI for corpus health storytelling`
Minimum proof: a browser user can land on the hosted demo, understand the corpus-health problem, inspect key findings, and see the cleanup narrative without needing direct library knowledge.

## Immediate next milestone scope

The next milestone should stay narrowly backend-facing. It should define the demo-facing API resources, the response shapes needed for a later UI, the curated dataset input path, and the minimum service integration pattern over the current corpulse library.

It should also settle the smallest async/service posture required for the separate service repo. The target is not full library parity; it is enough service confidence to support the hosted demo milestone without redesigning v1.1.

It should not include a production-polished UI, broad new vector DB wrappers, or a roadmap rewrite. Its job is to remove ambiguity at the service boundary and make the hosted demo milestone concrete.

## Decision gates before roadmap update

Confirm whether the service repo will standardize on the existing narrow async path or on a sync-first API layer for the first hosted demo. The roadmap should not be updated until that operating model is chosen.

Confirm the curated demo dataset strategy: fixed seeded dataset, replayable sample events, or another controlled demo-data flow. The hosted demo milestone depends on this being explicit.

Confirm the minimum public-demo API surface. At minimum, the project should decide which health summary, finding drill-down, and cleanup narrative endpoints are required before UI planning begins.

Confirm the hosting expectation for the first public demo: internal preview, public hosted preview, or a lightweight invite-only deployment. That decision affects how much service hardening belongs in milestone two versus milestone three.
