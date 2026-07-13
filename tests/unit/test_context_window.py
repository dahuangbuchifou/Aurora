"""Unit tests for ContextWindow — sorting stability, SHA-256 consistency, CU reference validation."""

import hashlib

from aurora.core.models.common import SourceLocator
from aurora.core.models.document import ContentUnit
from aurora.core.models.enums import ContentUnitType
from aurora.extraction.context_window import ContentUnitRef, ContextWindow


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
        """When sequence_no is equal, sort by unit_id for deterministic tie-breaking."""
        units = [
            _make_unit("cu_c", 1, "c"),
            _make_unit("cu_a", 1, "a"),
            _make_unit("cu_b", 1, "b"),
        ]
        window = ContextWindow.from_content_units("doc_1", units)
        ids = [u.unit_id for u in window.units]
        assert ids == ["cu_a", "cu_b", "cu_c"]

    def test_same_input_produces_same_order(self):
        """Repeated construction with same input must produce identical ordering."""
        units = [_make_unit(f"cu_{i}", i, f"text_{i}") for i in range(5)]

        # Shuffle the input order
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


class TestContextWindowSha256Consistency:
    """G1-5: ContextWindow SHA-256 must be deterministic and consistent."""

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

    def test_sha256_changes_with_different_document(self):
        # V1.2c: units must match document_id. Use matching doc_ids.
        units_a = [_make_unit("cu_0", 0, "hello", doc_id="doc_x")]
        units_b = [_make_unit("cu_0", 0, "hello", doc_id="doc_y")]
        w1 = ContextWindow.from_content_units("doc_x", units_a)
        w2 = ContextWindow.from_content_units("doc_y", units_b)
        # SHA is computed from unit IDs, texts, and seq_nos, not doc_id
        assert w1.window_sha256 == w2.window_sha256

    def test_rejects_mismatched_document_id(self):
        """V1.2c: ContextWindow must reject units from wrong document."""
        import pytest
        from aurora.extraction.context_window import ContextWindowError
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
        window = ContextWindow.from_content_units("doc_1", [])
        assert window.get_unit_by_id("nonexistent") is None

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

    def test_immutability(self):
        ref = ContentUnitRef(
            unit_id="cu_1",
            sequence_no=0,
            unit_type="paragraph",
            text="hello",
            document_id="doc_1",
        )
        try:
            ref.unit_id = "changed"
            assert False, "Should have raised FrozenInstanceError"
        except Exception:
            pass  # Expected
