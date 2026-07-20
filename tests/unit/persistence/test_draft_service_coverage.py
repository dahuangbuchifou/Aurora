"""Unit tests for draft_service.py error paths using mocking.

Covers error handlers and branch misses hard to reach via integration tests:
- SourceGraphError handler (B04 section)
- Source graph outer exception handler
- Phase 1 write failure
- Preflight failure
- Mapper failure
- Phase 2 write exception
- Phase 3 audit failure
- Dry run else path
"""

import pytest


def _make_mock_bundle():
    from unittest.mock import MagicMock
    bundle = MagicMock()
    bundle.bundle_sha256 = "a" * 64
    bundle.content_unit_window = (MagicMock(),)
    bundle.candidates = ()
    bundle.accepted_candidate_ids = ()
    bundle.context_hashes = {"window_sha256": "a" * 64}
    bundle.validation_findings = ()
    bundle.provider = "fixture"
    bundle.profile_name = "v1_adversarial"
    bundle.document_id = "doc_test"
    bundle.provider_version = "1.0"
    bundle.profile_version = "1.0"
    return bundle


class TestSourceGraphErrorHandler:
    def test_source_graph_error_triggers_handler(self):
        from unittest.mock import MagicMock, patch
        from aurora.persistence.draft_service import persist_drafts

        bundle = _make_mock_bundle()
        bundle.candidates = (MagicMock(),)
        bundle.candidates[0].source_unit_id = "cu_1"
        bundle.accepted_candidate_ids = ("cid_1",)

        mock_sessionmaker = MagicMock()
        mock_session = MagicMock()
        mock_sessionmaker.return_value.__enter__.return_value = mock_session
        mock_session.scalars.return_value.all.return_value = []

        with patch("aurora.persistence.draft_service.validate_bundle_preflight") as mock_pre, \
             patch("aurora.persistence.draft_service.map_accepted_candidates") as mock_map, \
             patch("aurora.persistence.draft_service.compute_independence_group") as mock_cu, \
             patch("aurora.persistence.draft_service._finalize_failed_run") as mock_fail:
            from aurora.core.models.enums import EntityType

            mock_entity = MagicMock()
            mock_entity.source_ref = "candidate:cid_1"
            mock_entity.id = "e1"
            mock_entity.object_type = "entity"
            mock_entity.schema_version = "1.1"
            mock_entity.created_by = "test"
            mock_entity.canonical_name = "Test Entity"
            mock_entity.entity_type = EntityType.ORGANIZATION
            del mock_entity.workspace_id

            mock_map.return_value = ([mock_entity], [], [], [], {"cid_1": "core_1"})
            mock_pre.return_value = None

            from aurora.persistence.source_graph import SourceGraphError
            mock_cu.side_effect = SourceGraphError("ContentUnit not found")
            mock_fail.return_value = True

            from aurora.persistence.persistence_policy import PersistencePolicy
            policy = PersistencePolicy(
                allowed_providers=frozenset({"fixture"}),
                allowed_profiles=frozenset({"v1_adversarial"}),
                workspace_id="ws_test",
            )

            tx = persist_drafts(mock_sessionmaker, bundle, workspace_id="ws_test", policy=policy)
            assert not tx.succeeded
            assert "SourceGraphError" in tx.error_message
            mock_fail.assert_called_once()

    def test_source_graph_outer_exception_handler(self):
        from unittest.mock import MagicMock, patch
        from aurora.persistence.draft_service import persist_drafts

        bundle = _make_mock_bundle()
        bundle.candidates = (MagicMock(),)
        bundle.candidates[0].source_unit_id = "cu_1"
        bundle.accepted_candidate_ids = ("cid_1",)

        mock_sessionmaker = MagicMock()
        mock_session = MagicMock()
        mock_sessionmaker.return_value.__enter__.return_value = mock_session
        mock_session.scalars.return_value.all.return_value = []

        with patch("aurora.persistence.draft_service.validate_bundle_preflight") as mock_pre, \
             patch("aurora.persistence.draft_service.map_accepted_candidates") as mock_map, \
             patch("aurora.persistence.draft_service.compute_independence_group") as mock_cu, \
             patch("aurora.persistence.draft_service._finalize_failed_run") as mock_fail:
            from aurora.core.models.enums import EntityType

            mock_entity = MagicMock()
            mock_entity.source_ref = "candidate:cid_1"
            mock_entity.id = "e1"
            mock_entity.object_type = "entity"
            mock_entity.schema_version = "1.1"
            mock_entity.created_by = "test"
            mock_entity.canonical_name = "Test Entity"
            mock_entity.entity_type = EntityType.ORGANIZATION
            del mock_entity.workspace_id

            mock_map.return_value = ([mock_entity], [], [], [], {"cid_1": "core_1"})
            mock_pre.return_value = None
            mock_cu.side_effect = RuntimeError("DB connection lost")
            mock_fail.return_value = True

            from aurora.persistence.persistence_policy import PersistencePolicy
            policy = PersistencePolicy(
                allowed_providers=frozenset({"fixture"}),
                allowed_profiles=frozenset({"v1_adversarial"}),
                workspace_id="ws_test",
            )

            tx = persist_drafts(mock_sessionmaker, bundle, workspace_id="ws_test", policy=policy)
            assert not tx.succeeded
            assert "Source graph resolution failed" in tx.error_message
            mock_fail.assert_called_once()


class TestPhase1FailureHandler:
    def test_phase1_write_failure(self):
        from unittest.mock import MagicMock, patch
        from aurora.persistence.draft_service import persist_drafts

        bundle = _make_mock_bundle()

        mock_sessionmaker = MagicMock()
        mock_session = MagicMock()
        mock_sessionmaker.return_value.__enter__.return_value = mock_session
        mock_session.scalars.return_value.all.return_value = []

        mock_session.commit.side_effect = RuntimeError("DB connection lost")

        with patch("aurora.persistence.draft_service.validate_bundle_preflight"):
            from aurora.persistence.persistence_policy import PersistencePolicy
            policy = PersistencePolicy(
                allowed_providers=frozenset({"fixture"}),
                allowed_profiles=frozenset({"v1_adversarial"}),
                workspace_id="ws_test",
            )
            tx = persist_drafts(mock_sessionmaker, bundle, workspace_id="ws_test", policy=policy)
            assert not tx.succeeded
            assert "Failed to create ProcessingRun" in tx.error_message


class TestPreflightFailureHandler:
    def test_preflight_failure_caught(self):
        from unittest.mock import MagicMock, patch
        from aurora.persistence.draft_service import persist_drafts

        bundle = _make_mock_bundle()

        mock_sessionmaker = MagicMock()
        mock_session = MagicMock()
        mock_sessionmaker.return_value.__enter__.return_value = mock_session
        mock_session.scalars.return_value.all.return_value = []

        with patch("aurora.persistence.draft_service.validate_bundle_preflight") as mock_pre, \
             patch("aurora.persistence.draft_service._finalize_failed_run") as mock_fail:
            mock_pre.side_effect = ValueError("Invalid content unit window")
            mock_fail.return_value = True

            from aurora.persistence.persistence_policy import PersistencePolicy
            policy = PersistencePolicy(
                allowed_providers=frozenset({"fixture"}),
                allowed_profiles=frozenset({"v1_adversarial"}),
                workspace_id="ws_test",
            )
            tx = persist_drafts(mock_sessionmaker, bundle, workspace_id="ws_test", policy=policy)
            assert not tx.succeeded
            assert "Preflight failed" in tx.error_message
            mock_fail.assert_called_once()


class TestMapperFailureHandler:
    def test_mapper_failure_caught(self):
        from unittest.mock import MagicMock, patch
        from aurora.persistence.draft_service import persist_drafts

        bundle = _make_mock_bundle()
        bundle.accepted_candidate_ids = ("cid_1",)

        mock_sessionmaker = MagicMock()
        mock_session = MagicMock()
        mock_sessionmaker.return_value.__enter__.return_value = mock_session
        mock_session.scalars.return_value.all.return_value = []

        with patch("aurora.persistence.draft_service.validate_bundle_preflight") as mock_pre, \
             patch("aurora.persistence.draft_service.map_accepted_candidates") as mock_map, \
             patch("aurora.persistence.draft_service._finalize_failed_run") as mock_fail:
            mock_pre.return_value = None
            mock_map.side_effect = ValueError("Missing required field")
            mock_fail.return_value = True

            from aurora.persistence.persistence_policy import PersistencePolicy
            policy = PersistencePolicy(
                allowed_providers=frozenset({"fixture"}),
                allowed_profiles=frozenset({"v1_adversarial"}),
                workspace_id="ws_test",
            )
            tx = persist_drafts(mock_sessionmaker, bundle, workspace_id="ws_test", policy=policy)
            assert not tx.succeeded
            assert "Mapper failed" in tx.error_message
            mock_fail.assert_called_once()


class TestPhase2WriteException:
    def test_phase2_exception_caught(self):
        from unittest.mock import MagicMock, patch
        from aurora.persistence.draft_service import persist_drafts

        bundle = _make_mock_bundle()
        bundle.candidates = (MagicMock(),)
        bundle.candidates[0].source_unit_id = "cu_1"
        bundle.candidates[0].candidate_id = "cid_1"
        bundle.accepted_candidate_ids = ("cid_1",)

        mock_sessionmaker = MagicMock()
        mock_session = MagicMock()
        mock_sessionmaker.return_value.__enter__.return_value = mock_session
        mock_session.scalars.return_value.all.return_value = []

        with patch("aurora.persistence.draft_service.validate_bundle_preflight") as mock_pre, \
             patch("aurora.persistence.draft_service.map_accepted_candidates") as mock_map, \
             patch("aurora.persistence.draft_service.compute_independence_group") as mock_cu, \
             patch("aurora.persistence.draft_service._finalize_failed_run") as mock_fail:
            from aurora.core.models.enums import EntityType

            mock_entity = MagicMock()
            mock_entity.source_ref = "candidate:cid_1"
            mock_entity.id = "e1"
            mock_entity.object_type = "entity"
            mock_entity.schema_version = "1.1"
            mock_entity.created_by = "test"
            mock_entity.canonical_name = "Test Entity"
            mock_entity.entity_type = EntityType.ORGANIZATION
            mock_entity.model_dump.return_value = {"id": "e1"}
            del mock_entity.workspace_id

            mock_map.return_value = ([mock_entity], [], [], [], {"cid_1": "core_1"})
            mock_pre.return_value = None
            mock_cu.return_value = "grp_1"
            mock_fail.return_value = True

            mock_session.add.side_effect = [None, RuntimeError("Row update error")]

            from aurora.persistence.persistence_policy import PersistencePolicy
            policy = PersistencePolicy(
                allowed_providers=frozenset({"fixture"}),
                allowed_profiles=frozenset({"v1_adversarial"}),
                workspace_id="ws_test",
            )
            tx = persist_drafts(mock_sessionmaker, bundle, workspace_id="ws_test", policy=policy)
            assert not tx.succeeded
            mock_fail.assert_called_once()


class TestPhase3AuditFailure:
    def test_phase3_audit_failure(self):
        from unittest.mock import MagicMock, patch
        from aurora.persistence.draft_service import persist_drafts

        bundle = _make_mock_bundle()
        bundle.candidates = (MagicMock(),)
        bundle.candidates[0].source_unit_id = "cu_1"
        bundle.candidates[0].candidate_id = "cid_1"
        bundle.accepted_candidate_ids = ("cid_1",)

        mock_sessionmaker = MagicMock()
        mock_session = MagicMock()
        mock_sessionmaker.return_value.__enter__.return_value = mock_session
        mock_session.scalars.return_value.all.return_value = []

        with patch("aurora.persistence.draft_service.validate_bundle_preflight") as mock_pre, \
             patch("aurora.persistence.draft_service.map_accepted_candidates") as mock_map, \
             patch("aurora.persistence.draft_service.compute_independence_group") as mock_cu, \
             patch("aurora.persistence.draft_service._finalize_success_run") as mock_succ, \
             patch("aurora.persistence.draft_service._finalize_failed_run") as mock_fail, \
             patch("aurora.persistence.draft_service.compute_draft_natural_key") as mock_nk:
            from aurora.core.models.enums import EntityType

            mock_entity = MagicMock()
            mock_entity.source_ref = "candidate:cid_1"
            mock_entity.id = "e1"
            mock_entity.object_type = "entity"
            mock_entity.schema_version = "1.1"
            mock_entity.created_by = "test"
            mock_entity.canonical_name = "Test Entity"
            mock_entity.entity_type = EntityType.ORGANIZATION
            mock_entity.model_dump.return_value = {"id": "e1"}
            del mock_entity.workspace_id

            mock_map.return_value = ([mock_entity], [], [], [], {"cid_1": "core_1"})
            mock_pre.return_value = None
            mock_cu.return_value = "grp_1"
            mock_succ.return_value = False
            mock_fail.return_value = True
            mock_nk.return_value = "a" * 64

            from aurora.persistence.persistence_policy import PersistencePolicy
            policy = PersistencePolicy(
                allowed_providers=frozenset({"fixture"}),
                allowed_profiles=frozenset({"v1_adversarial"}),
                workspace_id="ws_test",
            )
            tx = persist_drafts(mock_sessionmaker, bundle, workspace_id="ws_test", policy=policy)
            assert not tx.succeeded
            assert "Phase 3 audit update failed" in tx.error_message
            mock_succ.assert_called_once()
            assert mock_fail.call_count >= 1


class TestDryRunElsePath:
    def test_dry_run_candidate_not_found(self):
        from unittest.mock import MagicMock, patch
        from aurora.persistence.draft_service import persist_drafts

        bundle = _make_mock_bundle()
        bundle.accepted_candidate_ids = ("cid_1",)

        mock_sessionmaker = MagicMock()

        with patch("aurora.persistence.draft_service.validate_bundle_preflight") as mock_pre, \
             patch("aurora.persistence.draft_service.map_accepted_candidates") as mock_map:
            from aurora.core.models.enums import EntityType

            mock_entity = MagicMock()
            mock_entity.source_ref = "candidate:unknown_cid"
            mock_entity.id = "e1"
            mock_entity.object_type = "entity"
            mock_entity.schema_version = "1.1"
            mock_entity.created_by = "test"
            mock_entity.canonical_name = "Test Entity"
            mock_entity.entity_type = EntityType.ORGANIZATION
            del mock_entity.workspace_id

            mock_map.return_value = ([mock_entity], [], [], [], {"cid_1": "core_1"})
            mock_pre.return_value = None

            from aurora.persistence.persistence_policy import PersistencePolicy
            policy = PersistencePolicy(
                allowed_providers=frozenset({"fixture"}),
                allowed_profiles=frozenset({"v1_adversarial"}),
                workspace_id="ws_test",
            )
            tx = persist_drafts(mock_sessionmaker, bundle, workspace_id="ws_test", dry_run=True, policy=policy)
            assert tx.succeeded
            assert tx.created_count > 0
