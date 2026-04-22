# Spike Conventions

Patterns and stack choices established across spike sessions. New spikes follow these unless the question requires otherwise.

## Stack
Use the repository's Python package and pytest suite for executable spikes.

## Structure
Spike artifacts live under `.planning/spikes/NNN-name/README.md`. When a spike validates a library change, keep the proof close to production code and cover it with tests.

## Patterns
Prefer extraction of reusable primitives over one-off experimental forks when the spike is testing library architecture.

## Tools & Libraries
Use pytest for verification. Preserve optional dependency guards in integration modules.
