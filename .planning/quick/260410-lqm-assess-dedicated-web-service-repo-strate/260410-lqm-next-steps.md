# Next Steps

1. Start the dedicated service repo now and treat `corpulse` as the library-first analytics engine behind it.
2. Build the first service slice sync-first unless a hard async-first requirement is already known before implementation starts.
3. Define the first endpoints around shipped sync capabilities: corpus summary plus the highest-value drill-down analysis calls the service needs immediately.
4. Keep REST contracts, auth, deployment, demo controls, and any UI or browser work in the service repo rather than backfilling them into `corpulse`.
5. Use this trigger for any `corpulse` follow-up: return to library work only when service implementation reveals a missing analysis helper, missing structured analysis output, or missing async read method that blocks an endpoint already being built.

## Decision Gate

If the service is mandated to be async-first, the first `corpulse` follow-up is limited async analysis parity for the specific endpoints in scope. Add only the `AsyncCorpulse` methods those endpoints need; do not broaden the library with speculative async-first or service-facing features beyond that.
