# SYNTHETIC DATASET INTEGRATION

PASS

## DATASET

- repository path: `test_data/female_genitourinary_cases.json`
- cases: 20
- categories: 10
- real patient data: false
- external dataset: false

## LOADER

- load: PASS
- select by case_id: PASS
- PatientState conversion: PASS for all 20 cases
- label isolation: PASS; only `initial_patient_state` is converted

## TESTS

- Django check: PASS
- dataset tests: PASS
- total tests: 2
- failures: 0
- errors: 0

## ARCHITECTURE

- production pipeline changed: no
- labels leaked into production input: no
