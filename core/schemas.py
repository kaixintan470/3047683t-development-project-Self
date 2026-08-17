"""Shared data contracts for the clinical reasoning pipeline."""

from dataclasses import dataclass, field
from enum import Enum


@dataclass
class PatientState:
    chief_complaint: str = ""
    symptoms: list[str] = field(default_factory=list)

    age: int | None = None
    gender: str = ""
    duration: str = ""

    medical_history: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)

    explicit_negations: list[str] = field(default_factory=list)

    follow_up_answers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.age is not None and (
            isinstance(self.age, bool)
            or not isinstance(self.age, int)
            or self.age < 0
        ):
            raise ValueError("age must be None or a non-negative integer")

        list_fields = (
            self.symptoms,
            self.medical_history,
            self.allergies,
            self.medications,
            self.explicit_negations,
        )
        if any(
            not isinstance(values, list)
            or any(not isinstance(value, str) for value in values)
            for values in list_fields
        ):
            raise ValueError("patient list fields must contain only strings")


@dataclass
class EvidenceChunk:
    source: str
    title: str
    chunk_id: str
    content: str
    page: int | None = None
    section: str = ""
    retrieval_score: float | None = None
    matched_query: str = ""

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("source must not be empty")
        if not self.title:
            raise ValueError("title must not be empty")
        if not self.chunk_id:
            raise ValueError("chunk_id must not be empty")
        if not self.content:
            raise ValueError("content must not be empty")
        if self.page is not None and (
            isinstance(self.page, bool)
            or not isinstance(self.page, int)
            or self.page < 0
        ):
            raise ValueError("page must be None or a non-negative integer")


@dataclass
class DiagnosisCandidate:
    name: str
    probability: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty")
        if not 0 <= self.probability <= 1:
            raise ValueError("probability must be between 0 and 1")


@dataclass
class EvidenceReference:
    source: str
    support: str

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("source must not be empty")
        if not self.support:
            raise ValueError("support must not be empty")


@dataclass
class SufficiencyResult:
    patient_fact_support: bool
    relevant_evidence_available: bool
    no_critical_missing_discriminator: bool
    no_unsupported_assumption: bool

    rationale: str
    missing_information: list[str]

    @property
    def is_sufficient(self) -> bool:
        return (
            self.patient_fact_support
            and self.relevant_evidence_available
            and self.no_critical_missing_discriminator
            and self.no_unsupported_assumption
        )

    @property
    def status(self) -> str:
        return "SUFFICIENT" if self.is_sufficient else "INSUFFICIENT"


class SLMStatus(str, Enum):
    DIAGNOSTIC_OUTPUT = "DIAGNOSTIC_OUTPUT"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


@dataclass
class SLMOutput:
    model: str
    status: SLMStatus

    diagnoses: list[DiagnosisCandidate]
    reasoning: str
    confidence: float
    evidence: list[EvidenceReference]

    sufficiency: SufficiencyResult

    def __post_init__(self) -> None:
        if not self.model:
            raise ValueError("model must not be empty")
        if not isinstance(self.status, SLMStatus):
            raise ValueError("status must be a valid SLMStatus")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.status == SLMStatus.DIAGNOSTIC_OUTPUT:
            if not self.sufficiency.is_sufficient:
                raise ValueError("diagnostic output requires sufficient information")
            if not self.diagnoses:
                raise ValueError("diagnostic output requires at least one diagnosis")
            if not self.reasoning:
                raise ValueError("diagnostic output requires reasoning")
        if (
            self.status == SLMStatus.INSUFFICIENT_INFORMATION
            and self.sufficiency.is_sufficient
        ):
            raise ValueError("insufficient output requires insufficient information")


@dataclass
class KASResult:
    score: float
    rationale: str = ""

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1")


@dataclass
class LCSResult:
    score: int
    rationale: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.score, bool) or not isinstance(self.score, int):
            raise ValueError("score must be an integer from 0 to 3")
        if self.score not in (0, 1, 2, 3):
            raise ValueError("score must be one of 0, 1, 2, or 3")


class DCSDecision(str, Enum):
    APPROVED = "APPROVED"
    FOLLOW_UP = "FOLLOW_UP"


@dataclass
class DCSResult:
    score: float
    decision: DCSDecision

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1")


class PipelineStatus(str, Enum):
    NEED_MORE_INFO = "NEED_MORE_INFO"
    APPROVED = "APPROVED"
    UNRESOLVED_INSUFFICIENT_INFORMATION = "UNRESOLVED_INSUFFICIENT_INFORMATION"


@dataclass
class PipelineResult:
    status: PipelineStatus
    patient_info: PatientState

    candidate_diagnoses: list[DiagnosisCandidate] = field(default_factory=list)
    reasoning_summary: str = ""
    supporting_evidence: list[EvidenceReference] = field(default_factory=list)

    slm_a_output: SLMOutput | None = None
    slm_b_output: SLMOutput | None = None

    kas: KASResult | None = None
    lcs: LCSResult | None = None
    dcs: DCSResult | None = None

    validation_notes: str = ""
    follow_up_rounds: int = 0

    def __post_init__(self) -> None:
        if self.follow_up_rounds < 0:
            raise ValueError("follow_up_rounds must be non-negative")
        if self.status == PipelineStatus.APPROVED:
            required_results = (
                self.slm_a_output,
                self.slm_b_output,
                self.kas,
                self.lcs,
                self.dcs,
            )
            if any(result is None for result in required_results):
                raise ValueError("approved pipeline result requires all validation results")
            if self.dcs.decision != DCSDecision.APPROVED:
                raise ValueError("approved pipeline result requires an approved DCS decision")
