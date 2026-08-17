# AUTHENTICATION

PASS

- landing page: implemented at `/`
- registration: implemented at `/register/`
- email login: Django authentication with email stored as the unique username
- password hashing: Django `create_user` / `set_password`
- protected app: `/app/` requires authentication
- logout: POST `/logout/`
- admin@example.com account available: deterministic `ensure_test_account` command added
- migrations: PASS — all Django `admin`, `auth`, `contenttypes`, and `sessions` migrations applied
- local test account: PASS — `admin@example.com` created by `ensure_test_account`; password is stored through Django hashing

## TESTS

- `python manage.py check`: PASS — 0 issues
- `python manage.py test portal`: PASS — 15 tests, 0 failures, 0 errors
