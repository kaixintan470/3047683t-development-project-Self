# FINAL ASSESSMENT HISTORY DATABASE

IMPLEMENTATION_STATUS=PASS  
ARCHITECTURE_PRESERVED=TRUE  
DATABASE_MODEL=PASS  
REAL_ASSESSMENT_PERSISTENCE=PASS  
FOLLOWUP_RECORD_BEHAVIOUR=PASS  
DEMO_EXCLUSION=PASS  
USER_DATA_ISOLATION=PASS  
HISTORY_UI=PASS  
DJANGO_CHECK=PASS  
PORTAL_TESTS=PASS  
PORTAL_TEST_COUNT=31

## Implementation

- Added one minimal `AssessmentRecord` model linked to Django's existing authenticated user with `related_name="assessment_records"`.
- Stores terminal decision, existing approved likely condition and summary, full-precision KAS/LCS/DCS values, final patient snapshot, and the JSON-safe final result payload.
- Persistence occurs only after the normal canonical `/api/pipeline/` result is serialized and only for existing terminal statuses: `APPROVED` or `UNRESOLVED_INSUFFICIENT_INFORMATION`.
- `NEED_MORE_INFO` responses create no record. A later terminal follow-up completion creates one record containing the updated follow-up fact.
- Pipeline exceptions create no record.
- Scripted Demo A and Demo B endpoints remain fixture reads and create no record.
- `/app/history/` lists only the authenticated user's records newest first.
- `/app/history/<record_id>/` enforces ownership with a user-scoped 404 and reads saved snapshots without invoking inference.
- History UI displays KAS/DCS to two decimals and LCS as an integer while database values retain full precision.

## Architecture

The history feature wraps the existing real-pipeline response boundary. No file under `core/` was modified. Top-K, MedCPT/FAISS retrieval, Qwen/Gemma configuration, C1–C4 sufficiency, Dual-AND, KAS/LCS/DCS, follow-up rules, and terminal decision behaviour are unchanged.

No inference service is called by history list/detail pages or scripted demo routes.

## Migration

Migration filename:

- `portal/migrations/0001_initial.py`

Django generated and applied the migration successfully:

```text
Applying portal.0001_initial... OK
```

## Files changed

- `portal/models.py`
- `portal/migrations/0001_initial.py`
- `portal/views.py`
- `portal/urls.py`
- `portal/tests.py`
- `templates/portal/home.html`
- `templates/portal/history.html`
- `templates/portal/history_detail.html`
- `static/portal/app.css`
- `reports/FINAL_ASSESSMENT_HISTORY_DB.md`

## Commands executed

```powershell
python manage.py makemigrations portal
python manage.py migrate
python manage.py check
python manage.py test portal -v 2
```

The first Portal run exposed one deterministic test-fixture issue: two in-memory SQLite rows had equal timestamps, so their relative order was undefined. The test now assigns the older fixture a timestamp one minute earlier and continues to verify the model's `-created_at` ordering. No production history or clinical logic was changed for that correction.

## Final test result

```text
System check identified no issues (0 silenced).
Found 31 test(s).
Ran 31 tests in 7.444s
OK
```

Final counts:

- tests: 31
- failures: 0
- errors: 0

The logged `RuntimeError: local service unavailable` traces are deliberate mocked failure-path tests. Both passed and confirmed that failed pipeline calls create neither fake success payloads nor assessment records.

No real Ollama, Qwen, Gemma, MedCPT, FAISS, or unstable real-service test was invoked.

## Remaining limitations

- This is a patient-facing MSc prototype using the existing local SQLite configuration, not an electronic health record system.
- Existing historical pipeline runs are not backfilled; only terminal real assessments completed after this migration are persisted.
- No clinician dashboard, sharing, export, editing, deletion workflow, EHR/NHS integration, treatment recommendation, or investigation recommendation was added.
- The minimal prototype has no consultation idempotency key; the current UI disables a completed action, but an intentionally repeated terminal API request could create another snapshot.
- Scripted presentation demos are intentionally excluded from patient history.

## Git

- commit created: NO
- push performed: NO
- files staged: NO
- remotes changed: NO
