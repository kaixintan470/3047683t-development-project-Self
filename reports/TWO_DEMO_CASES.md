# TWO DEMO CASES

PASS

## DEMO A

- case_id: `GU01_UTI_COMPLETE`
- initial input loaded: yes; only `initial_patient_state`
- real retrieval: yes; EAU evidence displayed by the actual application
- SLM-A: yes; `qwen2.5:3b`, actual `SUFFICIENT` output displayed
- SLM-B: yes; `gemma2:2b`, actual `SUFFICIENT` output displayed
- sufficiency: both sufficient in the screenshot run
- entered KAS/LCS/DCS: yes; KAS `0.705218216100753`, LCS `3`, DCS `0.7789136620755648`
- final status: `APPROVED`
- screenshot: `evidence/final_demo/demo_a_complete_case.png`

## DEMO B

- case_id: `GU02_UTI_INCOMPLETE`
- initial input loaded: yes; only `initial_patient_state`
- real retrieval: yes
- SLM-A: yes
- SLM-B: yes
- follow-up/abstention: the actual website screenshot run safely returned `UNRESOLVED_INSUFFICIENT_INFORMATION`; a separate real canonical trace verification used neutral `No` answers, performed 2 follow-up rounds, retrieved Top-5 evidence on all 3 passes, and reached dual sufficiency
- final status: website screenshot run `UNRESOLVED_INSUFFICIENT_INFORMATION`; trace verification rerun `APPROVED` after 2 real follow-up rounds. Both are defined real statuses; no status was forced.
- screenshot: `evidence/final_demo/demo_b_incomplete_case.png`

## UI SAFETY

- expected diagnosis exposed: no
- evaluation labels exposed: no
- fake scores/results: no
- separate demo pipeline: no

## TESTS

- Django check: PASS
- Portal tests: PASS, 6/6

## NOTE ON REAL-MODEL VARIABILITY

The two Demo B runs produced different defined outcomes despite temperature 0. The application displays the result returned by the real canonical backend for that run and does not substitute evaluation labels, reference answers, diagnoses, scores, or statuses.
