"""Deterministic structured patient interview collection."""

from core.schemas import PatientState


INTERVIEW_FIELDS = (
    "chief_complaint",
    "symptoms",
    "age",
    "gender",
    "duration",
    "medical_history",
    "allergies",
    "medications",
)

INTERVIEW_QUESTIONS = {
    "chief_complaint": "What is the main health problem you would like help with?",
    "symptoms": "What symptoms are you currently experiencing?",
    "age": "What is your age?",
    "gender": "What is your gender?",
    "duration": "How long have you had these symptoms?",
    "medical_history": "Do you have any relevant medical history?",
    "allergies": "Do you have any allergies?",
    "medications": "Are you currently taking any medications?",
}

NEGATIVE_ANSWERS = {
    "no",
    "none",
    "nope",
    "nothing",
    "not applicable",
    "n/a",
}

TEXT_FIELDS = {"chief_complaint", "gender", "duration"}
LIST_FIELDS = {"symptoms", "medical_history", "allergies", "medications"}
OPTIONAL_LIST_FIELDS = {"medical_history", "allergies", "medications"}


def update_patient_field(
    patient: PatientState,
    field_name: str,
    answer: str,
) -> PatientState:
    """Clean and store one interview answer on the existing patient state."""
    if field_name not in INTERVIEW_FIELDS:
        raise ValueError(f"Unknown interview field: {field_name}")

    cleaned_answer = answer.strip()
    is_negative = cleaned_answer.casefold() in NEGATIVE_ANSWERS

    if field_name in OPTIONAL_LIST_FIELDS and is_negative:
        setattr(patient, field_name, [])
        if field_name not in patient.explicit_negations:
            patient.explicit_negations.append(field_name)
        return patient

    if field_name in {"chief_complaint", "symptoms"} and is_negative:
        setattr(patient, field_name, "" if field_name == "chief_complaint" else [])
        return patient

    if field_name in TEXT_FIELDS:
        setattr(patient, field_name, cleaned_answer)
    elif field_name == "age":
        patient.age = int(cleaned_answer)
    elif field_name in LIST_FIELDS:
        values = [item.strip() for item in cleaned_answer.split(",") if item.strip()]
        setattr(patient, field_name, values)

    if field_name in patient.explicit_negations:
        patient.explicit_negations.remove(field_name)

    return patient


def get_missing_interview_fields(patient: PatientState) -> list[str]:
    """Return unresolved interview fields in their fixed question order."""
    missing_fields: list[str] = []

    for field_name in INTERVIEW_FIELDS:
        value = getattr(patient, field_name)

        if field_name in OPTIONAL_LIST_FIELDS:
            if not value and field_name not in patient.explicit_negations:
                missing_fields.append(field_name)
        elif field_name == "age":
            if value is None:
                missing_fields.append(field_name)
        elif not value:
            missing_fields.append(field_name)

    return missing_fields


def get_next_question(patient: PatientState) -> tuple[str, str] | None:
    """Return the first unresolved interview field and its neutral question."""
    missing_fields = get_missing_interview_fields(patient)
    if not missing_fields:
        return None

    field_name = missing_fields[0]
    return field_name, INTERVIEW_QUESTIONS[field_name]
