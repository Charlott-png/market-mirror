# MM-001: Project Foundation

| Field | Value |
|---|---|
| Project | Market Mirror |
| Specification ID | MM-001 |
| Feature | Project foundation and first web page |
| Status | Approved |
| Version | 1.0 |
| Created | 2026-10-25 |
| Approved | 2026-10-25 |

## 1. Purpose

This specification defines the smallest working version of Market Mirror. Its purpose is to prove that the development environment, Flask web server, HTML rendering, error handling, and basic project documentation work correctly before marketplace features are added.

This stage creates a foundation only. It does not create users, products, a database, or AI functionality.

## 2. Student learning goals

After completing this feature, the student should be able to explain:

1. The difference between a web browser and a web server.
2. What an HTTP request and an HTTP response are.
3. How a Flask route connects a URL to a Python function.
4. Why a Python virtual environment is useful.
5. Why dependencies are recorded in a requirements file.
6. What an HTTP status code communicates.
7. Why automated tests are written before implementation in this project.

## 3. User story

As a visitor, I want to open Market Mirror in a browser and see a clear welcome page so that I know the application is running and understand its future purpose.

As a developer, I want a health endpoint and predictable error page so that I can confirm the server is working and diagnose incorrect URLs.

## 4. Scope

### 4.1 Included

- A Python project that runs inside a virtual environment.
- A Flask development server.
- A public home page at `/`.
- A public health endpoint at `/health`.
- A custom page for unknown URLs.
- A shared base HTML layout that later pages can reuse.
- A small stylesheet for a readable page.
- A dependency file containing the packages required for this stage.
- A README containing setup and run instructions.
- Automated tests derived from the approved requirements.

### 4.2 Excluded

The following are explicitly outside this specification:

- Database configuration or database models.
- Registration, login, logout, or user profiles.
- Product listings or image uploads.
- Search, filtering, saved products, or messaging.
- AI categorization, price prediction, or recommendations.
- Deployment to a public server.
- Payment, checkout, or shipping functionality.

These features require separate specifications and approval.

## 5. Functional requirements

### FR-001: Application startup

- The application shall start locally using a documented command.
- The server shall use Flask.
- Starting the application shall not require a database or an internet connection after dependencies are installed.
- A missing required configuration value shall produce a useful development error rather than silently failing.

### FR-002: Home page

- A `GET` request to `/` shall return HTTP status `200`.
- The response shall be an HTML document.
- The visible page shall contain the project name `Market Mirror`.
- The visible page shall briefly explain that Market Mirror is an online marketplace project.
- The page shall include a clear placeholder message explaining that marketplace features will be added gradually.

### FR-003: Health endpoint

- A `GET` request to `/health` shall return HTTP status `200`.
- The response shall use the `application/json` content type.
- The response body shall have exactly the following public fields:

```json
{
  "service": "market-mirror",
  "status": "ok"
}
```

- The health endpoint shall not reveal local file paths, secret values, package versions, or debug information.

### FR-004: Unknown URL handling

- A request to a route that does not exist shall return HTTP status `404`.
- The response shall be an HTML page rather than Flask's default plain error page.
- The page shall tell the visitor that the requested page could not be found.
- The page shall provide a link back to `/`.

### FR-005: Shared page layout

- The home page and the 404 page shall use the same base layout.
- The base layout shall contain the document title, page language, character encoding, viewport metadata, header, main content area, and footer.
- Page-specific content shall be inserted into the base layout instead of repeating the full document structure.

### FR-006: Basic presentation

- The application shall load its stylesheet from Flask's static-file system.
- Text shall remain readable at a browser width of 320 pixels.
- The interface shall not require JavaScript at this stage.
- Information shall remain understandable if the stylesheet fails to load.

### FR-007: Dependency record

- The project shall contain a dependency file that allows another developer to install the packages needed for this stage.
- Flask and pytest shall be included.
- The dependency file shall not list unrelated packages from the developer's global Python installation.

### FR-008: Project documentation

- The README shall describe the project in beginner-friendly language.
- The README shall document prerequisites, environment creation, dependency installation, server startup, and test execution.
- The documented commands shall target PowerShell on Windows for this stage.
- The README shall identify the feature as the project foundation and list the intentionally excluded marketplace features.

## 6. Non-functional requirements

### NFR-001: Beginner readability

- Python functions and variables shall use descriptive names.
- Files shall remain small enough for a beginner to examine individually.
- Comments shall explain reasons or unfamiliar ideas, not repeat obvious code.
- Unnecessary design patterns and abstractions shall be avoided.

### NFR-002: Maintainability

- Application creation shall be structured so later features can add configuration, extensions, and route groups without replacing the entire foundation.
- HTML shall use semantic elements where appropriate.
- Repeated page structure shall exist in one base template.

### NFR-003: Testability

- The application shall be constructible in a testing mode without starting a real web server.
- Tests shall not depend on execution order.
- Tests shall not require network access or modify files outside the project.

### NFR-004: Accessibility

- The HTML document shall declare English as its language.
- The page shall contain one clear top-level heading.
- Navigation and links shall be usable with a keyboard.
- Text and background colors shall provide readable contrast.

### NFR-005: Security baseline

- Debug mode shall not be hard-coded as permanently enabled.
- Health responses shall contain no sensitive details.
- User-controlled HTML is not part of this stage.
- Secrets shall not be committed to the repository.

## 7. Public interfaces

| Method | Path | Successful result | Authentication |
|---|---|---|---|
| `GET` | `/` | HTML, status `200` | Not required |
| `GET` | `/health` | JSON, status `200` | Not required |
| Any supported request | Unknown path | HTML, status `404` | Not required |

No other public application route is required by this specification.

## 8. Acceptance scenarios

### AC-001: Visitor opens the home page

**Given** the Market Mirror application is running  
**When** a visitor requests `/`  
**Then** the server responds with status `200`  
**And** the response is HTML  
**And** the visible content includes `Market Mirror`  
**And** the page explains the project's marketplace purpose.

### AC-002: Monitoring checks application health

**Given** the Market Mirror application is running  
**When** a client requests `/health`  
**Then** the server responds with status `200`  
**And** the response content type is JSON  
**And** the decoded response equals `{"service": "market-mirror", "status": "ok"}`.

### AC-003: Visitor requests a missing page

**Given** the Market Mirror application is running  
**When** a visitor requests `/this-page-does-not-exist`  
**Then** the server responds with status `404`  
**And** the response is HTML  
**And** the page explains that the requested page was not found  
**And** the page includes a link to `/`.

### AC-004: Pages share a common layout

**Given** the home page and 404 page are rendered  
**When** their HTML is examined  
**Then** both pages contain the shared site header and footer  
**And** neither page duplicates the complete base layout in its own template.

### AC-005: New developer follows the README

**Given** Python and Git are installed on a Windows computer  
**And** the developer has a fresh copy of the project  
**When** the developer follows the README commands in order  
**Then** dependencies install inside a virtual environment  
**And** the server starts  
**And** the home page can be opened  
**And** the automated test command completes successfully.

### AC-006: Narrow-screen readability

**Given** the home page is open  
**When** the browser viewport is 320 pixels wide  
**Then** the main content remains readable  
**And** important content is not cut off horizontally.

## 9. Constraints and assumptions

- Development operating system: Windows with PowerShell.
- Programming language: Python 3.11 or newer.
- Web framework: Flask.
- Test framework: pytest.
- The student has Git installed or will install it before the first commit.
- This stage uses server-rendered HTML rather than a JavaScript frontend framework.
- The development server is for local learning only and is not a production server.

## 10. Completion rule

This specification moved from **Draft** to **Approved** when the student explicitly approved MM-001 on 2026-10-25.

After approval, work must occur in this exact order:

1. Produce an implementation and test plan mapped to the requirement IDs.
2. Write pytest tests for the approved acceptance scenarios.
3. Run the tests and confirm they fail for the expected reason because the feature is not implemented yet.
4. Implement the minimum application code required to satisfy the tests.
5. Run the tests again and confirm they pass.
6. Explain the code and concepts in beginner-friendly language.

No planning, test code, or application implementation is authorized while this specification remains in Draft status.

