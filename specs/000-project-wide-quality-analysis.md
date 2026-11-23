# MM-QA-000: Project-Wide Risk, Edge-Case, Solution, and Testing Analysis

| Field | Value |
|---|---|
| Project | Market Mirror |
| Specification ID | MM-QA-000 |
| Scope | Complete 16-week project |
| Status | Approved |
| Version | 1.0 |
| Created | 2026-10-25 |
| Approved | 2026-10-25 |
| Existing context policy | Preserve all existing files and decisions |

## 1. Purpose

This specification defines a project-wide quality analysis for the complete 16-week Market Mirror roadmap.

After this specification is approved, the Planning stage will produce a master document that identifies realistic problems, failure modes, misuse cases, boundary conditions, and unusual user situations for every planned feature. Each identified issue will include a practical prevention or recovery solution and a detailed testing plan.

This specification does not replace the existing roadmap or MM-001 documents. It adds a quality and risk layer that future feature specifications, plans, tests, and implementations must consult.

## 2. Why this analysis is needed

Software often works correctly during a simple demonstration but fails when users provide unexpected data, repeat an action, lose their connection, access someone else's URL, or use the application differently from the developer's assumptions.

An **edge case** is a less common situation near the limits of expected behaviour. Examples include an empty search, a very long product title, two users saving the same item at the same time, or a recommendation request from a user with no activity history.

A **failure mode** describes how a feature can fail. A failure mode may come from invalid input, incorrect permissions, unavailable files, damaged data, network failure, deployment configuration, model uncertainty, or a programming defect.

The master analysis must help the student answer four questions for each important issue:

1. What could go wrong?
2. Why would it happen and what harm could it cause?
3. How should Market Mirror prevent, detect, or recover from it?
4. Which test proves the protection works?

## 3. Required deliverable after approval

The Planning stage shall create one project-wide master plan without deleting or rewriting previous context.

The plan shall contain:

- A prioritised risk register.
- A week-by-week edge-case catalogue covering all 16 weeks.
- Cross-cutting problems that affect several features.
- A proposed prevention, detection, and fallback strategy for each issue.
- Unit, integration, end-to-end, security, accessibility, AI-evaluation, and manual test plans where appropriate.
- Requirement and week traceability.
- A realistic division between required semester work and optional hardening work.
- Clear explanations appropriate for a high-school student.

The master plan will guide later feature specifications. It will not authorize implementation by itself.

## 4. Analysis unit and required fields

Every identified issue shall receive a stable identifier and the following information:

| Field | Required meaning |
|---|---|
| Issue ID | Stable identifier such as `AUTH-003` or `AI-PRICE-005` |
| Related week(s) | Roadmap week or cross-cutting scope |
| Feature | The affected user or system capability |
| Scenario | A concrete description of what goes wrong |
| Trigger | Input, event, timing, or condition that causes it |
| Impact | Effect on users, data, security, AI quality, or demonstration |
| Severity | Critical, High, Medium, or Low |
| Likelihood | Likely, Possible, or Unlikely for this university project |
| Priority | `P0`, `P1`, `P2`, or `P3` using Section 7 |
| Prevention | Design or validation that should stop the issue |
| Detection | Logging, assertion, monitoring, or user-visible signal |
| Recovery/fallback | Safe behaviour after prevention is insufficient |
| Test levels | Unit, integration, end-to-end, manual, security, accessibility, or ML evaluation |
| Detailed tests | Setup, action, expected result, and important negative assertions |
| SDD destination | Future specification or plan that must include the issue |
| MVP decision | Required, recommended, or future work |

## 5. Mandatory 16-week coverage

### QA-W01: Scope, environment, and foundation

The analysis shall cover:

- Missing or incorrect Python installation.
- Virtual-environment activation problems.
- Dependency installation and version conflicts.
- Incorrect working directory and missing files.
- Flask startup failures and port conflicts.
- Incorrect HTTP statuses, content types, and error handling.
- Broken static assets and narrow-screen layout.
- Git mistakes, ignored files, accidental secrets, and reproducibility.
- Differences between development and production behaviour.

### QA-W02: Database design and application structure

The analysis shall cover:

- Missing, duplicate, malformed, or orphaned records.
- Incorrect primary keys, foreign keys, uniqueness, nullability, and defaults.
- Price precision and invalid numeric values.
- Time-zone and timestamp consistency.
- Schema migration failures and partially applied migrations.
- Seed-data duplication and destructive seed behaviour.
- Delete, cascade, restrict, archive, and soft-delete decisions.
- Transaction rollback and database-lock behaviour.
- SQLite versus production PostgreSQL differences.

### QA-W03: Registration, login, and account security

The analysis shall cover:

- Empty, malformed, duplicate, case-variant, or extremely long credentials.
- Password strength, confirmation, hashing, and accidental exposure.
- Login enumeration, brute-force attempts, and generic error messages.
- Session expiration, stale sessions, logout, and multiple browser sessions.
- Open redirects through a `next` parameter.
- CSRF protection and unauthorized form submission.
- Logged-in users visiting logged-out-only pages.
- Profile privacy and future account deletion implications.

### QA-W04: Product listing CRUD

The analysis shall cover:

- Missing, blank, whitespace-only, malformed, or overlong listing fields.
- Zero, negative, extreme, and incorrectly formatted prices.
- Unsupported category or condition values.
- Editing or deleting another user's listing.
- Direct URL manipulation and hidden-field manipulation.
- Double submission, browser refresh, and repeated delete requests.
- Editing a deleted, archived, or sold listing.
- Two browser sessions editing the same listing.
- Loss of changes after validation failure.

### QA-W05: Product images and file handling

The analysis shall cover:

- Missing images and broken image references.
- Unsupported extensions, incorrect MIME types, disguised files, and corrupt images.
- Zero-byte, very large, extremely wide, or decompression-bomb images.
- Dangerous filenames, path traversal, duplicate names, and Unicode names.
- Image orientation, dimensions, compression, and accessibility text.
- Orphaned files after validation, replacement, or deletion.
- Storage failure, unavailable directories, and production ephemeral disks.
- Malicious content limitations and safe serving behaviour.

### QA-W06: Browse, search, filter, sort, and pagination

The analysis shall cover:

- Empty, whitespace, Unicode, punctuation, and very long queries.
- Search terms containing SQL-like or HTML-like text.
- No results, one result, and many results.
- Invalid, missing, duplicate, contradictory, or manipulated filter parameters.
- Minimum and maximum prices in the wrong order.
- Invalid sort options and deterministic tie-breaking.
- Page zero, negative pages, huge pages, and pages that become empty after deletion.
- Preserving active filters across pagination links.
- Sold, archived, or newly deleted products appearing incorrectly.
- Query performance and indexes as data grows.

### QA-W07: Product details, sellers, and event tracking

The analysis shall cover:

- Missing, deleted, archived, or sold products.
- Private seller information leaking into HTML.
- Sellers with no active listings.
- Broken images and missing optional fields.
- Owners viewing their own products.
- Bots, repeated refreshes, and inflated view counts.
- Anonymous event tracking and privacy decisions.
- Related-data query performance.

### QA-W08: Buyer-seller messaging

The analysis shall cover:

- Buyer messaging themselves.
- Unauthorized users guessing conversation identifiers.
- Empty, whitespace-only, enormous, or HTML/script messages.
- Repeated submission and duplicate messages.
- Messages sent after a product is deleted, archived, or sold.
- Conversation creation races and duplicate conversations.
- Ordering messages with equal timestamps.
- Read/unread state, multiple sessions, and stale pages.
- Abuse, spam, blocking, reporting, retention, and privacy limitations.

### QA-W09: Saved products and interaction events

The analysis shall cover:

- Saving the same product repeatedly or concurrently.
- Saving one's own, sold, archived, or deleted product.
- Unsaving an item that is not saved.
- Double clicks and retries.
- Unique constraints and race conditions.
- Behaviour when users or products are deleted.
- Event duplication, missing events, and inaccurate timestamps.
- Privacy and retention of behavioural data.

### QA-W10: Dashboard, refactoring, and usability

The analysis shall cover:

- Empty dashboards and first-time users.
- Incorrect counts or records belonging to another user.
- Large listing, saved-item, or conversation collections.
- Stale counts and deleted related data.
- Responsive layout, keyboard navigation, focus, contrast, labels, and alternative text.
- Refactoring that changes behaviour.
- Reused templates receiving missing variables.
- Clear loading, success, warning, empty, and error states.

### QA-W11: Test suite, data preparation, and AI baselines

The analysis shall cover:

- Tests that share state or depend on execution order.
- Tests accidentally using development or production data.
- Unstable, slow, or environment-dependent tests.
- Missing negative tests and false-positive assertions.
- Dataset duplicates, missing values, impossible values, inconsistent labels, and outliers.
- Train/test leakage and fitting preprocessing before splitting.
- Class imbalance and unrepresentative synthetic data.
- Random-seed and package-version reproducibility.
- Weak or incorrectly calculated baselines.
- Dataset licences, provenance, and documentation.

### QA-W12: Automatic product categorization

The analysis shall cover:

- Empty, extremely short, extremely long, misspelled, multilingual, or adversarial text.
- Categories missing from training data.
- Severe category imbalance.
- Low-confidence and conflicting predictions.
- Incorrect user-provided training labels.
- Vectorizer/model version mismatch.
- Missing or damaged model artifacts.
- Model drift as marketplace language changes.
- Accuracy hiding poor minority-category performance.
- User override and correction recording.

### QA-W13: Price suggestions

The analysis shall cover:

- Sparse categories and unseen category/condition combinations.
- Missing text and incomplete listings.
- Currency ambiguity and inconsistent units.
- Zero, negative, extreme, luxury, collectible, and incorrectly labelled prices.
- Outliers dominating estimates.
- Predictions below zero or far outside plausible ranges.
- Model performance that is worse than the category-median baseline.
- Fairness and misleading certainty.
- Missing model artifacts and safe fallback ranges.
- Evaluation by category rather than one overall score.

### QA-W14: Content-based recommendations

The analysis shall cover:

- New users and new products with no history.
- Users with only one interaction.
- Deleted, sold, archived, owned, or already viewed products in results.
- Duplicate and nearly identical recommendations.
- Empty vocabulary and products with little text.
- Popularity feedback loops and narrow filter bubbles.
- Recommendation diversity, freshness, and coverage.
- Manipulated listings designed to match many products.
- Privacy of behavioural profiles.
- Missing artifacts and recent/popular fallback behaviour.

### QA-W15: Integration, evaluation, and production preparation

The analysis shall cover:

- Model loading during startup and repeated loading per request.
- Missing, corrupt, incompatible, or outdated artifacts.
- AI timeouts, exceptions, and excessive memory use.
- Configuration mistakes and missing environment variables.
- Debug mode and secrets in production.
- Development/production database and filesystem differences.
- Logging without leaking credentials or private messages.
- Dependency vulnerabilities and incompatible upgrades.
- Migration, rollback, backup, and recovery procedures.
- End-to-end regression after integration.

### QA-W16: Deployment, documentation, and demonstration

The analysis shall cover:

- Failed builds, startup commands, migrations, and health checks.
- Temporary filesystems and missing uploaded images.
- Database connection limits and unavailable services.
- HTTPS, secure cookies, proxy headers, and production host configuration.
- Empty production data and unsafe demo accounts.
- Seed scripts that overwrite real data.
- Demonstration network failure and AI unpredictability.
- Broken setup documentation and machine-specific paths.
- Missing attribution, model metrics, limitations, and ethical discussion.
- Backup screenshots/video and a recoverable demo path.

## 6. Mandatory cross-cutting analysis

The master plan shall include dedicated sections for issues that affect several weeks:

### QA-X01: Input boundaries

- Empty values, whitespace, minimum/maximum length, Unicode, emojis, control characters, and malformed values.
- Numeric boundaries, rounding, precision, overflow, and locale-specific formatting.

### QA-X02: Authentication and authorization

- Anonymous, authenticated, owner, participant, and unauthorized-user behaviour.
- Direct URL access and server-side checks rather than hidden buttons alone.

### QA-X03: Data integrity and concurrency

- Duplicate submissions, simultaneous actions, stale updates, transactions, unique constraints, and rollback.

### QA-X04: Security and privacy

- CSRF, XSS, SQL injection assumptions, file risks, secret handling, session security, data exposure, abuse, and retention.

### QA-X05: Accessibility and responsive design

- Keyboard-only use, focus order, labels, landmarks, headings, contrast, alt text, error association, zoom, and 320-pixel layout.

### QA-X06: Performance and scalability

- Query counts, pagination, indexes, large datasets, file sizes, model-loading cost, response time, and memory use.

### QA-X07: Reliability and recovery

- Missing dependencies, unavailable database/storage/model, partial operations, retries, idempotency, backups, and safe fallbacks.

### QA-X08: AI quality and responsibility

- Baselines, leakage, imbalance, per-group metrics, uncertainty, explanations, user control, drift, reproducibility, and limitations.

### QA-X09: Observability

- Useful logs, health checks, failure signals, safe diagnostic context, and avoiding sensitive data in logs.

### QA-X10: SDD traceability

- Every required mitigation shall be routed into a future feature specification.
- Every approved behaviour shall map to planned tests before implementation.
- Future feature work shall not silently alter approved earlier behaviour.

## 7. Priority model

The master plan shall use this priority model:

| Priority | Meaning | Required treatment |
|---|---|---|
| `P0` | Could expose private data, allow unauthorized modification, destroy important data, or make the project unusable | Must be prevented and automatically tested before the affected feature is complete |
| `P1` | Breaks a core user journey, creates seriously incorrect AI output, or blocks deployment/demo | Must be addressed in the 16-week MVP with automated or repeatable validation |
| `P2` | Produces confusing behaviour, reduced accessibility, weak resilience, or inaccurate secondary behaviour | Should be addressed in the MVP when feasible; otherwise documented with fallback |
| `P3` | Rare polish issue or advanced production concern beyond the class scope | Document as future work unless inexpensive to handle safely |

Severity and likelihood must be considered separately. A rare data-exposure issue may still be `P0` because its impact is unacceptable.

## 8. Testing-plan requirements

For every `P0` and `P1` issue, the master plan shall define at least one specific repeatable test. `P2` and `P3` issues may use manual checks or documented future tests when automation is disproportionate.

Each detailed test shall state:

1. Test ID.
2. Related issue and requirement IDs.
3. Test level.
4. Preconditions and prepared data.
5. Exact action or request.
6. Expected status, page, database change, model output, or fallback.
7. Important behaviour that must **not** occur.
8. Cleanup or isolation requirements.

The combined plan shall include:

- Model and validation unit tests.
- Route and permission integration tests using Flask's test client.
- Database constraint and rollback tests.
- File-upload security and lifecycle tests.
- Search/filter/pagination combination tests.
- Cross-user authorization tests.
- Full buyer and seller journey tests.
- Keyboard, accessibility, and narrow-screen manual checks.
- AI data-validation, baseline, evaluation, artifact, and fallback tests.
- Deployment smoke tests and recovery rehearsals.

## 9. Solution-design requirements

Every proposed solution shall:

- Prefer simple, explainable techniques suitable for a university project.
- Use server-side validation and authorization for security decisions.
- Use database constraints as a second line of defence where appropriate.
- Preserve user-entered data after correctable validation errors where practical.
- Provide a safe fallback when AI or optional infrastructure is unavailable.
- Avoid claiming the AI is certain or objectively correct.
- Distinguish prevention, detection, and recovery rather than treating them as one action.
- State whether the solution belongs in the 16-week MVP or future production work.
- Avoid adding payments, shipping, real-time chat, or other features outside the approved marketplace scope.

## 10. Context-preservation requirements

The analysis and its future plan shall not:

- Delete, rename, or replace `MM-001`, `PLAN-001`, their tests, their Red/Green evidence, or their implementation.
- Rewrite the existing 16-week HTML roadmap.
- Change current application behaviour.
- Create application code or new pytest tests during the Specification or Planning stages.
- Treat the project-wide plan as approval to implement future features.

The analysis may reference previous documents and identify future changes, but each feature change must still receive its own approved specification and plan.

## 11. Acceptance criteria

### AC-QA-001: All weeks are covered

**Given** the master analysis has been produced  
**When** its coverage is reviewed  
**Then** every week from 1 through 16 has a dedicated problem and edge-case section  
**And** every listed roadmap feature appears in at least one issue.

### AC-QA-002: Issues are actionable

**Given** any `P0` or `P1` issue in the master plan  
**When** a student reads its entry  
**Then** the student can identify its trigger and impact  
**And** can describe the prevention, detection, recovery, and test approach.

### AC-QA-003: Tests are specific

**Given** any required automated test in the master plan  
**When** its description is reviewed  
**Then** it identifies setup, action, expected result, and forbidden result  
**And** it can later be converted into pytest without inventing the intended behaviour.

### AC-QA-004: Security and permissions are complete

**Given** every feature that reads or changes user-owned data  
**When** the cross-user scenarios are reviewed  
**Then** anonymous, authorized, and unauthorized behaviour is explicitly covered  
**And** server-side protection is required.

### AC-QA-005: AI failure is handled safely

**Given** categorization, price, or recommendation functionality  
**When** input is insufficient, the model is uncertain, or an artifact is unavailable  
**Then** the master plan defines a non-crashing fallback  
**And** defines a test for that fallback.

### AC-QA-006: The semester plan remains feasible

**Given** the complete risk catalogue  
**When** proposed solutions are prioritised  
**Then** required MVP protections are separated from optional production hardening  
**And** the project does not expand into payments, shipping, or unrelated features.

### AC-QA-007: Previous context is preserved

**Given** the existing project before this specification  
**When** the project-wide specification and plan are added  
**Then** all previous files remain present and unchanged except for separately approved status metadata  
**And** MM-001 continues to pass its existing tests.

### AC-QA-008: The material is teachable

**Given** a student with high-school-level programming knowledge  
**When** the student reads an issue and proposed response  
**Then** unfamiliar terms are explained  
**And** the reasoning is understandable without assuming professional software experience.

## 12. Non-goals

This project-wide specification does not authorize:

- Implementation of weeks 2–16.
- Creation of future feature tests.
- Changes to the completed MM-001 application.
- A claim that every theoretical software failure can be predicted.
- Full enterprise infrastructure, penetration testing, legal compliance certification, or payment security.
- Replacing feature-specific specifications with one large document.

The goal is broad, practical risk coverage appropriate for Market Mirror, not an impossible promise that no unknown defect can exist.

## 13. Completion and approval rule

This specification moved from **Draft** to **Approved** when the student explicitly asked for approval on 2026-10-25.

After approval, the next permitted action is the **Planning** stage: creation of the detailed project-wide problem, solution, priority, and test plan described here.

No future feature tests or application implementation are authorized by approval of this analysis specification.

