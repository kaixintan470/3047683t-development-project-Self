import unittest

from core.interview import (
    get_missing_interview_fields,
    get_next_question,
    update_patient_field,
)
from core.schemas import PatientState


class StructuredInterviewTests(unittest.TestCase):
    def test_complete_scripted_interview(self):
        patient = PatientState()
        answers = (
            ("chief_complaint", "Burning sensation during urination"),
            ("symptoms", "dysuria, frequency, urgency"),
            ("age", "28"),
            ("gender", "female"),
            ("duration", "2 days"),
            ("medical_history", "none"),
            ("allergies", "none"),
            ("medications", "none"),
        )

        for field_name, answer in answers:
            update_patient_field(patient, field_name, answer)

        self.assertEqual(patient.chief_complaint, "Burning sensation during urination")
        self.assertEqual(patient.symptoms, ["dysuria", "frequency", "urgency"])
        self.assertEqual(patient.age, 28)
        self.assertEqual(patient.gender, "female")
        self.assertEqual(patient.duration, "2 days")
        self.assertEqual(patient.medical_history, [])
        self.assertEqual(patient.allergies, [])
        self.assertEqual(patient.medications, [])
        self.assertIn("medical_history", patient.explicit_negations)
        self.assertIn("allergies", patient.explicit_negations)
        self.assertIn("medications", patient.explicit_negations)
        self.assertIsNone(get_next_question(patient))

    def test_explicit_negation_is_not_treated_as_missing(self):
        patient = PatientState(allergies=[], explicit_negations=["allergies"])
        self.assertNotIn("allergies", get_missing_interview_fields(patient))

    def test_no_and_none_are_confirmed_absent_but_blank_remains_unknown(self):
        patient = PatientState()

        update_patient_field(patient, "medical_history", "No")
        update_patient_field(patient, "allergies", "None")
        update_patient_field(patient, "medications", "   ")

        self.assertIn("medical_history", patient.explicit_negations)
        self.assertIn("allergies", patient.explicit_negations)
        self.assertNotIn("medications", patient.explicit_negations)
        self.assertNotIn("medical_history", get_missing_interview_fields(patient))
        self.assertNotIn("allergies", get_missing_interview_fields(patient))
        self.assertIn("medications", get_missing_interview_fields(patient))

    def test_existing_patient_facts_are_preserved(self):
        patient = PatientState(
            chief_complaint="Burning sensation during urination",
            symptoms=["dysuria", "frequency", "urgency"],
        )

        update_patient_field(patient, "duration", "2 days")

        self.assertEqual(patient.chief_complaint, "Burning sensation during urination")
        self.assertEqual(patient.symptoms, ["dysuria", "frequency", "urgency"])
        self.assertEqual(patient.duration, "2 days")


if __name__ == "__main__":
    unittest.main()
