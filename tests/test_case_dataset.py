from collections import Counter, defaultdict
from dataclasses import asdict
from unittest import TestCase

from evaluation.case_loader import (
    EVALUATION_ONLY_FIELDS,
    load_case_dataset,
    patient_state_from_case,
    select_case,
)


class SyntheticCaseDatasetTests(TestCase):
    def test_dataset_integrity(self) -> None:
        dataset = load_case_dataset()
        cases = dataset["cases"]
        case_ids = [case["case_id"] for case in cases]
        category_counts = Counter(case["category_id"] for case in cases)
        presentations = defaultdict(list)
        for case in cases:
            presentations[case["category_id"]].append(case["presentation_type"])

        self.assertEqual(len(cases), 20)
        self.assertEqual(len(set(case_ids)), 20)
        self.assertEqual(len(category_counts), 10)
        self.assertTrue(all(count == 2 for count in category_counts.values()))
        self.assertTrue(
            all(sorted(values) == ["complete", "initially_incomplete"] for values in presentations.values())
        )
        self.assertTrue(all(case["synthetic"] is True for case in cases))
        self.assertTrue(
            all(case["initial_patient_state"]["gender"] == "female" for case in cases)
        )
        self.assertTrue(
            all(
                type(case["initial_patient_state"]["age"]) is int
                and case["initial_patient_state"]["age"] >= 18
                for case in cases
            )
        )
        self.assertIs(dataset["construction"]["real_patient_data"], False)
        self.assertIs(dataset["construction"]["external_dataset"], False)

    def test_patient_state_compatibility_and_label_isolation(self) -> None:
        dataset = load_case_dataset()
        for case in dataset["cases"]:
            selected = select_case(case["case_id"], dataset)
            patient = patient_state_from_case(selected)
            patient_payload = asdict(patient)

            self.assertEqual(patient.gender, "female")
            self.assertTrue(EVALUATION_ONLY_FIELDS.isdisjoint(patient_payload))
            self.assertTrue(
                EVALUATION_ONLY_FIELDS.isdisjoint(patient.__dict__)
            )
