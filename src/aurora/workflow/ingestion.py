"""M2-001 deterministic offline ingestion workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping, cast

from sqlalchemy.orm import Session, sessionmaker

from aurora.collector import LocalFileCollector
from aurora.core.models import ContentUnit, Document, ProcessingRun, Source
from aurora.core.models.common import (
    DerivationLink,
    ProcessorInfo,
    Provenance,
    utc_now,
)
from aurora.core.models.enums import (
    DerivationRelationType,
    DocumentType,
    ObjectType,
    OriginType,
    ParseStatus,
    RunStatus,
    SourceType,
)
from aurora.ingestion.contracts import (
    DuplicateStrategy,
    IngestionInputType,
    IngestionRequest,
    IngestionResult,
    ParserDescriptor,
)
from aurora.ingestion.errors import (
    DuplicateIngestionError,
    IngestionError,
    PersistenceIngestionError,
    UnsupportedInputError,
)
from aurora.ingestion.hashing import content_hash_for_text
from aurora.ingestion.identity import (
    canonical_source_key,
    content_unit_object_id,
    document_dedupe_key,
    document_object_id,
    document_series_key,
    source_object_id,
)
from aurora.ingestion.limits import resolve_max_bytes
from aurora.parser import (
    MarkdownParser,
    ParsedDocument,
    Parser,
    PlainTextParser,
    StructuredSegmentsParser,
)
from aurora.repository import ObjectRepository

_SOURCE_KEY = "canonical_source_key"
_DEDUPE_KEY = "ingestion_dedupe_key"
_SERIES_KEY = "ingestion_series_key"
_VERSION_KEY = "ingestion_version"
_PARSER_NAME_KEY = "parser_name"
_PARSER_VERSION_KEY = "parser_version"
_EXPLICIT_IDEMPOTENCY_KEY = "explicit_idempotency_key"


@dataclass(frozen=True)
class _ResolvedMetadata:
    workspace_id: str
    source_name: str
    source_type: SourceType
    source_key: str | None
    source_homepage_url: str | None
    title: str
    document_type: DocumentType
    published_at: datetime | None
    language: str
    tags: list[str]
    idempotency_key: str | None
    mime_type: str
    created_by: str


@dataclass(frozen=True)
class _DocumentPlan:
    document: Document
    content_units: tuple[ContentUnit, ...]
    reused: bool
    warnings: tuple[str, ...]


class IngestionService:
    """Run a complete local ingestion with auditable transaction boundaries."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        collector: LocalFileCollector | None = None,
        parsers: Mapping[IngestionInputType, Parser] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.collector = collector or LocalFileCollector()
        self.parsers: dict[IngestionInputType, Parser] = dict(
            parsers
            or {
                IngestionInputType.MARKDOWN: MarkdownParser(),
                IngestionInputType.TEXT: PlainTextParser(),
                IngestionInputType.STRUCTURED_SEGMENTS: StructuredSegmentsParser(),
            }
        )

    def ingest(self, request: IngestionRequest) -> IngestionResult:
        parser = self._parser_for(request.input_type)
        if request.dry_run:
            return self._ingest_dry_run(request, parser)

        run = self._create_run(request, parser)
        try:
            self._transition_run(run.id, RunStatus.RUNNING)
            collected = self.collector.collect(
                request.path,
                max_bytes=resolve_max_bytes(request.max_bytes),
            )
            parsed = parser.parse(collected)
            metadata = self._resolve_metadata(request, parsed, collected.path)
            self._align_run_workspace(run.id, metadata.workspace_id)
            source, source_warnings = self._get_or_create_source(
                metadata=metadata,
                processing_run_id=run.id,
            )
            plan = self._persist_or_reuse_document(
                request=request,
                metadata=metadata,
                parsed=parsed,
                input_uri=collected.input_uri,
                source=source,
                processing_run_id=run.id,
            )
            output_ids = [source.id, plan.document.id]
            output_ids.extend(unit.id for unit in plan.content_units)
            self._transition_run(
                run.id,
                RunStatus.SUCCESS,
                output_object_ids=output_ids,
            )
            return self._result(
                run_id=run.id,
                source=source,
                plan=plan,
                parsed=parsed,
                dry_run=False,
                warnings=[*source_warnings, *plan.warnings],
            )
        except IngestionError as exc:
            self._mark_run_failed(run.id, exc)
            raise
        except Exception as exc:
            wrapped = PersistenceIngestionError(
                "unexpected ingestion failure",
                context={"exception_type": type(exc).__name__},
            )
            self._mark_run_failed(run.id, wrapped)
            raise wrapped from exc

    def _ingest_dry_run(
        self,
        request: IngestionRequest,
        parser: Parser,
    ) -> IngestionResult:
        collected = self.collector.collect(
            request.path,
            max_bytes=resolve_max_bytes(request.max_bytes),
        )
        parsed = parser.parse(collected)
        metadata = self._resolve_metadata(request, parsed, collected.path)
        dry_run_time = utc_now()
        run = ProcessingRun(
            task_type="offline_ingestion_dry_run",
            processor=ProcessorInfo(
                module=f"aurora.parser.{parsed.parser.name}",
                code_version=parsed.parser.version,
            ),
            run_status=RunStatus.SUCCESS,
            started_at=dry_run_time,
            finished_at=dry_run_time,
            created_by=request.created_by,
            workspace_id=metadata.workspace_id,
            metadata={"dry_run": True, "input_type": request.input_type.value},
        )
        source, source_warnings = self._plan_source(metadata, run.id)
        plan = self._plan_document(
            request=request,
            metadata=metadata,
            parsed=parsed,
            input_uri=collected.input_uri,
            source=source,
            processing_run_id=run.id,
            persist=False,
        )
        return self._result(
            run_id=run.id,
            source=source,
            plan=plan,
            parsed=parsed,
            dry_run=True,
            warnings=[*source_warnings, *plan.warnings],
        )

    def _parser_for(self, input_type: IngestionInputType) -> Parser:
        parser = self.parsers.get(input_type)
        if parser is None:
            raise UnsupportedInputError(
                f"no parser registered for input type: {input_type.value}"
            )
        return parser

    def _resolve_metadata(
        self,
        request: IngestionRequest,
        parsed: ParsedDocument,
        path: Path,
    ) -> _ResolvedMetadata:
        manifest = parsed.structured_manifest
        if manifest is not None:
            workspace_id = request.workspace_id or manifest.workspace_id
            source_name = request.source_name or manifest.source.name
            source_type = request.source_type or manifest.source.source_type
            source_key = request.source_key or manifest.source.canonical_key
            homepage = request.source_homepage_url or manifest.source.homepage_url
            title = request.title or manifest.document.title
            document_type = request.document_type or manifest.document.document_type
            published_at = request.published_at or manifest.document.published_at
            language = request.language or manifest.document.language
            tags = list(dict.fromkeys([*manifest.document.tags, *request.tags]))
            idempotency_key = (
                request.idempotency_key or manifest.document.idempotency_key
            )
            mime_type = "application/vnd.aurora.segments+json"
        else:
            if not request.source_name or request.source_type is None:
                raise UnsupportedInputError(
                    "source_name and source_type are required for this input"
                )
            workspace_id = request.workspace_id or "default"
            source_name = request.source_name
            source_type = request.source_type
            source_key = request.source_key
            homepage = request.source_homepage_url
            title = request.title or parsed.inferred_title or path.stem
            document_type = request.document_type or (
                DocumentType.MARKDOWN
                if request.input_type == IngestionInputType.MARKDOWN
                else DocumentType.TEXT
            )
            published_at = request.published_at
            language = request.language or "zh-CN"
            tags = list(dict.fromkeys(request.tags))
            idempotency_key = request.idempotency_key
            mime_type = (
                "text/markdown"
                if request.input_type == IngestionInputType.MARKDOWN
                else "text/plain"
            )

        if not source_name:
            raise UnsupportedInputError("resolved source name is empty")
        if not title:
            raise UnsupportedInputError("resolved document title is empty")

        return _ResolvedMetadata(
            workspace_id=workspace_id,
            source_name=source_name,
            source_type=source_type,
            source_key=source_key,
            source_homepage_url=str(homepage) if homepage else None,
            title=title,
            document_type=document_type,
            published_at=published_at,
            language=language,
            tags=tags,
            idempotency_key=idempotency_key,
            mime_type=mime_type,
            created_by=request.created_by,
        )

    def _create_run(
        self,
        request: IngestionRequest,
        parser: Parser,
    ) -> ProcessingRun:
        workspace_id = request.workspace_id or "default"
        run = ProcessingRun(
            task_type="offline_ingestion",
            processor=ProcessorInfo(
                module=f"aurora.parser.{parser.name}",
                code_version=parser.version,
            ),
            run_status=RunStatus.PENDING,
            created_by=request.created_by,
            workspace_id=workspace_id,
            metadata={
                "input_type": request.input_type.value,
                "input_name": request.path.name,
            },
        )
        session = self.session_factory()
        try:
            ObjectRepository(session).create(run)
            session.commit()
            return run
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _transition_run(
        self,
        run_id: str,
        status: RunStatus,
        *,
        output_object_ids: list[str] | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> ProcessingRun:
        session = self.session_factory()
        try:
            repository = ObjectRepository(session)
            current = cast(ProcessingRun, repository.get_required(run_id))
            payload = current.model_dump(mode="python")
            payload["run_status"] = status
            if output_object_ids is not None:
                payload["output_object_ids"] = output_object_ids
            if status in {
                RunStatus.SUCCESS,
                RunStatus.PARTIAL_SUCCESS,
                RunStatus.FAILED,
                RunStatus.CANCELLED,
            }:
                payload["finished_at"] = utc_now()
            else:
                payload["finished_at"] = None
            payload["error_code"] = error_code
            payload["error_message"] = error_message
            updated = ProcessingRun.model_validate(payload)
            result = cast(ProcessingRun, repository.update(updated))
            session.commit()
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _align_run_workspace(self, run_id: str, workspace_id: str) -> None:
        session = self.session_factory()
        try:
            repository = ObjectRepository(session)
            current = cast(ProcessingRun, repository.get_required(run_id))
            if current.workspace_id == workspace_id:
                return
            payload = current.model_dump(mode="python")
            payload["workspace_id"] = workspace_id
            repository.update(ProcessingRun.model_validate(payload))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _mark_run_failed(self, run_id: str, error: IngestionError) -> None:
        try:
            self._transition_run(
                run_id,
                RunStatus.FAILED,
                error_code=error.code,
                error_message=error.message,
            )
        except Exception:
            # Do not hide the original ingestion error if audit persistence fails.
            pass

    def _plan_source(
        self,
        metadata: _ResolvedMetadata,
        processing_run_id: str,
    ) -> tuple[Source, list[str]]:
        canonical_key = canonical_source_key(
            source_name=metadata.source_name,
            source_type=metadata.source_type,
            explicit_key=metadata.source_key,
            homepage_url=metadata.source_homepage_url,
        )
        session = self.session_factory()
        try:
            repository = ObjectRepository(session)
            matches = [
                cast(Source, candidate)
                for candidate in repository.find_by_external_id(
                    object_type=ObjectType.SOURCE,
                    key=_SOURCE_KEY,
                    value=canonical_key,
                    workspace_id=metadata.workspace_id,
                )
                if isinstance(candidate, Source)
                and candidate.source_type == metadata.source_type
            ]
            if len(matches) > 1:
                raise PersistenceIngestionError(
                    "multiple sources share the same canonical source key",
                    context={"canonical_source_key": canonical_key},
                )
            if matches:
                source = cast(Source, matches[0])
                warnings = []
                if source.name != metadata.source_name:
                    warnings.append(
                        "existing source reused with a different display name"
                    )
                return source, warnings
        finally:
            session.close()

        now = utc_now()
        source = Source(
            id=source_object_id(
                workspace_id=metadata.workspace_id,
                source_type=metadata.source_type,
                canonical_key=canonical_key,
            ),
            name=metadata.source_name,
            source_type=metadata.source_type,
            homepage_url=metadata.source_homepage_url,
            first_seen_at=now,
            last_seen_at=now,
            workspace_id=metadata.workspace_id,
            language=metadata.language,
            tags=metadata.tags,
            created_by=metadata.created_by,
            external_ids={_SOURCE_KEY: canonical_key},
            provenance=Provenance(
                origin_type=OriginType.IMPORTED,
                processing_run_id=processing_run_id,
            ),
        )
        return source, []

    def _get_or_create_source(
        self,
        *,
        metadata: _ResolvedMetadata,
        processing_run_id: str,
    ) -> tuple[Source, list[str]]:
        planned, warnings = self._plan_source(metadata, processing_run_id)
        session = self.session_factory()
        try:
            repository = ObjectRepository(session)
            existing = repository.get(planned.id)
            if existing is None:
                repository.create(planned)
                session.commit()
                return planned, warnings

            source = cast(Source, existing)
            payload = source.model_dump(mode="python")
            payload["last_seen_at"] = utc_now()
            updated = Source.model_validate(payload)
            repository.update(updated)
            session.commit()
            return updated, warnings
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _persist_or_reuse_document(
        self,
        *,
        request: IngestionRequest,
        metadata: _ResolvedMetadata,
        parsed: ParsedDocument,
        input_uri: str,
        source: Source,
        processing_run_id: str,
    ) -> _DocumentPlan:
        return self._plan_document(
            request=request,
            metadata=metadata,
            parsed=parsed,
            input_uri=input_uri,
            source=source,
            processing_run_id=processing_run_id,
            persist=True,
        )

    def _plan_document(
        self,
        *,
        request: IngestionRequest,
        metadata: _ResolvedMetadata,
        parsed: ParsedDocument,
        input_uri: str,
        source: Source,
        processing_run_id: str,
        persist: bool,
    ) -> _DocumentPlan:
        dedupe_key = document_dedupe_key(
            source_id=source.id,
            content_hash=parsed.content_hash,
            parser_name=parsed.parser.name,
            parser_version=parsed.parser.version,
        )
        series_key = document_series_key(
            source_id=source.id,
            input_uri=input_uri,
            idempotency_key=metadata.idempotency_key,
        )

        session = self.session_factory()
        try:
            repository = ObjectRepository(session)
            exact_documents = [
                cast(Document, obj)
                for obj in repository.find_by_external_id(
                    object_type=ObjectType.DOCUMENT,
                    key=_DEDUPE_KEY,
                    value=dedupe_key,
                    workspace_id=metadata.workspace_id,
                )
            ]
            exact_documents.sort(key=self._document_version)

            if exact_documents and request.duplicate_strategy != DuplicateStrategy.NEW_VERSION:
                if request.duplicate_strategy == DuplicateStrategy.REJECT:
                    raise DuplicateIngestionError(
                        "an identical document already exists",
                        context={
                            "document_id": exact_documents[-1].id,
                            "content_hash": parsed.content_hash,
                        },
                    )
                existing = exact_documents[-1]
                units = self._content_units_for_document(
                    repository,
                    existing.id,
                    metadata.workspace_id,
                )
                if not units:
                    raise PersistenceIngestionError(
                        "reused document has no content units",
                        context={"document_id": existing.id},
                    )
                return _DocumentPlan(
                    document=existing,
                    content_units=tuple(units),
                    reused=True,
                    warnings=(),
                )

            series_documents = [
                cast(Document, obj)
                for obj in repository.find_by_external_id(
                    object_type=ObjectType.DOCUMENT,
                    key=_SERIES_KEY,
                    value=series_key,
                    workspace_id=metadata.workspace_id,
                )
            ]
            series_documents.sort(key=self._document_version)
            version_no = (
                self._document_version(series_documents[-1]) + 1
                if series_documents
                else 1
            )
            parent_id = series_documents[-1].id if series_documents else None
            document_id = document_object_id(
                dedupe_key=dedupe_key,
                series_key=series_key,
                version_no=version_no,
            )
            external_ids = {
                _DEDUPE_KEY: dedupe_key,
                _SERIES_KEY: series_key,
                _VERSION_KEY: str(version_no),
                _PARSER_NAME_KEY: parsed.parser.name,
                _PARSER_VERSION_KEY: parsed.parser.version,
            }
            if metadata.idempotency_key:
                external_ids[_EXPLICIT_IDEMPOTENCY_KEY] = metadata.idempotency_key

            document = Document(
                id=document_id,
                source_id=source.id,
                document_type=metadata.document_type,
                title=metadata.title,
                published_at=metadata.published_at,
                content_hash=parsed.content_hash,
                normalized_url=input_uri,
                mime_type=metadata.mime_type,
                raw_storage_uri=input_uri,
                parse_status=ParseStatus.PARSED,
                parent_document_id=parent_id,
                workspace_id=metadata.workspace_id,
                language=metadata.language,
                tags=metadata.tags,
                source_refs=[source.id],
                created_by=request.created_by,
                external_ids=external_ids,
                provenance=Provenance(
                    origin_type=OriginType.IMPORTED,
                    processing_run_id=processing_run_id,
                ),
            )
            content_units = tuple(
                self._build_content_unit(
                    parsed_unit=parsed_unit,
                    document=document,
                    source=source,
                    processing_run_id=processing_run_id,
                    created_by=request.created_by,
                )
                for parsed_unit in parsed.units
            )

            if persist:
                repository.create(document)
                for unit in content_units:
                    repository.create(unit)
                session.commit()
            return _DocumentPlan(
                document=document,
                content_units=content_units,
                reused=False,
                warnings=(),
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _document_version(document: Document) -> int:
        raw = document.external_ids.get(_VERSION_KEY, "1")
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _content_units_for_document(
        repository: ObjectRepository,
        document_id: str,
        workspace_id: str,
    ) -> list[ContentUnit]:
        units = [
            cast(ContentUnit, obj)
            for obj in repository.find_by_payload_field(
                object_type=ObjectType.CONTENT_UNIT,
                field_name="document_id",
                value=document_id,
                workspace_id=workspace_id,
            )
        ]
        units.sort(key=lambda unit: (unit.sequence_no, unit.id))
        return units

    @staticmethod
    def _build_content_unit(
        *,
        parsed_unit,
        document: Document,
        source: Source,
        processing_run_id: str,
        created_by: str,
    ) -> ContentUnit:
        unit_hash = content_hash_for_text(parsed_unit.text)
        return ContentUnit(
            id=content_unit_object_id(
                document_id=document.id,
                unit_type=parsed_unit.unit_type,
                sequence_no=parsed_unit.sequence_no,
                normalized_text_hash=unit_hash,
            ),
            document_id=document.id,
            unit_type=parsed_unit.unit_type,
            sequence_no=parsed_unit.sequence_no,
            text=parsed_unit.text,
            locator=parsed_unit.locator,
            speaker=parsed_unit.speaker,
            workspace_id=document.workspace_id,
            language=document.language,
            tags=document.tags,
            source_refs=[source.id, document.id],
            created_by=created_by,
            external_ids={"normalized_text_hash": unit_hash},
            provenance=Provenance(
                origin_type=OriginType.DERIVED,
                origin_object_ids=[document.id],
                derivation_links=[
                    DerivationLink(
                        object_id=document.id,
                        relation_type=DerivationRelationType.EXTRACTED_FROM,
                    )
                ],
                processing_run_id=processing_run_id,
            ),
        )

    @staticmethod
    def _result(
        *,
        run_id: str,
        source: Source,
        plan: _DocumentPlan,
        parsed: ParsedDocument,
        dry_run: bool,
        warnings: list[str],
    ) -> IngestionResult:
        return IngestionResult(
            processing_run_id=run_id,
            source_id=source.id,
            document_id=plan.document.id,
            content_unit_ids=[unit.id for unit in plan.content_units],
            content_unit_count=len(plan.content_units),
            content_hash=parsed.content_hash,
            idempotency_key=plan.document.external_ids[_DEDUPE_KEY],
            reused=plan.reused,
            dry_run=dry_run,
            parser=ParserDescriptor(
                name=parsed.parser.name,
                version=parsed.parser.version,
            ),
            warnings=warnings,
        )
