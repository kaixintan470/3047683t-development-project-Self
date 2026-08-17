"""Controlled guideline manifest and local document preprocessing."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from pypdf import PdfReader

from core.config import DEFAULT_CONFIG
from core.schemas import EvidenceChunk


@dataclass(frozen=True)
class GuidelineManifestEntry:
    guideline_id: str
    organisation: str
    title: str
    year: int


GUIDELINE_MANIFEST = (
    GuidelineManifestEntry(
        "ukhsa_uti_women_under_65_2025",
        "UKHSA",
        "UTI in women under 65",
        2025,
    ),
    GuidelineManifestEntry(
        "eau_urological_infections_2026",
        "EAU",
        "Urological Infections",
        2026,
    ),
    GuidelineManifestEntry(
        "bashh_gonorrhoea_2025",
        "BASHH",
        "Gonorrhoea",
        2025,
    ),
    GuidelineManifestEntry(
        "iusti_chlamydia_2025",
        "IUSTI",
        "Chlamydia",
        2025,
    ),
    GuidelineManifestEntry(
        "bashh_pelvic_inflammatory_disease_2019",
        "BASHH",
        "Pelvic Inflammatory Disease",
        2019,
    ),
    GuidelineManifestEntry(
        "bashh_bacterial_vaginosis_2012",
        "BASHH",
        "Bacterial Vaginosis",
        2012,
    ),
    GuidelineManifestEntry(
        "bashh_vulvovaginal_candidiasis_2019",
        "BASHH",
        "Vulvovaginal Candidiasis",
        2019,
    ),
    GuidelineManifestEntry(
        "bashh_trichomonas_2021",
        "BASHH",
        "Trichomonas",
        2021,
    ),
    GuidelineManifestEntry(
        "bashh_mycoplasma_genitalium_2025",
        "BASHH",
        "Mycoplasma genitalium",
        2025,
    ),
    GuidelineManifestEntry(
        "bashh_anogenital_herpes_2024",
        "BASHH",
        "Anogenital Herpes",
        2024,
    ),
)


@dataclass(frozen=True)
class DocumentBlock:
    source: str
    title: str
    page: int | None
    text: str


@dataclass(frozen=True)
class DocumentSection:
    source: str
    title: str
    page: int | None
    section: str
    text: str


SECTION_HEADINGS = {
    "clinical presentation": "Clinical Presentation",
    "diagnosis": "Diagnosis",
    "differential diagnosis": "Differential Diagnosis",
    "red flags": "Red Flags",
}

SPLIT_SEPARATORS = ("\n\n", "\n", " ")


def load_document(
    path: str | Path,
    source: str,
    title: str,
) -> list[DocumentBlock]:
    """Load a UTF-8 text file or extract text from a PDF page by page."""
    document_path = Path(path)
    suffix = document_path.suffix.casefold()

    if suffix == ".txt":
        return [
            DocumentBlock(
                source=source,
                title=title,
                page=None,
                text=document_path.read_text(encoding="utf-8"),
            )
        ]

    if suffix == ".pdf":
        blocks: list[DocumentBlock] = []
        reader = PdfReader(document_path)
        for page_number, pdf_page in enumerate(reader.pages, start=1):
            text = pdf_page.extract_text()
            if text and text.strip():
                blocks.append(
                    DocumentBlock(
                        source=source,
                        title=title,
                        page=page_number,
                        text=text,
                    )
                )
        return blocks

    raise ValueError(f"Unsupported document type: {suffix}")


def detect_sections(blocks: list[DocumentBlock]) -> list[DocumentSection]:
    """Split document blocks at the four controlled clinical headings."""
    sections: list[DocumentSection] = []

    for block in blocks:
        current_section = "General"
        current_lines: list[str] = []

        def flush_section() -> None:
            section_text = "\n".join(current_lines).strip()
            if section_text:
                sections.append(
                    DocumentSection(
                        source=block.source,
                        title=block.title,
                        page=block.page,
                        section=current_section,
                        text=section_text,
                    )
                )

        for line in block.text.splitlines():
            heading = SECTION_HEADINGS.get(line.strip().casefold())
            if heading is not None:
                flush_section()
                current_section = heading
                current_lines = []
            else:
                current_lines.append(line)

        flush_section()

    return sections


def _split_boundary(text: str, chunk_size: int) -> int:
    search_start = chunk_size // 2
    candidate = text[: chunk_size + 1]

    for separator in SPLIT_SEPARATORS:
        position = candidate.rfind(separator, search_start)
        if position != -1:
            return position + len(separator)

    return chunk_size


def _split_text_recursive(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    cleaned_text = text.strip()
    if not cleaned_text:
        return []
    if len(cleaned_text) <= chunk_size:
        return [cleaned_text]

    boundary = _split_boundary(cleaned_text, chunk_size)
    current_chunk = cleaned_text[:boundary].strip()
    next_start = max(1, boundary - chunk_overlap)
    remaining_chunks = _split_text_recursive(
        cleaned_text[next_start:],
        chunk_size,
        chunk_overlap,
    )

    return ([current_chunk] if current_chunk else []) + remaining_chunks


def chunk_sections(
    sections: list[DocumentSection],
    chunk_size: int = DEFAULT_CONFIG.chunk_size,
    chunk_overlap: int = DEFAULT_CONFIG.chunk_overlap,
) -> list[EvidenceChunk]:
    """Recursively split oversized sections into traceable evidence chunks."""
    chunks: list[EvidenceChunk] = []

    for section_index, section in enumerate(sections):
        section_chunks = _split_text_recursive(
            section.text,
            chunk_size,
            chunk_overlap,
        )
        for chunk_index, content in enumerate(section_chunks):
            identity = "|".join(
                (
                    section.source,
                    section.title,
                    str(section.page),
                    section.section,
                    str(section_index),
                    str(chunk_index),
                    content,
                )
            )
            chunk_id = f"chunk-{sha256(identity.encode('utf-8')).hexdigest()[:16]}"
            chunks.append(
                EvidenceChunk(
                    source=section.source,
                    title=section.title,
                    page=section.page,
                    section=section.section,
                    chunk_id=chunk_id,
                    content=content,
                    retrieval_score=None,
                    matched_query="",
                )
            )

    return chunks


def preprocess_document(
    path: str | Path,
    source: str,
    title: str,
) -> list[EvidenceChunk]:
    """Load, section, and chunk one controlled local guideline file."""
    blocks = load_document(path, source=source, title=title)
    sections = detect_sections(blocks)
    return chunk_sections(sections)
