# FINAL TEST MATRIX

Django Check        TRUE  
Config              TRUE  
Schemas             TRUE  
Interview           TRUE  
Corpus              TRUE  
Retrieval           TRUE  
Reasoning           TRUE  
Sufficiency         TRUE  
KAS/LCS             TRUE  
DCS                 TRUE  
Follow-up           TRUE  
Pipeline            TRUE  
Evaluation          TRUE  
Synthetic Dataset   TRUE  
Portal              TRUE  
Real Services       FALSE  
Demo A              FALSE  
Demo B              FALSE

## Required result distinction

1. Deterministic Unit Tests = **PASS**
2. Portal Tests = **PASS**
3. Real End-to-End Smoke Test = **PASS**
4. Real Model Structured-Output Stability = **UNSTABLE / KNOWN LIMITATION**

`Real Services` is FALSE in the high-level Boolean matrix because the complete real-service test command did not pass: one independent Qwen structured response was truncated. This does not override the separately observed PASS for the real end-to-end smoke case.

Demo A and Demo B are FALSE only in the sense that the current website demonstration verification gate was not completed in this review. Per the final instruction, the stochastic models were not called repeatedly; both website demos are deferred for separate conversion to frozen recorded demonstrations. No clinical failure or model status is inferred from these rows.

## Command evidence

| Test area | Test command | Tests | Result | Failures | Errors |
|---|---|---:|---|---:|---:|
| Django Check | `python manage.py check` | system check | PASS | 0 | 0 |
| Config | `python -m unittest tests.test_config -v` | 5 | PASS | 0 | 0 |
| Schemas | `python -m unittest tests.test_schemas -v` | 14 | PASS | 0 | 0 |
| Interview | `python -m unittest tests.test_interview -v` | 4 | PASS | 0 | 0 |
| Corpus | `python -m unittest tests.test_corpus -v` | 3 | PASS | 0 | 0 |
| Retrieval | `python -m unittest tests.test_retrieval -v` | 4 | PASS | 0 | 0 |
| Reasoning | `python -m unittest tests.test_reasoning -v` | 3 | PASS | 0 | 0 |
| Sufficiency | `python -m unittest tests.test_sufficiency -v` | 4 | PASS | 0 | 0 |
| KAS/LCS validation | `python -m unittest tests.test_validation -v` | 3 | PASS | 0 | 0 |
| DCS | `python -m unittest tests.test_dcs -v` | 3 | PASS | 0 | 0 |
| Follow-up | `python -m unittest tests.test_followup -v` | 3 | PASS | 0 | 0 |
| Pipeline | `python -m unittest tests.test_pipeline -v` | 3 | PASS | 0 | 0 |
| Evaluation | `python -m unittest tests.test_evaluation -v` | 2 | PASS | 0 | 0 |
| Synthetic Dataset | `python -m unittest tests.test_case_dataset -v` | 2 | PASS | 0 | 0 |
| Portal | `python manage.py test portal` | 15 | PASS | 0 | 0 |
| Full discovery | `python -m unittest discover -s tests -v` | 56 | FAIL | 0 | 1 |
| Real Services rerun | `python -m unittest tests.test_real_services -v` | incomplete | INCONCLUSIVE | 0 observed | no final count |

The independent deterministic modules contain 53 passing tests in total. Portal contains 15 passing tests.

## Real-service evidence

During full discovery:

- `test_one_real_end_to_end_case`: PASS using the real local services.
- `test_real_retrieval_returns_metadata`: PASS.
- `test_real_independent_a_b_calls_are_parseable`: ERROR.
- Full discovery result: 56 tests, 55 passed, 0 failures, 1 error.

Observed error:

```text
json.decoder.JSONDecodeError:
Unterminated string starting at: line 2520 column 17 (char 178237)
```

Exact known limitation:

> Qwen occasionally returns truncated or incomplete structured JSON during real local inference.

On the later separate rerun, `test_one_real_end_to_end_case` passed again. The independent A/B parseability test did not complete before interruption, so the separate command has no final PASS/FAIL result and is recorded as **UNSTABLE / INCONCLUSIVE**. No further model retries were made.

## Appendix A evidence

| Test area | Test command | Number of tests | PASS/FAIL |
|---|---|---:|---|
| Deterministic unit/component tests | 13 independent `tests.test_*` commands excluding real services | 53 | PASS |
| Portal integration and authentication | `python manage.py test portal` | 15 | PASS |
| Django configuration | `python manage.py check` | system check | PASS |
| Full discovery including real services | `python -m unittest discover -s tests -v` | 56 | FAIL — 1 real-model JSON parse error |
| Real end-to-end smoke | `tests.test_real_services.RealServiceSmokeTests.test_one_real_end_to_end_case` within executed commands | 1 | PASS |
| Real model structured-output stability | `tests.test_real_services.RealServiceSmokeTests.test_real_independent_a_b_calls_are_parseable` | 1 | UNSTABLE / INCONCLUSIVE |
