"""Unit tests for ContextWindow V2 — canonicalized JSON hash, duplicate/empty rejection, sorting stability."""

import hashlib
import pytest

from aurora.core.models.common import SourceLocator
from aurora.core.models.document import ContentUnit
from aurora.core.models.enums import ContentUnitType
from aurora.extraction.context_window import (
    ContentUnitRef,
    ContextWindow,
    ContextWindowError,
)


def _make_unit(
    unit_id: str,
    sequence_no: int,
    text: str,
    doc_id: str = "doc_1",
    unit_type: ContentUnitType = ContentUnitType.PARAGRAPH,
) -> ContentUnit:
    return ContentUnit(
        id=unit_id,
        document_id=doc_id,
        unit_type=unit_type,
        sequence_no=sequence_no,
        text=text,
        locator=SourceLocator(block_no=sequence_no + 1),
    )


class TestContextWindowV2Hash:
    """V2: Canonicalized JSON hash includes context_schema_version, document_id, units."""

    def test_sha256_identical_for_same_input(self):
        units = [_make_unit(f"cu_{i}", i, f"text_{i}") for i in range(3)]
        w1 = ContextWindow.from_content_units("doc_1", units)
        w2 = ContextWindow.from_content_units("doc_1", units)
        assert w1.window_sha256 == w2.window_sha256

    def test_sha256_changes_with_different_text(self):
        units1 = [_make_unit("cu_0", 0, "hello")]
        units2 = [_make_unit("cu_0", 0, "world")]
        w1 = ContextWindow.from_content_units("doc_1", units1)
        w2 = ContextWindow.from_content_units("doc_1", units2)
        assert w1.window_sha256 != w2.window_sha256

    def test_sha256_changes_with_different_document_id(self):
        """V2: document_id is part of the hash, so different doc → different hash."""
        units = [_make_unit("cu_0", 0, "hello", doc_id="doc_x")]
        w1 = ContextWindow.from_content_units("doc_x", units)
        # Need matching units
        units2 = [_make_unit("cu_0", 0, "hello", doc_id="doc_y")]
        w2 = ContextWindow.from_content_units("doc_y", units2)
        assert w1.window_sha256 != w2.window_sha256

    def test_sha256_changes_with_different_unit_type(self):
        units1 = [_make_unit("cu_0", 0, "hello", unit_type=ContentUnitType.PARAGRAPH)]
        units2 = [_make_unit("cu_0", 0, "hello", unit_type=ContentUnitType.HEADING)]
        w1 = ContextWindow.from_content_units("doc_1", units1)
        w2 = ContextWindow.from_content_units("doc_1", units2)
        assert w1.window_sha256 != w2.window_sha256

    def test_sha256_length_is_64_hex(self):
        units = [_make_unit("cu_0", 0, "hello")]
        w = ContextWindow.from_content_units("doc_1", units)
        assert len(w.window_sha256) == 64
        assert all(c in "0123456789abcdef" for c in w.window_sha256)

    def test_schema_version_included(self):
        units = [_make_unit("cu_0", 0, "hello")]
        w = ContextWindow.from_content_units("doc_1", units)
        assert w.context_schema_version == "1.0"

    def test_input_order_does_not_affect_hash(self):
        """Random input order → deterministic sorted output → same hash."""
        units = [_make_unit(f"cu_{i}", i, f"text_{i}") for i in range(5)]
        import random
        random.seed(42)
        shuffled = list(units)
        random.shuffle(shuffled)

        w1 = ContextWindow.from_content_units("doc_1", units)
        w2 = ContextWindow.from_content_units("doc_1", shuffled)
        assert w1.window_sha256 == w2.window_sha256


class TestContextWindowSortingStability:
    """G1-6: ContextWindow must have deterministic, stable ordering."""

    def test_units_sorted_by_sequence_no_ascending(self):
        units = [
            _make_unit("cu_3", 3, "third"),
            _make_unit("cu_1", 1, "first"),
            _make_unit("cu_2", 2, "second"),
        ]
        window = ContextWindow.from_content_units("doc_1", units)
        seqs = [u.sequence_no for u in window.units]
        assert seqs == [1, 2, 3]

    def test_tie_break_by_unit_id(self):
        units = [
            _make_unit("cu_c", 1, "c"),
            _make_unit("cu_a", 1, "a"),
            _make_unit("cu_b", 1, "b"),
        ]
        window = ContextWindow.from_content_units("doc_1", units)
        ids = [u.unit_id for u in window.units]
        assert ids == ["cu_a", "cu_b", "cu_c"]

    def test_same_input_produces_same_order(self):
        units = [_make_unit(f"cu_{i}", i, f"text_{i}") for i in range(5)]
        import random
        random.seed(42)
        shuffled = list(units)
        random.shuffle(shuffled)

        window1 = ContextWindow.from_content_units("doc_1", units)
        window2 = ContextWindow.from_content_units("doc_1", shuffled)
        window3 = ContextWindow.from_content_units("doc_1", shuffled)

        ids1 = [u.unit_id for u in window1.units]
        ids2 = [u.unit_id for u in window2.units]
        ids3 = [u.unit_id for u in window3.units]
        assert ids1 == ids2 == ids3


class TestContextWindowValidation:
    """V2: Rejects empty windows, duplicates, cross-document units."""

    def test_rejects_empty_window(self):
        with pytest.raises(ContextWindowError, match="at least one unit"):
            ContextWindow.from_content_units("doc_1", [])

    def test_rejects_duplicate_unit_ids(self):
        units = [
            _make_unit("cu_dup", 0, "first"),
            _make_unit("cu_dup", 1, "second"),
        ]
        with pytest.raises(ContextWindowError, match="Duplicate unit_id"):
            ContextWindow.from_content_units("doc_1", units)

    def test_rejects_duplicate_sequence_unit_id_pairs(self):
        # Same seq_no + same unit_id should be caught by unit_id check first
        units = [
            _make_unit("cu_a", 1, "a"),
            _make_unit("cu_a", 1, "a"),
        ]
        with pytest.raises(ContextWindowError, match="Duplicate unit_id"):
            ContextWindow.from_content_units("doc_1", units)

    def test_rejects_cross_document_units(self):
        units = [_make_unit("cu_0", 0, "hello", doc_id="doc_other")]
        with pytest.raises(ContextWindowError):
            ContextWindow.from_content_units("doc_target", units)


class TestContextWindowUnitReference:
    """ContextWindow must provide correct CU lookup capabilities."""

    def test_unit_ids_returns_all_ids(self):
        units = [_make_unit(f"cu_{i}", i, f"text_{i}") for i in range(3)]
        window = ContextWindow.from_content_units("doc_1", units)
        assert window.unit_ids == frozenset({"cu_0", "cu_1", "cu_2"})

    def test_get_unit_by_id_found(self):
        units = [_make_unit("cu_42", 0, "hello")]
        window = ContextWindow.from_content_units("doc_1", units)
        unit = window.get_unit_by_id("cu_42")
        assert unit is not None
        assert unit.text == "hello"

    def test_get_unit_by_id_not_found(self):
        units = [_make_unit("cu_1", 0, "hello")]
        window = ContextWindow.from_content_units("doc_1", units)
        assert window.get_unit_by_id("nonexistent") is None

    def test_has_unit(self):
        units = [_make_unit("cu_1", 0, "hello")]
        window = ContextWindow.from_content_units("doc_1", units)
        assert window.has_unit("cu_1")
        assert not window.has_unit("cu_missing")

    def test_get_unit_text(self):
        units = [_make_unit("cu_1", 0, "sample text")]
        window = ContextWindow.from_content_units("doc_1", units)
        assert window.get_unit_text("cu_1") == "sample text"
        assert window.get_unit_text("missing") is None

    def test_all_text_concatenation(self):
        units = [
            _make_unit("cu_0", 0, "line1"),
            _make_unit("cu_1", 1, "line2"),
        ]
        window = ContextWindow.from_content_units("doc_1", units)
        assert window.all_text() == "line1\nline2"

    def test_len(self):
        units = [_make_unit(f"cu_{i}", i, f"text_{i}") for i in range(5)]
        window = ContextWindow.from_content_units("doc_1", units)
        assert len(window) == 5


class TestContentUnitRef:
    """ContentUnitRef correctly captures immutable CU snapshot."""

    def test_from_content_unit(self):
        unit = _make_unit("cu_test", 0, "test text")
        ref = ContentUnitRef.from_content_unit(unit)
        assert ref.unit_id == "cu_test"
        assert ref.sequence_no == 0
        assert ref.text == "test text"
        assert ref.document_id == "doc_1"
        assert ref.unit_type == ContentUnitType.PARAGRAPH.value

    def test_text_sha256(self):
        ref = ContentUnitRef(
            unit_id="cu_1", sequence_no=0, unit_type="paragraph",
            text="hello", document_id="doc_1",
        )
        expected = hashlib.sha256("hello".encode("utf-8")).hexdigest()
        assert ref.text_sha256 == expected

    def test_locator_sha256(self):
        ref1 = ContentUnitRef(
            unit_id="cu_1", sequence_no=0, unit_type="paragraph",
            text="hello", document_id="doc_1",
        )
        ref2 = ContentUnitRef(
            unit_id="cu_1", sequence_no=0, unit_type="paragraph",
            text="hello", document_id="doc_1",
        )
        assert ref1.locator_sha256 == ref2.locator_sha256

    def test_to_hash_dict(self):
        ref = ContentUnitRef(
            unit_id="cu_1", sequence_no=0, unit_type="paragraph",
            text="hello", document_id="doc_1",
        )
        d = ref.to_hash_dict()
        assert d["unit_id"] == "cu_1"
        assert d["sequence_no"] == 0
        assert d["unit_type"] == "paragraph"
        assert "text_sha256" in d
        assert "locator_sha256" in d
        assert len(d["text_sha256"]) == 64

    def test_immutability(self):
        ref = ContentUnitRef(
            unit_id="cu_1", sequence_no=0, unit_type="paragraph",
            text="hello", document_id="doc_1",
        )
        with pytest.raises(Exception):
            ref.unit_id = "changed"
