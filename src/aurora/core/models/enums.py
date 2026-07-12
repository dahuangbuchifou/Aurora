"""Aurora V1.1 core enumerations."""

from enum import StrEnum


class ObjectType(StrEnum):
    SOURCE = "source"
    DOCUMENT = "document"
    CONTENT_UNIT = "content_unit"
    ENTITY = "entity"
    EVENT = "event"
    DATA_POINT = "data_point"
    CLAIM = "claim"
    EVIDENCE = "evidence"
    FACT = "fact"
    KNOWLEDGE_OBJECT = "knowledge_object"
    RELATION = "relation"
    TIMELINE_ENTRY = "timeline_entry"
    INSIGHT = "insight"
    PERSONAL_OPINION = "personal_opinion"
    OUTPUT_ARTIFACT = "output_artifact"
    FEEDBACK = "feedback"
    PROCESSING_RUN = "processing_run"


class LifecycleStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"
    DELETED = "deleted"


class PrivacyLevel(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


class OriginType(StrEnum):
    ORIGINAL = "original"
    IMPORTED = "imported"
    DERIVED = "derived"
    USER_CREATED = "user_created"


class DerivationRelationType(StrEnum):
    DERIVED_FROM = "derived_from"
    QUOTED_FROM = "quoted_from"
    SUMMARIZES = "summarizes"
    REPOSTS = "reposts"
    CALCULATED_FROM = "calculated_from"
    TRANSLATED_FROM = "translated_from"
    EXTRACTED_FROM = "extracted_from"
    INFERRED_FROM = "inferred_from"


class SourceType(StrEnum):
    OFFICIAL_WEBSITE = "official_website"
    COMPANY_ANNOUNCEMENT = "company_announcement"
    GOVERNMENT_DATABASE = "government_database"
    ACADEMIC_JOURNAL = "academic_journal"
    RESEARCH_INSTITUTION = "research_institution"
    NEWS_MEDIA = "news_media"
    VIDEO_CHANNEL = "video_channel"
    PODCAST = "podcast"
    SOCIAL_MEDIA = "social_media"
    BLOG = "blog"
    API = "api"
    LOCAL_FILE = "local_file"
    USER_NOTE = "user_note"
    UNKNOWN = "unknown"


class SourceQualityTier(StrEnum):
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"
    S4 = "S4"
    S5 = "S5"


class DocumentType(StrEnum):
    WEB_ARTICLE = "web_article"
    NEWS = "news"
    PDF = "pdf"
    VIDEO = "video"
    AUDIO = "audio"
    MARKDOWN = "markdown"
    TEXT = "text"
    SPREADSHEET = "spreadsheet"
    COMPANY_FILING = "company_filing"
    RESEARCH_REPORT = "research_report"
    USER_NOTE = "user_note"
    UNKNOWN = "unknown"


class ParseStatus(StrEnum):
    DISCOVERED = "discovered"
    QUEUED = "queued"
    COLLECTED = "collected"
    PARSED = "parsed"
    PARTIALLY_PARSED = "partially_parsed"
    FAILED = "failed"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class ContentUnitType(StrEnum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TRANSCRIPT_SEGMENT = "transcript_segment"
    TABLE = "table"
    TABLE_ROW = "table_row"
    LIST_ITEM = "list_item"
    QUOTE = "quote"
    CODE_BLOCK = "code_block"
    NOTE_BLOCK = "note_block"
    UNKNOWN = "unknown"


class QualityLevel(StrEnum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class HumanReviewStatus(StrEnum):
    NOT_REVIEWED = "not_reviewed"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class EntityType(StrEnum):
    PERSON = "person"
    COMPANY = "company"
    ORGANIZATION = "organization"
    INDUSTRY = "industry"
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    POLICY = "policy"
    LOCATION = "location"
    SECURITY = "security"
    PAPER = "paper"
    PROJECT = "project"
    CONCEPT = "concept"
    UNKNOWN = "unknown"


class EventStatus(StrEnum):
    REPORTED = "reported"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    SUPERSEDED = "superseded"


class TimePrecision(StrEnum):
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    UNKNOWN = "unknown"


class CalculationMethod(StrEnum):
    REPORTED = "reported"
    CALCULATED = "calculated"
    ESTIMATED = "estimated"
    DERIVED = "derived"
    UNKNOWN = "unknown"


class MeasurementKind(StrEnum):
    UNKNOWN = "unknown"
    MONETARY = "monetary"
    RATIO = "ratio"
    PERCENTAGE = "percentage"
    COUNT = "count"
    PHYSICAL = "physical"
    INDEX = "index"
    RATE = "rate"
    OTHER = "other"


class ClaimType(StrEnum):
    FACT_CLAIM = "fact_claim"
    INTERPRETATION = "interpretation"
    CAUSAL_CLAIM = "causal_claim"
    PREDICTION = "prediction"
    RECOMMENDATION = "recommendation"
    RISK_CLAIM = "risk_claim"
    VALUE_JUDGMENT = "value_judgment"
    HYPOTHESIS = "hypothesis"


class ClaimDimension(StrEnum):
    GENERAL = "general"
    BUSINESS_GROWTH = "business_growth"
    FINANCIAL_PERFORMANCE = "financial_performance"
    VALUATION = "valuation"
    RISK = "risk"
    MARKET_EXPECTATION = "market_expectation"
    ACTION_RECOMMENDATION = "action_recommendation"
    POLICY = "policy"
    TECHNOLOGY = "technology"
    OPERATIONS = "operations"
    GOVERNANCE = "governance"
    SUPPLY_CHAIN = "supply_chain"
    COMPETITION = "competition"
    OTHER = "other"


class EpistemicStatus(StrEnum):
    ASSERTED = "asserted"
    UNDER_REVIEW = "under_review"
    SUPPORTED = "supported"
    DISPUTED = "disputed"
    VERIFIED = "verified"
    FALSIFIED = "falsified"
    OUTDATED = "outdated"
    WITHDRAWN = "withdrawn"


class EvidenceRole(StrEnum):
    SUPPORT = "support"
    REFUTE = "refute"
    QUALIFY = "qualify"
    CONTEXT = "context"
    COUNTEREXAMPLE = "counterexample"


class EvidenceType(StrEnum):
    DIRECT_QUOTE = "direct_quote"
    OFFICIAL_DATA = "official_data"
    COMPANY_FILING = "company_filing"
    RESEARCH_RESULT = "research_result"
    OBSERVED_EVENT = "observed_event"
    EXPERT_TESTIMONY = "expert_testimony"
    HISTORICAL_CASE = "historical_case"
    DERIVED_CALCULATION = "derived_calculation"
    USER_OBSERVATION = "user_observation"
    UNKNOWN = "unknown"


class EvidenceDirectness(StrEnum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    CIRCUMSTANTIAL = "circumstantial"
    UNKNOWN = "unknown"


class EvidenceStrength(StrEnum):
    E0 = "E0"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"
    E5 = "E5"


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    PARTIALLY_VERIFIED = "partially_verified"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    FALSIFIED = "falsified"
    OUTDATED = "outdated"


class KnowledgeType(StrEnum):
    TOPIC_CARD = "topic_card"
    COMPANY_PROFILE = "company_profile"
    PERSON_PROFILE = "person_profile"
    INDUSTRY_CARD = "industry_card"
    TECHNOLOGY_CARD = "technology_card"
    POLICY_CARD = "policy_card"
    EVENT_SUMMARY = "event_summary"
    CONCEPT_DEFINITION = "concept_definition"
    ARGUMENT_MAP = "argument_map"
    RISK_CARD = "risk_card"
    CASE_STUDY = "case_study"


class KnowledgeStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    CHALLENGED = "challenged"
    REVISED = "revised"
    INVALIDATED = "invalidated"
    ARCHIVED = "archived"


class RelationStatus(StrEnum):
    ASSERTED = "asserted"
    HYPOTHESIZED = "hypothesized"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    INVALIDATED = "invalidated"


class InsightStatus(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    SUPPORTED = "supported"
    CHALLENGED = "challenged"
    REVISED = "revised"
    INVALIDATED = "invalidated"
    ARCHIVED = "archived"


class OpinionStatus(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    ACTIVE = "active"
    WATCH = "watch"
    CHALLENGED = "challenged"
    REVISED = "revised"
    INVALIDATED = "invalidated"
    ARCHIVED = "archived"


class OutputType(StrEnum):
    RESEARCH_BRIEF = "research_brief"
    RESEARCH_REPORT = "research_report"
    OPINION_MATRIX = "opinion_matrix"
    TIMELINE = "timeline"
    RISK_LIST = "risk_list"
    COMPANY_PROFILE = "company_profile"
    INDUSTRY_PROFILE = "industry_profile"
    DECISION_MEMO = "decision_memo"
    LEARNING_CARD = "learning_card"
    WQRS_INPUT = "wqrs_input"
    MARKDOWN_REPORT = "markdown_report"
    OTHER = "other"


class OutputReviewStatus(StrEnum):
    NOT_REVIEWED = "not_reviewed"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


class FeedbackType(StrEnum):
    USER_RATING = "user_rating"
    CORRECTION = "correction"
    NEW_EVIDENCE = "new_evidence"
    PREDICTION_OUTCOME = "prediction_outcome"
    APPLICATION_RESULT = "application_result"
    DUPLICATE_REPORT = "duplicate_report"
    STALENESS_REPORT = "staleness_report"
    QUALITY_ISSUE = "quality_issue"


class FeedbackEffect(StrEnum):
    SUPPORT = "support"
    CHALLENGE = "challenge"
    CORRECT = "correct"
    INVALIDATE = "invalidate"
    NO_CHANGE = "no_change"


class FeedbackAction(StrEnum):
    REVIEW_REQUIRED = "review_required"
    REVISION_REQUIRED = "revision_required"
    INVALIDATE_CANDIDATE = "invalidate_candidate"
    NO_CHANGE = "no_change"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"
