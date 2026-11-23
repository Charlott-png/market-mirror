# MM-026 isolated browser checklist

Status: TEST CONTRACT — written before implementation

Implementation note (2026-11-07): the real migrated one-image product and its
open/close lightbox path passed a loopback browser smoke check. The complete
five-photo picker/switching/narrow-screen exercise below remains a student demo
rehearsal; isolated automated contracts cover its data and security behavior.

Use only generated product-angle images and a temporary database/uploads folder.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | Sign in as the fictional seller and open Sell. | Multiple picker, 5-photo, 5-MiB each, 25-MiB total and first-is-cover instructions appear. |
| 2 | Choose five generated angle files. | Five ordered local previews appear; first says Cover photo; no listing/server upload happens yet. |
| 3 | Replace selection with six files, then a group containing one corrupt file. | Complete preview group clears and useful feedback appears; no silent truncation. |
| 4 | Re-select five valid files and Save. | One product and five ordered gallery rows/files are created. |
| 5 | Inspect owner preview/product detail. | Five thumbnail links appear and cover is the initial large image. |
| 6 | Keyboard-activate thumbnail 3. | Main image, alt/link, current marker, status and lightbox source change to photo 3; focus stays on thumbnail. |
| 7 | Open and close the lightbox. | It displays photo 3 and retains Close/Escape/backdrop/focus/scroll behavior. |
| 8 | Test at 360px and, if available, 200% zoom/dark/reduced-motion. | No page overflow; thumbnails/previews/focus remain readable. |
| 9 | Edit text with no selected files. | Existing five-photo gallery remains byte/row identical. |
| 10 | Select two replacement images and save. | New two-image gallery/cover appears together; old fixture files are cleaned after commit. |
| 11 | View public cards. | Only the new cover appears, never the whole gallery. |
| 12 | Archive the listing and use owner/stranger sessions. | Owner may view all gallery media; stranger receives 404. |
| 13 | Disable JavaScript where supported. | Native multiple input submits normally; thumbnail media links remain useful. |
| 14 | Inspect console and unrelated pages. | No new errors or gallery UI leakage. |

Actual drag/drop is attempted only if the available browser controls safely
support local file dragging. Record picker-only coverage honestly otherwise.
