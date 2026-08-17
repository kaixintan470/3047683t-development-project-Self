# FINAL SCRIPTED DEMO

PASS

## DEMO A

DEMO_A_INITIAL_STATE=TRUE  
DEMO_A_BUTTON_RUN_REAL_PIPELINE=TRUE  
DEMO_A_FIXED_FINAL_STATE=TRUE  
DEMO_A_CALLS_LIVE_PIPELINE=FALSE

Demo A uses `GU01_UTI_COMPLETE` and follows exactly two scripted presentation states: detailed initial facts, then a fixed completed result. Its displayed KAS, LCS and DCS use the previously recorded Demo A values documented in `reports/TWO_DEMO_CASES.md`. The fixture and UI identify all demo output as scripted presentation content.

## DEMO B

DEMO_B_INITIAL_STATE=TRUE  
DEMO_B_FIXED_FOLLOWUP_STATE=TRUE  
DEMO_B_FOLLOWUP_QUESTION_VISIBLE=TRUE  
DEMO_B_REQUIRES_USER_TEXT_INPUT=FALSE  
DEMO_B_BUTTON_CHANGES_TO_SUBMIT_ADDITIONAL_INFORMATION=TRUE  
DEMO_B_AUTOMATICALLY_APPLIES_SUPPLEMENTAL_FACT=TRUE  
DEMO_B_FIXED_FINAL_STATE=TRUE  
DEMO_B_CALLS_LIVE_PIPELINE=FALSE

Demo B uses `GU02_UTI_INCOMPLETE` and follows exactly three scripted presentation states. Vaginal discharge is initially displayed as unknown, the fixed follow-up asks whether unusual vaginal discharge is present, and the second click automatically displays it as confirmed absent before rendering the scripted final result. No answer field is required. Its displayed KAS, LCS and DCS use the previously recorded Demo B values documented in `FINAL_CODE_REVIEW.md`.

## MODE SEPARATION

NORMAL_MODE_CALLS_CANONICAL_PIPELINE=TRUE  
DEMO_NOTICE_VISIBLE=TRUE  
DEMO_SWITCH_RESETS_STATE=TRUE

The demo routes read only `test_data/scripted_demo_cases.json`. The frontend handles demo transitions before the live request branch and never posts demo actions to `/api/pipeline/`. `Run Live Assessment` resets all demo state. Normal non-demo submissions still post to `/api/pipeline/`, which still instantiates the unchanged canonical pipeline through `create_real_pipeline()`.

## UI

ASSESSMENT_SUMMARY_PRESERVED=TRUE  
TECHNICAL_TRACE_PRESERVED=TRUE  
KAS_DCS_TWO_DECIMALS=TRUE  
LCS_INTEGER=TRUE

The same patient, evidence, dual-SLM, Assessment Summary and validation components are reused for live and scripted presentation output. The visible notice states that demo output is fixed and that no live model inference is executed.

## TESTS

DJANGO_CHECK=PASS  
PORTAL_TESTS=19  
PORTAL_RESULT=PASS  
FAILURES=0  
ERRORS=0

Commands executed:

```text
python manage.py check
python manage.py test portal -v 2
```

The expected logged `RuntimeError: local service unavailable` comes from the existing mocked JSON-error test; that test passed. No Ollama, Qwen, Gemma, MedCPT, FAISS, real demo inference, real-service suite, or unstable structured-output test was run.

## ARCHITECTURE

SECOND_PIPELINE_CREATED=NO  
CORE_CLINICAL_LOGIC_CHANGED=NO  
TOP_K_CHANGED=NO  
DUAL_AND_CHANGED=NO  
KAS_LCS_DCS_FORMULAS_CHANGED=NO

No file under `core/` was changed. The scripted fixture is presentation data, not a reasoning pipeline, and contains no treatment or investigation recommendation.

## GIT

COMMIT_CREATED=NO  
PUSH_PERFORMED=NO

No files were staged and existing remotes were not changed.
