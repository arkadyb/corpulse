import io
import builtins
import sys
from contextlib import redirect_stdout
from types import SimpleNamespace

import numpy as np
import pytest

import corpulse.core as c_mod
from corpulse.core import (
    Corpulse,
    _build_cleanup_payload,
    _build_dataframe_rows,
    _build_report_rows,
    _build_report_summary,
)
from tests.report_fixtures import (
    FROZEN,
    build_report_fixture_backend,
    build_report_fixture_snapshot,
)


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


def _helper_inputs():
    corpulse = Corpulse(backend=build_report_fixture_backend())
    window_days = 30
    since = c_mod._days_ago(window_days)
    all_docs = corpulse.db.all_documents()
    r_map = {row["doc_id"]: row for row in corpulse.db.retrieval_counts(since=since)}
    e_map = {row["doc_id"]: row["cnt"] for row in corpulse.db.engagement_counts(since=since)}
    ghosts = corpulse.get_ghosts()
    obsolete = corpulse.get_obsolete()
    stale = corpulse.get_stale_embeddings()
    health = corpulse.corpus_health()
    suspects = corpulse.get_suspects()
    return {
        "all_docs": all_docs,
        "r_map": r_map,
        "e_map": e_map,
        "ghost_ids": {row["doc_id"] for row in ghosts},
        "obsolete_ids": {row["doc_id"] for row in obsolete},
        "stale_ids": {row["doc_id"] for row in stale},
        "health": health,
        "ghosts": ghosts,
        "obsolete": obsolete,
        "stale": stale,
        "suspects": suspects,
        "window_days": window_days,
    }


def test_baseline_capture_report_output():
    corpulse = Corpulse(backend=build_report_fixture_backend())
    buf = io.StringIO()

    with redirect_stdout(buf):
        corpulse.report(window_days=30)

    assert buf.getvalue() == EXPECTED_REPORT_OUTPUT


def test_baseline_capture_cleanup_output():
    corpulse = Corpulse(backend=build_report_fixture_backend())
    buf = io.StringIO()

    with redirect_stdout(buf):
        corpulse.cleanup_report()

    assert buf.getvalue() == EXPECTED_CLEANUP_OUTPUT


def test_report_stdout_unchanged(capsys):
    corpulse = Corpulse(backend=build_report_fixture_backend())

    corpulse.report(window_days=30)

    assert capsys.readouterr().out == EXPECTED_REPORT_OUTPUT


def test_cleanup_report_stdout_unchanged(capsys):
    corpulse = Corpulse(backend=build_report_fixture_backend())

    corpulse.cleanup_report()

    assert capsys.readouterr().out == EXPECTED_CLEANUP_OUTPUT


def test_to_dataframe_raises_without_pandas(monkeypatch):
    corpulse = Corpulse(backend=build_report_fixture_backend())
    orig_import = builtins.__import__

    def _missing_pandas(name, *args, **kwargs):
        if name == "pandas":
            raise ImportError("forced missing pandas")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _missing_pandas)

    with pytest.raises(RuntimeError, match="^pip install pandas to use to_dataframe\\(\\)$"):
        corpulse.to_dataframe()


def test_to_dataframe_happy_path(monkeypatch):
    corpulse = Corpulse(backend=build_report_fixture_backend())
    orig_import = builtins.__import__

    class FakeSeries:
        def __init__(self, values):
            self._values = values

        def head(self, n):
            return self._values[:n]

        def __iter__(self):
            return iter(self._values)

    class FakeILoc:
        def __init__(self, rows):
            self._rows = rows

        def __getitem__(self, index):
            return self._rows[index]

    class FakeDataFrame:
        def __init__(self, rows):
            self._rows = list(rows)
            self.columns = list(rows[0].keys()) if rows else []
            self.iloc = FakeILoc(self._rows)

        def sort_values(self, key, ascending=False):
            return FakeDataFrame(
                sorted(self._rows, key=lambda row: row[key], reverse=not ascending)
            )

        def __getitem__(self, key):
            return FakeSeries([row[key] for row in self._rows])

    def _fake_pandas(name, *args, **kwargs):
        if name == "pandas":
            return SimpleNamespace(DataFrame=FakeDataFrame)
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_pandas)

    df = corpulse.to_dataframe(window_days=30)

    assert list(df.columns) == [
        "doc_id",
        "filename",
        "retrievals",
        "engagements",
        "engagement_rate",
        "status",
    ]
    assert df.iloc[0]["filename"] == "noisy.md"
    assert list(df["retrievals"].head(4)) == [10, 8, 7, 6]


def test_report_fallback_without_tabulate(monkeypatch, capsys):
    corpulse = Corpulse(backend=build_report_fixture_backend())
    orig_import = builtins.__import__

    def _missing_tabulate(name, *args, **kwargs):
        if name == "tabulate":
            raise ImportError("forced missing tabulate")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _missing_tabulate)

    corpulse.report(window_days=30)

    out = capsys.readouterr().out
    assert "Document" in out
    assert "Retrieved" in out
    assert "Engagement" in out
    assert "Status" in out
    assert "👻 ghosts:" in out
    assert "Run corpulse.cleanup_report() for a prioritised action list." in out


def test_report_with_tabulate_installed(monkeypatch, capsys):
    corpulse = Corpulse(backend=build_report_fixture_backend())
    orig_import = builtins.__import__
    calls = {}

    def _fake_tabulate(rows, headers, tablefmt):
        calls["rows"] = rows
        calls["headers"] = headers
        calls["tablefmt"] = tablefmt
        return "<tabulated>"

    def _with_tabulate(name, *args, **kwargs):
        if name == "tabulate":
            return SimpleNamespace(tabulate=_fake_tabulate)
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _with_tabulate)
    monkeypatch.delitem(sys.modules, "tabulate", raising=False)

    corpulse.report(window_days=30)

    out = capsys.readouterr().out
    assert "<tabulated>" in out
    assert calls["headers"] == ["Document", "Retrieved", "Engagement", "Status"]
    assert calls["tablefmt"] == "rounded_outline"
    assert calls["rows"][0] == ["noisy.md", 10, "10%", "◌  low eng."]


def test_build_dataframe_rows():
    inputs = _helper_inputs()

    rows = _build_dataframe_rows(
        inputs["all_docs"],
        inputs["r_map"],
        inputs["e_map"],
        inputs["ghost_ids"],
        inputs["obsolete_ids"],
        inputs["stale_ids"],
    )

    by_id = {row["doc_id"]: row for row in rows}
    assert set(by_id["noisy-doc"]) == {
        "doc_id",
        "filename",
        "retrievals",
        "engagements",
        "engagement_rate",
        "status",
    }
    assert by_id["noisy-doc"] == {
        "doc_id": "noisy-doc",
        "filename": "noisy.md",
        "retrievals": 10,
        "engagements": 1,
        "engagement_rate": 0.1,
        "status": "low_engagement",
    }
    assert by_id["ghost-a"]["status"] == "ghost"
    assert by_id["api-v1"]["status"] == "obsolete"
    assert by_id["stale-doc"]["status"] == "stale"
    assert by_id["healthy-a"]["status"] == "healthy"

    divergent_docs = [{"doc_id": "boundary", "filename": "boundary.md"}]
    r_map = {"boundary": {"doc_id": "boundary", "cnt": 20}}
    e_map = {"boundary": 3 - 1e-9}
    dataframe_rows = _build_dataframe_rows(divergent_docs, r_map, e_map, set(), set(), set())
    assert dataframe_rows[0]["engagement_rate"] == 0.15
    assert dataframe_rows[0]["status"] != "low_engagement"


def test_shared_report_fixture_snapshot_matches_seed_backend():
    snapshot = build_report_fixture_snapshot()
    backend = build_report_fixture_backend()

    assert [doc["doc_id"] for doc in snapshot["documents"]] == [
        doc["doc_id"] for doc in backend.all_documents()
    ]
    assert snapshot["retrieval_rows"][0]["doc_id"] == "api-v1"
    assert snapshot["engagement_rows"] == backend.engagement_counts(
        since=c_mod._days_ago(snapshot["window_days"])
    )


def test_build_report_rows():
    inputs = _helper_inputs()

    rows = _build_report_rows(
        inputs["all_docs"],
        inputs["r_map"],
        inputs["e_map"],
        inputs["ghost_ids"],
        inputs["obsolete_ids"],
        inputs["stale_ids"],
        top_k=4,
    )

    assert [row["filename"] for row in rows] == [
        "noisy.md",
        "healthy_a.md",
        "healthy_b.md",
        "guide-v2.md",
    ]
    assert set(rows[0]) == {
        "filename",
        "retrievals",
        "engagement_rate",
        "status",
        "status_display",
    }
    assert rows[0]["status"] == "low_engagement"
    assert rows[0]["status_display"] == "◌  low eng."
    assert rows[1]["engagement_rate"] == "38%"

    full_rows = _build_report_rows(
        inputs["all_docs"],
        inputs["r_map"],
        inputs["e_map"],
        inputs["ghost_ids"],
        inputs["obsolete_ids"],
        inputs["stale_ids"],
        top_k=20,
    )
    status_display = {row["filename"]: row["status_display"] for row in full_rows}
    assert status_display["ghost_a.md"] == "👻 ghost"
    assert status_display["api-v1.md"] == "⚠  obsolete"
    assert status_display["stale.md"] == "🕓 stale emb."
    assert status_display["healthy_a.md"] == "✓  healthy"

    divergent_docs = [{"doc_id": "boundary", "filename": "boundary.md"}]
    r_map = {"boundary": {"doc_id": "boundary", "cnt": 20}}
    e_map = {"boundary": 3 - 1e-9}
    report_rows = _build_report_rows(divergent_docs, r_map, e_map, set(), set(), set(), top_k=1)
    assert report_rows[0]["engagement_rate"] == "15%"
    assert report_rows[0]["status"] == "low_engagement"


def test_build_report_summary():
    inputs = _helper_inputs()

    summary = _build_report_summary(
        inputs["all_docs"],
        inputs["window_days"],
        inputs["health"],
    )

    assert summary == {
        "total_docs": 10,
        "window_days": 30,
        "bloat_warning": True,
        "noise_pct": 70.0,
        "ghosts": 2,
        "obsolete": 2,
        "duplicates": 4,
        "stale": 1,
        "recommendation": "Consider pruning ~7 low-signal documents.",
    }


def test_build_cleanup_payload():
    inputs = _helper_inputs()

    payload = _build_cleanup_payload(
        inputs["health"],
        inputs["ghosts"],
        inputs["obsolete"],
        inputs["stale"],
        inputs["suspects"],
        ghost_threshold_days=30,
    )

    assert set(payload) == {
        "total_docs",
        "noise_pct",
        "bloat_warning",
        "recommendation",
        "ghost_threshold_days",
        "ghosts",
        "obsolete",
        "stale",
        "suspects",
    }
    for section in ("ghosts", "obsolete", "stale", "suspects"):
        assert set(payload[section]) == {"count", "top5", "overflow"}

    assert payload["ghosts"] == {
        "count": 2,
        "top5": [
            {"doc_id": "ghost-a", "filename": "ghost_a.md"},
            {"doc_id": "ghost-b", "filename": "ghost_b.md"},
        ],
        "overflow": 0,
    }
    assert payload["obsolete"]["count"] == 2
    assert payload["stale"]["count"] == 1
    assert payload["suspects"]["count"] == 1

    empty_payload = _build_cleanup_payload(
        {
            "total_docs": 1,
            "noise_estimate": 0.0,
            "bloat_warning": False,
            "recommendation": "Corpus looks healthy.",
        },
        [],
        [],
        [],
        [],
        ghost_threshold_days=30,
    )
    assert empty_payload["ghosts"] == {"count": 0, "top5": [], "overflow": 0}
    assert empty_payload["obsolete"] == {"count": 0, "top5": [], "overflow": 0}
    assert empty_payload["stale"] == {"count": 0, "top5": [], "overflow": 0}
    assert empty_payload["suspects"] == {"count": 0, "top5": [], "overflow": 0}
