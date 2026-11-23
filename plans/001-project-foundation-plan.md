# MM-001: Project Foundation — Implementation and Test Plan

| Field | Value |
|---|---|
| Project | Market Mirror |
| Plan ID | PLAN-001 |
| Approved specification | MM-001 version 1.0 |
| Stage | Planning |
| Status | Approved |
| Created | 2026-10-25 |
| Approved | 2026-10-25 |

## 1. Purpose of this plan

The approved specification describes **what** the project foundation must do. This plan describes **how we intend to prove and build it**, without creating tests or application code yet.

The work will continue in this order:

1. Review and accept this plan.
2. Write the pytest tests described in this plan.
3. Validate that pytest discovers the tests and that they fail because the application is not implemented.
4. Implement the smallest amount of application code needed to satisfy the tests.
5. Run all tests and perform the manual checks.

## 2. Proposed technical approach

The foundation will use a small Flask **application factory**.

An application factory is a Python function named `create_app`. Instead of creating one global application that is difficult to configure, the function creates and returns a Flask application when it is called.

This approach is useful because:

- The development server can create an application configured for local use.
- pytest can create a separate application configured for testing.
- Future database and login extensions can be added in one predictable place.
- Tests do not need to start a real network server.

The initial pages will be rendered on the server using Jinja templates. A shared `base.html` template will contain the repeated page structure, while the home and 404 templates will provide only their page-specific content.

## 3. Planned project structure

The following files are planned. They do not exist yet unless identified as an approved specification or plan.

```text
market-mirror/
├── app/
│   ├── __init__.py              # Defines create_app()
│   ├── routes.py                # Home and health routes
│   ├── templates/
│   │   ├── base.html            # Shared HTML structure
│   │   ├── index.html           # Home-page content
│   │   └── errors/
│   │       └── 404.html         # Friendly missing-page content
│   └── static/
│       └── css/
│           └── style.css        # Basic responsive presentation
├── plans/
│   └── 001-project-foundation-plan.md
├── specs/
│   └── 001-project-foundation.md
├── tests/
│   ├── conftest.py              # Reusable test application/client fixtures
│   └── test_foundation.py       # Tests for MM-001
├── .gitignore                   # Files Git must not track
├── README.md                    # Beginner setup and usage guide
├── requirements.txt             # Runtime dependency: Flask
├── requirements-dev.txt         # Test dependency: pytest
└── run.py                       # Simple local development entry point
```

### Why dependencies are split

`requirements.txt` will contain packages required to run the application. `requirements-dev.txt` will contain packages required only while developing or testing it.

This teaches the difference between:

- A **runtime dependency**, which the deployed application needs.
- A **development dependency**, which helps developers but is not part of the running website.

## 4. Planned implementation steps

These steps describe the future Implementation stage. They must not begin until the Testing stage is complete and the tests have been observed failing for the expected reasons.

### IMP-001: Create the application factory

Planned file: `app/__init__.py`

- Define `create_app(test_config=None)`.
- Create the Flask application.
- Apply optional test configuration when provided.
- Register the routes and 404 error handler.
- Return the configured application.
- Do not hard-code debug mode.

Mapped requirements: FR-001, NFR-002, NFR-003, NFR-005.

### IMP-002: Add the public routes

Planned file: `app/routes.py`

- Add `GET /` and render `index.html`.
- Add `GET /health` and return the exact approved JSON fields.
- Keep the health response free of internal details.

Mapped requirements: FR-002, FR-003, NFR-005.

### IMP-003: Add shared and page-specific templates

Planned files: `base.html`, `index.html`, and `errors/404.html`.

- Put the HTML document structure, metadata, header, main element, and footer in `base.html`.
- Make `index.html` extend the base template.
- Make the 404 template extend the same base template.
- Put exactly one top-level heading in each rendered page.
- Add a home link to the 404 page.

Mapped requirements: FR-002, FR-004, FR-005, NFR-004.

### IMP-004: Add basic responsive styles

Planned file: `app/static/css/style.css`.

- Use a small set of readable colors, spacing, and font rules.
- Keep the layout usable at 320 pixels wide.
- Avoid JavaScript and decorative complexity.
- Preserve readable document order without CSS.

Mapped requirements: FR-006, NFR-004.

### IMP-005: Add local startup entry point

Planned file: `run.py`.

- Import and call the application factory.
- Allow Flask's normal local development command to find the application.
- Avoid forcing debug mode in source code.

Mapped requirements: FR-001, NFR-005.

### IMP-006: Record dependencies and ignored files

Planned files: `requirements.txt`, `requirements-dev.txt`, and `.gitignore`.

- Record Flask as a runtime dependency.
- Record pytest as a development dependency.
- Ignore `.venv`, Python cache files, pytest cache files, environment files, and editor/OS clutter.
- Do not ignore specifications, plans, tests, source code, or templates.

Mapped requirements: FR-007, NFR-005.

### IMP-007: Write beginner-friendly project documentation

Planned file: `README.md`.

- Explain what Market Mirror will become.
- Clearly identify MM-001 as a foundation stage.
- Document PowerShell commands for setup, activation, installation, startup, and tests.
- Explain what each important command does.
- List features that are not implemented yet.

Mapped requirements: FR-008, NFR-001.

## 5. Pytest strategy

pytest will use Flask's built-in test client. The test client behaves like a tiny browser controlled by Python. It can request routes and inspect their responses without opening Chrome, Edge, or a real network port.

### Planned fixtures

`tests/conftest.py` will define:

- `app`: creates the Flask application with `TESTING=True`.
- `client`: creates a test client from the test application.

Fixtures avoid repeating the same setup in every test.

### Planned test cases

#### TEST-001: Application can be created in testing mode

- Create the application with testing configuration.
- Assert that testing mode is enabled.
- Do not start a real server.

Requirements covered: FR-001, NFR-003.

#### TEST-002: Home page returns successful HTML

- Request `GET /`.
- Assert status `200`.
- Assert an HTML content type.
- Assert the response contains `Market Mirror`.
- Assert the response contains a short marketplace description.
- Assert the response contains the gradual-development placeholder.

Requirements covered: FR-002; acceptance scenario AC-001.

#### TEST-003: Health endpoint returns the exact public contract

- Request `GET /health`.
- Assert status `200`.
- Assert a JSON content type.
- Decode the JSON.
- Assert it equals exactly:

```json
{"service": "market-mirror", "status": "ok"}
```

- Assert no unexpected fields are present.

Requirements covered: FR-003, NFR-005; acceptance scenario AC-002.

#### TEST-004: Unknown route returns the custom 404 page

- Request `GET /this-page-does-not-exist`.
- Assert status `404`.
- Assert an HTML content type.
- Assert the response explains that the page was not found.
- Assert the HTML contains a link whose destination is `/`.

Requirements covered: FR-004; acceptance scenario AC-003.

#### TEST-005: Home page contains shared layout elements

- Request the home page.
- Assert that the rendered response contains a site header, main content region, and footer.
- Assert the document declares English.
- Assert the response contains viewport metadata.

Requirements covered: FR-005, NFR-004; part of AC-004.

#### TEST-006: 404 page contains shared layout elements

- Request an unknown route.
- Assert that the response contains the same site header and footer identifiers as the home page.
- Assert the page still returns status `404` rather than accidentally returning `200`.

Requirements covered: FR-004, FR-005; acceptance scenario AC-004.

#### TEST-007: Stylesheet is linked and available

- Request the home page.
- Assert it links to the expected static stylesheet.
- Request that stylesheet URL.
- Assert it returns status `200`.
- Assert it uses a CSS content type.

Requirements covered: FR-006.

#### TEST-008: Dependency files contain the correct package groups

- Read the two project-owned dependency files.
- Assert Flask appears in the runtime file.
- Assert pytest appears in the development file.
- Assert pytest does not appear as a runtime requirement.

Requirements covered: FR-007.

#### TEST-009: README contains all required setup sections

- Read the project README.
- Assert it mentions prerequisites, virtual-environment creation, activation, installation, startup, and test execution.
- Assert it identifies unimplemented features.

Requirements covered: FR-008; supports AC-005.

## 6. Manual validation plan

Some requirements are clearer when checked by a person rather than by a fragile automated test.

### MANUAL-001: Fresh PowerShell setup

Follow the README from a clean virtual environment and confirm:

1. Dependencies install successfully.
2. The local server starts with the documented command.
3. `/` and `/health` can be opened.
4. The documented pytest command works.

Requirements covered: AC-005.

### MANUAL-002: Narrow-screen readability

Open the home page with the browser viewport set to 320 pixels wide and confirm:

1. No important text is cut off.
2. The page does not require horizontal scrolling for its main content.
3. The home link and other interactive elements remain usable.

Requirements covered: FR-006, NFR-004, AC-006.

### MANUAL-003: Page without styles

Disable or temporarily block the stylesheet and confirm that headings, paragraphs, navigation, and page order still make sense.

Requirements covered: FR-006.

## 7. Requirement traceability matrix

A traceability matrix is a table connecting each requirement to the work that will implement and verify it. It helps ensure nothing in the specification is forgotten.

| Requirement | Planned implementation | Planned verification |
|---|---|---|
| FR-001 | IMP-001, IMP-005 | TEST-001, MANUAL-001 |
| FR-002 | IMP-002, IMP-003 | TEST-002 |
| FR-003 | IMP-002 | TEST-003 |
| FR-004 | IMP-003 | TEST-004, TEST-006 |
| FR-005 | IMP-003 | TEST-005, TEST-006 |
| FR-006 | IMP-004 | TEST-007, MANUAL-002, MANUAL-003 |
| FR-007 | IMP-006 | TEST-008, MANUAL-001 |
| FR-008 | IMP-007 | TEST-009, MANUAL-001 |
| NFR-001 | All small source files, IMP-007 | Code review and student explanation |
| NFR-002 | IMP-001, IMP-003 | TEST-001, TEST-005, TEST-006 |
| NFR-003 | IMP-001 | TEST-001 and isolated pytest execution |
| NFR-004 | IMP-003, IMP-004 | TEST-005, MANUAL-002, MANUAL-003 |
| NFR-005 | IMP-001, IMP-002, IMP-005, IMP-006 | TEST-003 and repository review |

## 8. Expected Red–Green workflow

### Red stage: tests exist before the feature

During the Testing stage:

1. Create only the test files described above.
2. Check that Python can parse the test files.
3. Run pytest.
4. Confirm the tests fail because the `app` package and feature files do not exist yet.
5. Record the failure summary as evidence that the tests were written first.

A failure is useful here only if it occurs for the expected reason. A spelling mistake or invalid Python syntax is not an acceptable Red result.

### Green stage: minimum implementation satisfies the tests

During the Implementation stage:

1. Create the planned source and documentation files.
2. Run the smallest relevant test after each small change.
3. Run the entire test suite when all tests pass individually.
4. Perform the three manual checks.
5. Avoid adding features outside MM-001.

## 9. Planned work order

The work order is designed to make errors easy to locate:

1. Create `tests/conftest.py` and `tests/test_foundation.py`.
2. Validate test syntax and pytest discovery.
3. Run tests and capture the expected Red result.
4. Create dependency and ignore files.
5. Create the application factory.
6. Add routes and error handler.
7. Add templates.
8. Add stylesheet.
9. Add local entry point.
10. Add README.
11. Run individual tests during implementation.
12. Run the complete test suite.
13. Perform manual validation.
14. Explain each file and concept to the student.
15. Make the first Git commit only after the feature is verified.

## 10. Definition of done

MM-001 will be complete only when:

- Every approved functional requirement has an implementation.
- All planned pytest tests pass.
- All three manual checks pass.
- No feature listed as out of scope has been added.
- The README setup has been followed successfully.
- No secret, virtual environment, or cache file is tracked by Git.
- The student can explain routes, responses, templates, fixtures, and the Red–Green process in their own words.

## 11. Approval gate

This plan must be reviewed before test code is created. Approval authorizes only the **Testing** stage. It does not authorize application implementation until the tests have been written, checked, run, and observed failing for the expected missing-feature reason.

