import io
from contextlib import redirect_stdout

import numpy as np
import pytest

import corpulse.core as c_mod
from corpulse.core import Corpulse, _vec_to_bytes
from corpulse.backends.memory import InMemoryBackend


FROZEN = 1_700_000_000.0

EXPECTED_REPORT_OUTPUT = (
    "\n"
    "  corpulse — Corpus Health Report\n"
    "  10 documents · last 30 days · ⚠ corpus bloat detected (70% noise est.)\n"
    "  Document                             Retrieved   Engagement  Status\n"
    "  ──────────────────────────────────────────────────────────────────────\n"
    "  noisy.md                                    10          10%  ◌  low eng.\n"
    "  healthy_a.md                                 8          38%  ✓  healthy\n"
    "  healthy_b.md                                 7          29%  ✓  healthy\n"
    "  guide-v2.md                                  6          33%  ✓  healthy\n"
    "  api-v2.md                                    5          20%  ✓  healthy\n"
    "  stale.md                                     3           0%  🕓 stale emb.\n"
    "  api-v1.md                                    2           0%  ⚠  obsolete\n"
    "  guide-v1.md                                  1           0%  ⚠  obsolete\n"
    "  ghost_a.md                                   0            —  👻 ghost\n"
    "  ghost_b.md                                   0            —  👻 ghost\n"
    "\n"
    "  👻 ghosts: 2  💀 obsolete: 2  ⚠ duplicates: 4  🕓 stale: 1\n"
    "  Run corpulse.cleanup_report() for a prioritised action list.\n"
    "\n"
)
EXPECTED_CLEANUP_OUTPUT = (
    "\n"
    "────────────────────────────────────────────────────────────\n"
    "  corpulse — Cleanup Report\n"
    "────────────────────────────────────────────────────────────\n"
    "  Total documents : 10\n"
    "  Noise estimate  : 70%\n"
    "  ⚠  Consider pruning ~7 low-signal documents.\n"
    "\n"
    "  👻  GHOSTS  (2 docs — never retrieved in 30d)\n"
    "      · ghost_a.md\n"
    "      · ghost_b.md\n"
    "\n"
    "  💀  OBSOLETE  (2 docs)\n"
    "      · api-v1.md  →  superseded by api-v2.md\n"
    "      · guide-v1.md  →  superseded by guide-v2.md\n"
    "\n"
    "  🕓  STALE EMBEDDINGS  (1 docs)\n"
    "      · stale.md  (40d behind — source 2023-11-04, embedded 2023-09-25)\n"
    "\n"
    "  🔁  RE-CHUNK CANDIDATES  (1 docs — high retrieval, low engagement)\n"
    "      · noisy.md  (10 retrievals, 10% engagement)\n"
    "\n"
    "────────────────────────────────────────────────────────────\n"
    "\n"
)


@pytest.fixture(autouse=True)
def _freeze_now(monkeypatch):
    monkeypatch.setattr(c_mod, "_now", lambda: FROZEN)


def _embedding(seed: int, dim: int = 8) -> bytes:
    rng = np.random.default_rng(seed)
    vec = rng.random(dim).astype(np.float32)
    return _vec_to_bytes(vec / np.linalg.norm(vec))


def _report_fixture_backend() -> InMemoryBackend:
    backend = InMemoryBackend()

    docs = [
        ("ghost-a", "ghost_a.md", _embedding(1), FROZEN - 4 * 86400),
        ("ghost-b", "ghost_b.md", _embedding(2), FROZEN - 5 * 86400),
        ("api-v1", "api-v1.md", _embedding(3), FROZEN - 12 * 86400),
        ("api-v2", "api-v2.md", _embedding(3), FROZEN - 2 * 86400),
        ("guide-v1", "guide-v1.md", _embedding(4), FROZEN - 8 * 86400),
        ("guide-v2", "guide-v2.md", _embedding(5), FROZEN - 1 * 86400),
        ("stale-doc", "stale.md", _embedding(6), FROZEN - 50 * 86400),
        ("noisy-doc", "noisy.md", _embedding(7), FROZEN - 6 * 86400),
        ("healthy-a", "healthy_a.md", _embedding(8), FROZEN - 3 * 86400),
        ("healthy-b", "healthy_b.md", _embedding(9), FROZEN - 3 * 86400),
    ]

    for doc_id, filename, embedding, embedded_at in docs:
        backend.upsert_document(doc_id, filename, embedding=embedding, embedded_at=embedded_at)

    backend.update_source_timestamp("ghost-a", FROZEN - 4 * 86400)
    backend.update_source_timestamp("ghost-b", FROZEN - 5 * 86400)
    backend.update_source_timestamp("api-v1", FROZEN - 1 * 86400)
    backend.update_source_timestamp("api-v2", FROZEN - 1 * 86400)
    backend.update_source_timestamp("guide-v1", FROZEN - 2 * 86400)
    backend.update_source_timestamp("guide-v2", FROZEN - 1 * 86400)
    backend.update_source_timestamp("stale-doc", FROZEN - 10 * 86400)
    backend.update_source_timestamp("noisy-doc", FROZEN - 2 * 86400)
    backend.update_source_timestamp("healthy-a", FROZEN - 2 * 86400)
    backend.update_source_timestamp("healthy-b", FROZEN - 2 * 86400)

    recent_ts = FROZEN - 5 * 86400

    for i in range(2):
        backend.insert_retrieval("api-v1", f"api-v1-q{i}", 1, 0.81, recent_ts)
    for i in range(5):
        backend.insert_retrieval("api-v2", f"api-v2-q{i}", 1, 0.96, recent_ts)
    for i in range(1):
        backend.insert_retrieval("guide-v1", f"guide-v1-q{i}", 1, 0.72, recent_ts)
    for i in range(6):
        backend.insert_retrieval("guide-v2", f"guide-v2-q{i}", 1, 0.95, recent_ts)
    for i in range(3):
        backend.insert_retrieval("stale-doc", f"stale-q{i}", 1, 0.7, recent_ts)
    for i in range(10):
        backend.insert_retrieval("noisy-doc", f"noisy-q{i}", 1, 0.75, recent_ts)
    for i in range(8):
        backend.insert_retrieval("healthy-a", f"healthy-a-q{i}", 1, 0.97, recent_ts)
    for i in range(7):
        backend.insert_retrieval("healthy-b", f"healthy-b-q{i}", 1, 0.91, recent_ts)

    backend.insert_engagement("api-v2", "opened", recent_ts)
    for _ in range(2):
        backend.insert_engagement("guide-v2", "opened", recent_ts)
    backend.insert_engagement("noisy-doc", "opened", recent_ts)
    for _ in range(3):
        backend.insert_engagement("healthy-a", "opened", recent_ts)
    for _ in range(2):
        backend.insert_engagement("healthy-b", "opened", recent_ts)

    return backend


def test_baseline_capture_report_output():
    corpulse = Corpulse(backend=_report_fixture_backend())
    buf = io.StringIO()

    with redirect_stdout(buf):
        corpulse.report(window_days=30)

    assert buf.getvalue() == EXPECTED_REPORT_OUTPUT


def test_baseline_capture_cleanup_output():
    corpulse = Corpulse(backend=_report_fixture_backend())
    buf = io.StringIO()

    with redirect_stdout(buf):
        corpulse.cleanup_report()

    assert buf.getvalue() == EXPECTED_CLEANUP_OUTPUT
