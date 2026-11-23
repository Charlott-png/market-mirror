# MM-025 isolated browser checklist

Status: TEST CONTRACT — written before implementation

Use only a temporary fixture database and generated/demo product images. Never
run purchasing steps against the student's real catalogue.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | Sign in as the fixture buyer and add two products from different sellers. | Cart count is 2; Saved state is unchanged. |
| 2 | Open Cart on desktop. | Both products, exact full total, and the local/no-real-payment explanation appear. |
| 3 | Activate Checkout using only the keyboard. | One POST is followed by a 303 redirect. |
| 4 | Inspect the destination. | One H1 says “Thank you for your purchase”; order number, item snapshots, sellers, prices, exact total and no-real-payment note appear. |
| 5 | Refresh twice. | Same receipt remains; no duplicate order is created. |
| 6 | Return to Cart and Explore. | Cart/count are empty/zero and sold products are absent from active discovery. |
| 7 | Sign in as each seller. | Their management page labels the purchased listing Sold. |
| 8 | Sign in as another buyer who had the same product in Cart. | Generic unavailable row appears; private receipt/product details are not leaked. |
| 9 | Paste the first buyer's receipt URL. | HTTP 404 presentation, with no receipt content. |
| 10 | Repeat at a 360 px viewport and 200% zoom where supported. | No horizontal page overflow; receipt text and controls wrap and remain usable. |
| 11 | Disable JavaScript and repeat a fresh fixture checkout. | Server-rendered checkout and receipt still work. |
| 12 | Navigate with Tab/Shift+Tab and activate controls with Enter/Space. | Visible focus and logical order are preserved. |

Capture desktop and narrow screenshots only after automated tests are Green.
Record limitations honestly if browser controls cannot test actual zoom or
JavaScript disabling.
