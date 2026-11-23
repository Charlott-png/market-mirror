# MM-021 browser acceptance checklist

Status: defined before implementation

This checklist checks the behavior that pytest cannot fully measure, such as the
real size of a tap target and whether a fixed bar covers the end of a page. All
mutating checks use a temporary test database, never the user's local data.

| # | Browser check | Expected result |
| --- | --- | --- |
| 1 | Open Home at 1000×800. | Main navigation is visible. Mobile navigation and Account shortcuts are hidden. The desktop Cart count and Sign out remain unchanged. |
| 2 | Compare 673px and 672px viewport widths with a 16px root size. | Desktop mode is used at 673px. At exactly 672px (42rem), the desktop links disappear, the brand stays visible, and the bottom bar appears. |
| 3 | Open Home at 320×800. | The bar shows exactly Home, Explore, Sell, Messages, Profile in that order. Labels remain visible and the page has no horizontal scrolling. |
| 4 | Inspect computed layout at 320px. | Each item is at least 44px high, columns have equal width, the bar touches the viewport bottom, and `scrollWidth <= innerWidth`. |
| 5 | Use a long Explore result list, run an AJAX search, then scroll to the very end. | Search still updates normally. The final card, pagination, footer, and controls can scroll completely above the fixed bar. |
| 6 | While signed out, open Home and Explore, then select Sell, Messages, and Profile. | Public pages open. Protected links safely redirect to Sign in with a local intended destination and make no data changes. |
| 7 | Sign in to the temporary fixture and visit all five destinations plus product/seller/detail/grouped pages. | Each rendered page has no more than one active item, and the approved endpoint group is active with both color and a non-color cue. |
| 8 | Open Profile with a two-digit cart count. | Account shortcuts show Dashboard, Saved, Cart with the correct count, and a Sign out button. They do not appear on Login, Register, or listing forms. |
| 9 | Navigate the bar and Profile shortcuts using Tab and Shift+Tab. | Focus follows document order, is clearly visible, is not clipped, and every action works without a mouse. |
| 10 | Open a product image lightbox on mobile. | The modal covers the navigation because the browser top layer remains above the fixed bar. Closing it restores the page. |
| 11 | Block or remove `market.js`, then reload. | All five links, active state, Profile shortcuts, and secure server forms still work because navigation does not depend on JavaScript. |
| 12 | Check a short landscape viewport and 200% zoom if browser tooling permits. | Labels wrap instead of disappearing; there is no page-width overflow or covered final content. |
| 13 | Check light and dark themes. | Text, active state, focus indicator, border, and background retain readable contrast through existing theme variables. |
| 14 | Emulate print if tooling permits. | Mobile navigation and Account shortcuts are absent, and no blank bottom clearance remains. |
| 15 | Inspect the browser console and save desktop/mobile evidence screenshots. | No new errors or warnings are produced by MM-021. Evidence shows the desktop and 320px mobile layouts. |

The valid logout check is performed last because it intentionally ends the
temporary session. A missing browser capability is recorded honestly in the
green verification instead of being claimed as tested.
