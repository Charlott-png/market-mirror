# MM-002 Red Test Baseline

| Field | Result |
|---|---|
| Specification | MM-002 version 1.0 |
| Plan | PLAN-002 |
| Stage | Testing — Red |
| Date | 2026-10-25 |
| Python syntax | Valid |
| Tests discovered | 72 |
| Passing | 11 |
| Failing assertions | 4 |
| Setup errors | 57 |
| Validation result | Expected Red state confirmed |

## Commands used

```powershell
.venv\Scripts\python.exe -m compileall -q tests
.venv\Scripts\python.exe -m pytest --collect-only -q --basetemp <writable-test-folder>
.venv\Scripts\python.exe -m pytest -q --tb=no --basetemp <writable-test-folder>
```

`<writable-test-folder>` was a temporary folder owned by this task. It was used
because the execution sandbox does not allow pytest to use the computer's normal
Windows temporary folder. This changes only where temporary test files are kept;
it does not change what the tests check.

## Passing tests observed

Eleven tests passed. They confirm that the MM-001 application factory, pages,
health endpoint, error page, stylesheet, documentation, and other public
contracts still behave as expected before MM-002 implementation begins.

## Expected failures observed

Fifty-seven database-dependent test cases stopped during setup because the
future shared database extension has not been implemented yet:

```text
ModuleNotFoundError: No module named 'app.extensions'
```

One configuration test failed because the application does not yet define its
default `SQLALCHEMY_DATABASE_URI`.

Three migration tests failed because the future Flask-Migrate `db` command has
not been registered yet.

## Why this is a valid Red result

- Every test file contains valid Python syntax.
- pytest successfully discovered all 72 test cases.
- The 11 earlier foundation tests still pass.
- The remaining failures point directly to database features that MM-002 says
  must be created during Implementation.
- The failures are not caused by broken test syntax, a misspelled test command,
  or inaccessible temporary files.

The MM-002 tests are therefore ready to guide the Implementation stage. No
database implementation was added during Testing.
