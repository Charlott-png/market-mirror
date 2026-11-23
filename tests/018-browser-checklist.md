# MM-018 browser checklist — defined before implementation

Use isolated fixtures for counts and edge cases; do not change real users/listings.

1. Follow a seller link from a product page and verify requested username, full join date, biography, seller-owned active cards and browse link.
2. Compare three-active and four-active fixture sellers. Badge must appear only for four, beside the username, with a visible activity-only explanation.
3. Navigate both pages of a 21-item seller: correct seller links, 20 then 1 card, total 21 and badge on both pages.
4. Empty seller retains header/date and a helpful message. Missing photos retain placeholders.
5. Test desktop and 320px width, long usernames and multiline biography; no horizontal overflow. Check light/dark preference and actual 200% zoom if supported; mark unavailable checks honestly.
6. Use Tab/Enter for seller, browse, product and pagination links; focus must be visible.
7. Confirm profile works without JavaScript, using a disclosed controlled no-script fixture if needed.
8. Follow a profile product link, open and close the existing MM-017 lightbox.
9. Inspect browser errors and save desktop/narrow screenshots. Restore temporary viewport overrides and stop disposable fixture servers.
