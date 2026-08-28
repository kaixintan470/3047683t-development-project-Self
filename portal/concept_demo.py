"""Local, token-free concept matching for the patient-language confirmation demo."""

from __future__ import annotations

from collections import Counter
from math import sqrt
import re

from portal.models import MedicalConcept


SEED_CONCEPTS = [
    {
        "code": "SYM_DYSURIA",
        "canonical_term": "Dysuria",
        "display_label": "排尿疼痛 / 烧灼感",
        "aliases": ["尿痛", "小便疼", "尿尿疼", "排尿刺痛", "排尿烧灼", "尿的时候火辣辣", "stinging when peeing"],
    },
    {
        "code": "SYM_FREQUENCY",
        "canonical_term": "Urinary frequency",
        "display_label": "排尿次数增多 / 尿频",
        "aliases": ["尿频", "老想尿", "总想去厕所", "一直跑厕所", "排尿次数多", "frequent urination"],
    },
    {
        "code": "SYM_URGENCY",
        "canonical_term": "Urinary urgency",
        "display_label": "尿急 / 突然强烈想排尿",
        "aliases": ["尿急", "憋不住尿", "突然特别想尿", "马上就得尿", "urgent urination"],
    },
    {
        "code": "SYM_HEMATURIA",
        "canonical_term": "Hematuria",
        "display_label": "血尿 / 尿液带血",
        "aliases": ["尿血", "尿里有血", "尿是红的", "血尿", "blood in urine"],
    },
    {
        "code": "SYM_SUPRAPUBIC_PAIN",
        "canonical_term": "Suprapubic pain",
        "display_label": "下腹 / 耻骨上疼痛",
        "aliases": ["下腹疼", "小肚子疼", "耻骨上疼", "下腹部疼痛", "suprapubic pain"],
    },
    {
        "code": "SYM_PELVIC_PRESSURE",
        "canonical_term": "Pelvic pressure",
        "display_label": "盆腔 / 下腹坠胀感",
        "aliases": ["下面胀", "下腹坠胀", "小肚子发胀", "盆腔坠胀", "pelvic pressure"],
    },
    {
        "code": "SYM_FEVER",
        "canonical_term": "Fever",
        "display_label": "发热 / 发烧",
        "aliases": ["发烧", "发热", "体温高", "高烧", "fever"],
    },
    {
        "code": "SYM_HEADACHE",
        "canonical_term": "Headache",
        "display_label": "头痛",
        "aliases": ["头疼", "头痛", "脑袋疼", "头很痛", "headache"],
    },
    {
        "code": "SYM_VOMITING",
        "canonical_term": "Vomiting",
        "display_label": "呕吐",
        "aliases": ["吐了", "一直吐", "呕吐", "想吐并吐出来", "vomiting"],
    },
    {
        "code": "SYM_NAUSEA",
        "canonical_term": "Nausea",
        "display_label": "恶心 / 想吐",
        "aliases": ["恶心", "想吐", "反胃", "nausea"],
    },
]


def ensure_seed_concepts() -> None:
    if MedicalConcept.objects.exists():
        return
    MedicalConcept.objects.bulk_create(
        [MedicalConcept(category="symptom", **item) for item in SEED_CONCEPTS]
    )


def _normalise(text: str) -> str:
    return re.sub(r"\s+", "", text.strip().lower())


def _char_ngram_vector(text: str, n: int = 2) -> Counter[str]:
    """Create a tiny local vector from character n-grams; no LLM or API tokens."""
    cleaned = _normalise(text)
    if not cleaned:
        return Counter()
    if len(cleaned) < n:
        return Counter({cleaned: 1})
    return Counter(cleaned[index : index + n] for index in range(len(cleaned) - n + 1))


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    left_norm = sqrt(sum(value * value for value in left.values()))
    right_norm = sqrt(sum(value * value for value in right.values()))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def rank_concepts(patient_text: str, top_k: int = 5) -> list[dict[str, object]]:
    """Return Top-K controlled concepts most similar to the patient's wording."""
    ensure_seed_concepts()
    patient_vector = _char_ngram_vector(patient_text)
    ranked: list[dict[str, object]] = []

    for concept in MedicalConcept.objects.all():
        candidate_phrases = [concept.display_label, concept.canonical_term, *concept.aliases]
        score = max(
            (_cosine(patient_vector, _char_ngram_vector(phrase)) for phrase in candidate_phrases),
            default=0.0,
        )
        ranked.append(
            {
                "code": concept.code,
                "canonical_term": concept.canonical_term,
                "display_label": concept.display_label,
                "score": round(score, 4),
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:top_k]
