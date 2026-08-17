# FROZEN DEMO PATCH

FAIL

The evidence-sufficiency stop condition in `FINAL_FROZEN_DEMO_PATCH.md` was triggered. No fixture, demo endpoint, frontend behaviour, clinical code, or test was added or modified. Creating the requested frozen demonstrations from the available records would require fabricating or combining values from different runs, which is prohibited.

## DEMO A

- fixture source identified: PARTIAL — `evidence/final_demo/demo_a_complete_case.png` and `reports/TWO_DEMO_CASES.md`
- live pipeline called: NOT APPLICABLE — frozen mode was not implemented
- one-stage deterministic presentation: NO

Recoverable from the recorded Demo A run:

- case: `GU01_UTI_COMPLETE`
- patient facts
- displayed EAU evidence excerpts
- displayed Qwen and Gemma reasoning
- KAS `0.705218216100753`
- LCS `3`
- DCS `0.7789136620755648`
- final status `APPROVED`

Missing required recorded field:

- the complete structured Assessment Summary expected by the current UI, including its exact recorded concise summary; the existing screenshot predates that UI section

## DEMO B

- fixture source identified: PARTIAL — `evidence/final_demo/demo_b_incomplete_case.png`, `reports/TWO_DEMO_CASES.md`, and `FINAL_CODE_REVIEW.md`
- Stage 1 follow-up loaded: NO
- recorded answer required: NO — not implemented
- Stage 2 final result loaded: NO
- live pipeline called during demo: NOT APPLICABLE — frozen mode was not implemented

The repository does not contain one internally consistent, complete recorded two-stage run for `GU02_UTI_INCOMPLETE`.

Available records conflict or are incomplete:

- `demo_b_incomplete_case.png` records the age-27 GU02 website run ending `UNRESOLVED_INSUFFICIENT_INFORMATION`; it does not contain a Stage 1 follow-up question followed by a final Stage 2 result.
- `reports/TWO_DEMO_CASES.md` records a separate trace verification that reached `APPROVED` after two follow-up rounds, but does not preserve the exact questions, complete final diagnosis, evidence, both reasoning outputs, or scores.
- `FINAL_CODE_REVIEW.md` records another GU02 run using answer `No`, ending `APPROVED` after one follow-up round with KAS `0.6984387350589722`, LCS `3`, and DCS `0.7738290512942292`; it does not preserve the exact Stage 1 question, complete final diagnosis, evidence, or both reasoning outputs.
- `evidence/phase_12/02_followup.png` and `03_approved_result.png` show an age-28 case, while `GU02_UTI_INCOMPLETE` is age 27. Those screenshots cannot be relabelled or combined with GU02.

Missing fields required to implement Demo B without fabrication:

- one exact recorded GU02 Stage 1 follow-up question
- the exact answer paired with that same selected run
- the complete updated GU02 Stage 2 patient state
- the complete Stage 2 retrieved evidence from that run
- both complete Stage 2 model reasoning outputs from that run
- the Stage 2 diagnosis and Assessment Summary from that run
- KAS, LCS, DCS, trace, and final status tied to all of the same fields above

## LIVE MODE

- canonical ClinicalPipeline still used: YES
- real assessment route unchanged: YES

The existing `/api/pipeline/` route remains connected to `create_real_pipeline()` and the unchanged canonical `ClinicalPipeline`.

## UI

- frozen-demo notice shown: NO — patch stopped before implementation
- Assessment Summary preserved: YES — existing live UI remains unchanged
- technical trace preserved: YES — existing live UI remains unchanged
- KAS/DCS two-decimal display preserved: YES — existing live UI remains unchanged

## TESTS

- Django check: PASS — 0 issues
- Portal tests: PASS — 15 tests
- failures: 0
- errors: 0

These are the unchanged current Portal tests. Frozen-demo acceptance tests were not added because the required recorded fixture could not be created without fabrication.

The logged `RuntimeError: local service unavailable` traceback is deliberately injected by an existing Portal test that verifies controlled JSON error handling; the test passed.

No Ollama, MedCPT, FAISS, Qwen, Gemma, ClinicalPipeline demo run, or unstable real-model structured-output test was invoked.

## ARCHITECTURE

- second pipeline created: NO
- core clinical logic changed: NO
- Top-K changed: NO
- KAS/LCS/DCS formulas changed: NO

## GIT

- commit created: NO
- push performed: NO

## REQUIRED NEXT INPUT

To complete this patch, provide or place in the repository a machine-readable saved payload from one complete real Demo A run and one complete two-stage real Demo B run. The Demo B record must preserve Stage 1, its exact answer, and Stage 2 as one run. Once those records exist, the fixture-driven presentation can be implemented without invoking the models or inventing clinical values.
