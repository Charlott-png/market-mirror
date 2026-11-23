# MM-019 browser checklist — defined before implementation

Use an isolated loopback-only fixture with temporary database/uploads and ordinary authentication pages. Never mutate the real local demo database.

1. Sign in as an isolated buyer through the normal login form.
2. Add two products from catalogue cards with keyboard controls. Verify accessible notices and header count 0 → 1 → 2.
3. Repeat Add for one item; verify one row and unchanged count.
4. Add from a public seller profile and Saved page. Confirm private owner-dashboard cards have no Add control.
5. Open Cart and verify pictures/placeholders, product/seller links, newest-added order, full count, exact USD subtotal and current-price note.
6. Remove one product; verify count/subtotal update. A repeated remove remains safe.
7. Use isolated status manipulation to make one cart product sold/archived. Verify generic unavailable content, no private canary, row still counted, subtotal exclusion and Checkout blocked.
8. Restore an all-eligible fixture, click Checkout and verify the visible “No payment was taken and no order was created” message. Refresh/revisit Cart and confirm rows/count remain.
9. Sign in as a second isolated buyer. Verify an independent zero count/cart and no first-buyer content.
10. Check desktop and 320 CSS-pixel viewport with a long product title and two-digit count; no horizontal page overflow.
11. Use Tab/Enter through Cart navigation, Add, Browse, product/seller links, Remove and Checkout with visible focus.
12. Run a controlled no-script fixture and repeat core Add, Remove and Checkout operations.
13. Smoke-check product detail/MM-017 lightbox and MM-018 seller-profile navigation.
14. Inspect browser warnings/errors. Save desktop and narrow screenshots showing the nav count, rows and summary.
15. Attempt actual 200% zoom and dark mode only if controls expose them; record unavailable controls honestly and never call viewport resizing a zoom test.

Stop the fixture server and restore temporary browser viewport settings after evidence capture.
