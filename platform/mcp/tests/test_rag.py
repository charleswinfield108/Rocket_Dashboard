"""
Tests for tools/rag.py — search_manuals and search_incidents.

Two test layers:
  Unit tests   — mock ChromaDB; verify validation, result shaping, no-match signal.
  Integration  — hit the real ChromaDB collections built by rag/ingest.py.
                 Skipped automatically if chroma_data/ has not been populated.
                 These tests prove semantic matching works across paraphrase gaps.

Run unit tests only:
    pytest tests/test_rag.py -m "not integration"

Run everything (requires populated chroma_data/):
    pytest tests/test_rag.py
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.rag import (
    search_manuals,
    search_incidents,
    _dist_to_score,
    _validate_query,
    _validate_k,
    NO_MATCH_THRESHOLD,
)

# ── Integration-test guard ────────────────────────────────────────────────────

_CHROMA_PATH = Path(__file__).parent.parent / "rag" / "chroma_data"
_COLLECTIONS_EXIST = (
    (_CHROMA_PATH / "chroma.sqlite3").exists()
    or any(_CHROMA_PATH.glob("*.parquet"))
    or _CHROMA_PATH.is_dir() and any(_CHROMA_PATH.iterdir())
    if _CHROMA_PATH.exists()
    else False
)

integration = pytest.mark.skipif(
    not _COLLECTIONS_EXIST,
    reason="chroma_data/ not populated — run rag/ingest.py first",
)


# ── Mock helpers ──────────────────────────────────────────────────────────────

def _make_chroma_result(docs, metadatas, distances):
    """Return a value shaped like col.query(...) output."""
    return {
        "documents":  [docs],
        "metadatas":  [metadatas],
        "distances":  [distances],
    }


def _mock_collection(docs, metadatas, distances, count=100):
    col = MagicMock()
    col.count.return_value = count
    col.query.return_value = _make_chroma_result(docs, metadatas, distances)
    return col


# ── _dist_to_score ────────────────────────────────────────────────────────────

class TestDistToScore:
    def test_zero_distance_is_one(self):
        assert _dist_to_score(0.0) == 1.0

    def test_two_is_zero(self):
        assert _dist_to_score(2.0) == 0.0

    def test_beyond_two_clamps_to_zero(self):
        assert _dist_to_score(3.0) == 0.0

    def test_midpoint(self):
        assert _dist_to_score(1.0) == pytest.approx(0.5, rel=1e-3)

    def test_good_match(self):
        score = _dist_to_score(0.3)
        assert score > 0.8


# ── Validation ────────────────────────────────────────────────────────────────

class TestValidateQuery:
    def test_valid_string(self):
        _validate_query("hydraulic pressure loss")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _validate_query("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            _validate_query("   ")

    def test_non_string_raises(self):
        with pytest.raises(TypeError):
            _validate_query(123)  # type: ignore


class TestValidateK:
    def test_valid_range(self):
        _validate_k(1)
        _validate_k(5)
        _validate_k(20)

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            _validate_k(0)

    def test_over_max_raises(self):
        with pytest.raises(ValueError):
            _validate_k(21)

    def test_bool_raises(self):
        with pytest.raises(TypeError):
            _validate_k(True)  # type: ignore

    def test_float_raises(self):
        with pytest.raises(TypeError):
            _validate_k(5.0)  # type: ignore


# ── search_manuals — unit tests ───────────────────────────────────────────────

class TestSearchManualsUnit:
    _meta = {
        "source_type":   "manual",
        "document_name": "hydraulic_maintenance",
        "section":       "Control Valve - Adjustment and Testing",
        "page_start":    3,
        "chunk_index":   4,
    }
    _doc  = "The control valve governs up-direction speed and pressure relief."
    _dist = 0.28   # good match

    def _patched(self, docs, metas, dists):
        col = _mock_collection(docs, metas, dists)
        return patch("tools.rag._get_collection", return_value=col)

    def test_found_true_on_good_match(self):
        with self._patched([self._doc], [self._meta], [self._dist]):
            result = search_manuals("hydraulic pressure")
        assert result["found"] is True

    def test_hit_count(self):
        with self._patched([self._doc, self._doc], [self._meta, self._meta], [0.28, 0.45]):
            result = search_manuals("hydraulic pressure", k=2)
        assert result["count"] == 2

    def test_citation_fields_present(self):
        with self._patched([self._doc], [self._meta], [self._dist]):
            hit = search_manuals("hydraulic pressure")["hits"][0]
        assert hit["document_name"] == "hydraulic_maintenance"
        assert hit["section"] == "Control Valve - Adjustment and Testing"
        assert hit["page_start"] == 3

    def test_score_is_float(self):
        with self._patched([self._doc], [self._meta], [self._dist]):
            score = search_manuals("hydraulic pressure")["hits"][0]["score"]
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_text_present(self):
        with self._patched([self._doc], [self._meta], [self._dist]):
            hit = search_manuals("hydraulic")["hits"][0]
        assert hit["text"] == self._doc

    def test_source_field(self):
        with self._patched([self._doc], [self._meta], [self._dist]):
            result = search_manuals("pressure")
        assert result["source"] == "manuals"

    def test_query_echoed(self):
        with self._patched([self._doc], [self._meta], [self._dist]):
            result = search_manuals("pressure drop")
        assert result["query"] == "pressure drop"

    # no-match cases

    def test_no_match_on_high_distance(self):
        with self._patched([self._doc], [self._meta], [NO_MATCH_THRESHOLD + 0.1]):
            result = search_manuals("xyzzy flurble nonsense")
        assert result["found"] is False

    def test_no_match_has_message(self):
        with self._patched([self._doc], [self._meta], [NO_MATCH_THRESHOLD + 0.1]):
            result = search_manuals("xyzzy flurble nonsense")
        assert "message" in result
        assert len(result["message"]) > 10

    def test_no_match_has_no_hits_key(self):
        with self._patched([self._doc], [self._meta], [NO_MATCH_THRESHOLD + 0.1]):
            result = search_manuals("xyzzy flurble nonsense")
        assert "hits" not in result

    def test_empty_collection_returns_no_match(self):
        col = _mock_collection([], [], [], count=0)
        col.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        with patch("tools.rag._get_collection", return_value=col):
            result = search_manuals("hydraulic")
        assert result["found"] is False

    # validation

    def test_invalid_query_raises(self):
        with pytest.raises(ValueError):
            search_manuals("")

    def test_invalid_k_raises(self):
        with pytest.raises(ValueError):
            search_manuals("query", k=0)


# ── search_incidents — unit tests ─────────────────────────────────────────────

class TestSearchIncidentsUnit:
    _meta = {
        "source_type": "incident",
        "incident_id": 518574,
        "date":        "2011-01-06",
        "category":    "ED-Near Miss",
    }
    _doc  = "Incident #518574 (2011-01-06)\nCategory: ED-Near Miss\nFlood on 13th floor."
    _dist = 0.31

    def _patched(self, docs, metas, dists):
        col = _mock_collection(docs, metas, dists)
        return patch("tools.rag._get_collection", return_value=col)

    def test_found_true_on_good_match(self):
        with self._patched([self._doc], [self._meta], [self._dist]):
            result = search_incidents("flooding elevator shaft")
        assert result["found"] is True

    def test_citation_fields_present(self):
        with self._patched([self._doc], [self._meta], [self._dist]):
            hit = search_incidents("flooding")["hits"][0]
        assert hit["incident_id"] == 518574
        assert hit["date"] == "2011-01-06"
        assert hit["category"] == "ED-Near Miss"

    def test_score_range(self):
        with self._patched([self._doc], [self._meta], [self._dist]):
            score = search_incidents("flooding")["hits"][0]["score"]
        assert 0.0 < score <= 1.0

    def test_source_field(self):
        with self._patched([self._doc], [self._meta], [self._dist]):
            result = search_incidents("flooding")
        assert result["source"] == "incidents"

    def test_no_match_on_high_distance(self):
        with self._patched([self._doc], [self._meta], [NO_MATCH_THRESHOLD + 0.1]):
            result = search_incidents("xyzzy flurble nonsense")
        assert result["found"] is False

    def test_no_match_has_message(self):
        with self._patched([self._doc], [self._meta], [NO_MATCH_THRESHOLD + 0.1]):
            result = search_incidents("xyzzy flurble nonsense")
        assert "message" in result

    def test_invalid_k_bool_raises(self):
        with pytest.raises(TypeError):
            search_incidents("flood", k=True)  # type: ignore


# ── Integration tests — real ChromaDB, proves semantic matching ───────────────

class TestSearchManualsIntegration:
    @integration
    def test_hydraulic_pressure_drop_finds_hydraulic_doc(self):
        """
        "hydraulic pressure drops" (user phrasing) must retrieve content about
        "hydraulic pressure loss / pressure test" (source phrasing).
        Proves embedding similarity bridges the paraphrase gap.
        """
        result = search_manuals("hydraulic pressure drops", k=5)
        assert result["found"] is True, (
            "Expected a hit for 'hydraulic pressure drops' but got no-match. "
            "Check that the collections were populated with ingest.py."
        )
        top = result["hits"][0]
        assert "hydraulic" in top["document_name"].lower() or \
               "hydraulic" in (top["section"] or "").lower() or \
               "hydraulic" in top["text"].lower(), (
            f"Top hit doesn't seem to be about hydraulics: {top}"
        )

    @integration
    def test_brake_adjustment_finds_traction_doc(self):
        result = search_manuals("how to adjust the brake", k=5)
        assert result["found"] is True
        texts = " ".join(h["text"] for h in result["hits"])
        assert "brake" in texts.lower()

    @integration
    def test_scores_are_descending(self):
        result = search_manuals("door reversal device test", k=5)
        if result["found"]:
            scores = [h["score"] for h in result["hits"]]
            assert scores == sorted(scores, reverse=True), "Hits must be ordered best-first"

    @integration
    def test_out_of_domain_query_returns_no_match(self):
        """
        A question clearly outside elevator maintenance should score below the
        threshold so the chatbot doesn't hallucinate a source.
        """
        result = search_manuals("recipe for chocolate cake with vanilla frosting", k=5)
        assert result["found"] is False, (
            "Out-of-domain query should not exceed the relevance threshold "
            f"(dist={result.get('top_distance')})"
        )

    @integration
    def test_citation_metadata_complete(self):
        result = search_manuals("safety code inspection requirement", k=3)
        if result["found"]:
            for hit in result["hits"]:
                assert hit["document_name"] is not None
                assert hit["section"] is not None


class TestSearchIncidentsIntegration:
    @integration
    def test_entrapment_query_finds_incidents(self):
        """
        "passenger got stuck inside elevator" must retrieve incidents about
        entrapment — proves semantic similarity works across narrative paraphrases.
        """
        result = search_incidents("passenger got stuck inside elevator", k=5)
        assert result["found"] is True, (
            "Expected entrapment incidents but got no-match. "
            "Check that the incidents collection is populated."
        )

    @integration
    def test_flooding_query_finds_flood_incidents(self):
        result = search_incidents("water flooding into elevator pit", k=5)
        assert result["found"] is True
        texts = " ".join(h["text"] for h in result["hits"])
        assert any(w in texts.lower() for w in ("flood", "water", "rain", "pipe"))

    @integration
    def test_citation_fields_present(self):
        result = search_incidents("door malfunction entrapment", k=3)
        if result["found"]:
            for hit in result["hits"]:
                assert "incident_id" in hit
                assert "date" in hit
                assert "category" in hit

    @integration
    def test_out_of_domain_query_returns_no_match(self):
        result = search_incidents("annual mortgage interest rate calculation refinancing", k=5)
        assert result["found"] is False, (
            "Out-of-domain query should not exceed the relevance threshold"
        )
