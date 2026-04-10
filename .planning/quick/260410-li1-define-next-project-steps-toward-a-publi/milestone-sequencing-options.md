## Option A

### First three milestones in order

1. Service shell for hosted demo over existing corpulse library
2. Public demo UI over curated service endpoints
3. Service hardening and operator controls for repeatable hosted usage

### User-visible progress unlocked

The first milestone makes corpulse visible outside Python by exposing a narrow REST surface over the shipped analytics engine, seeded with curated demo data. Prospects can hit endpoints or a simple hosted preview and see corpus health results without reading library code first.

The second milestone turns that API into a browser narrative. Users can inspect a health summary, drill into ghosts and suspects, and understand the cleanup story through a web UI designed around demo evaluation rather than library usage.

The third milestone improves durability and trust for the hosted experience through stronger deployment posture, refreshable demo datasets, and better service controls, making the demo safe to show repeatedly.

### Key dependencies and risks

This path depends on the v1.1 storage work being sufficient for a service-backed deployment and on the team choosing a narrow API shape quickly. It also depends on curated sample data because the hosted demo cannot rely on a user's live vector database at first contact.

The main risk is that a thin service shell can expose gaps in the current async surface or service ergonomics earlier than expected. If the API boundary is chosen too loosely, the UI milestone may inherit instability.

### Fit with current project state

This option fits the current state because it treats corpulse as backend capability inside the separate service repo already anticipated in project docs. It does not require new wrappers or a packaging change before visible user value appears. The tradeoff is that some backend hardening happens under real demo pressure rather than before it.

## Option B

### First three milestones in order

1. Backend/API hardening milestone for service-grade corpulse exposure
2. Hosted demo service with curated corpus flows
3. Public web UI for evaluation and storytelling

### User-visible progress unlocked

The first milestone mostly unlocks technical readiness rather than broad user-facing visibility. It would define the API contract, settle async/service patterns, and prove that corpulse can be exposed safely and consistently from a separate service repo.

The second milestone then turns that hardened backend into a real hosted demo path with seeded data and stable analysis endpoints. External users would begin to see a functioning service, even if the first presentation layer is still basic.

The third milestone adds the web UI that makes the hosted service legible and persuasive to evaluators. This is the point where corpulse clearly becomes a public demo experience instead of a backend integration exercise.

### Key dependencies and risks

This path depends on making correct service decisions up front: API resource shape, ingestion model for demo data, and the minimum async breadth required. It also requires discipline not to let backend work expand into generic platform engineering.

The main risk is slower visible momentum. A backend-first milestone can consume time while still leaving the project without a hosted public surface that demonstrates benefits to prospective users.

### Fit with current project state

This option fits well with the separate-service expectation and the newly shipped Postgres backends. It is more conservative than Option A and reduces rework risk, but it delays the first public-facing proof. For a project that just finished foundational v1.1 work, this may be a credible but not the fastest path to a convincing hosted demo.

## Option C

### First three milestones in order

1. Broader library and integration expansion beyond Qdrant
2. Service/API layer after multiple integrations are proven
3. Public web UI after the broader backend surface exists

### User-visible progress unlocked

The first milestone would expand the library's reach for integrators by adding more wrappers, broader async parity, or new framework surfaces. This could make corpulse more generally attractive to developers, but it would still keep the project in a library-first posture.

The second milestone would finally expose the expanded analytics capability through a service layer. Only at that point would non-Python evaluators start to see a hosted experience.

The third milestone would add the browser UI and public storytelling layer, completing the path to a hosted demo much later.

### Key dependencies and risks

This option depends on deciding which integrations matter next and on proving that each new library surface is worth the added scope. It also risks multiplying maintenance work before the project validates that a hosted public demo is the right growth path.

The main risk is strategic drift. More wrappers and broader library polish do not solve the immediate gap called out in project state: there is still no public-facing service or UI.

### Fit with current project state

This option fits the historical library-first direction, but it does not fit the current need to define the next steps toward a hosted public demo. It preserves technical optionality at the cost of delaying the first public proof of value.

## Recommended sequence

Recommend Option B: backend/API hardening first, then hosted demo service, then public web UI.

This is the fastest credible path to a hosted public demo because it uses the shipped v1.1 backend foundation, respects the separate-service-repo decision, and avoids building a UI on top of an underdefined service contract. It is slightly slower to first visual output than Option A, but it lowers the chance of rework while still keeping the milestone sequence tightly focused on the hosted-demo goal rather than on more library expansion.
