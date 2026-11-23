# PLAN-030 — Midnight & Gold Luxury Visual Redesign

Status: IMPLEMENTED — PLAN-030 approved and completed on 2026-11-08

Date: 2026-11-08 (Asia/Shanghai)

Approved specification: MM-030, explicitly approved by the user on 2026-11-08.

## 1. Outcome

Transform the complete Market Mirror interface into a coherent, luxurious
Midnight & Gold design while preserving every working marketplace feature.

The implementation will:

- replace the current light/adaptive palette with an intentional dark theme;
- use Cinzel for display headings and Montserrat for interface/body text;
- make product cards resemble restrained glass display cases;
- make eligible Add to Cart controls full-width gold action bars;
- make the desktop header sticky and the footer deep black;
- increase Explore-page space to create a calmer premium catalogue;
- restyle forms, panels, cart, seller pages, chat and AI controls consistently;
- retain usable local font fallbacks when Google Fonts are unavailable; and
- keep mobile, reduced-motion, forced-color and print experiences usable.

This is a presentation-only feature. No model, migration, database, route,
authorization, form action, AI provider or JavaScript behavior will change.

## 2. Beginner-friendly architecture

The redesign has three layers:

```text
base.html
  loads the fonts and supplies the shared header/main/footer structure
                         │
                         ▼
style.css
  defines reusable colors, fonts, spacing and component appearances
                         │
                         ▼
page templates
  add small descriptive classes so the shared styles know what each area is
```

CSS custom properties act like named design variables. For example, one
`--color-gold` value can be reused by buttons, links and borders. Changing the
variable changes the whole system without copying a hex value into every rule.

Templates continue to provide meaning and data. CSS changes appearance only.
Existing JavaScript continues to find the same IDs and data attributes.

## 3. Files and responsibilities

| File | Planned change | Reason |
| --- | --- | --- |
| `app/static/css/style.css` | Reorganize the existing stylesheet around approved tokens and restyle every shared component, state, breakpoint, preference and print view. | One coherent source prevents page-by-page color drift. |
| `app/templates/base.html` | Add Google Fonts preconnect/stylesheet links, update the stylesheet cache key and add presentation classes only if required. | Fonts and shared chrome belong in the base document. |
| `app/templates/macros.html` | Add presentation-only classes to reusable product-card elements and cart action controls without changing forms or links. | Every card receives the same glass-case and gold-bar treatment. |
| `app/templates/catalogue.html` | Add an Explore page wrapper/class and distinguish Recently Viewed from search results without renaming AJAX hooks. | Allows larger catalogue spacing without affecting every grid. |
| `app/templates/index.html` | Add presentation hooks only if the hero needs them beyond its existing classes. | Makes the landing page use the approved visual hierarchy. |
| `app/templates/product.html` | Add detail/action/related-section classes only where existing hooks are not descriptive enough. | Themes gallery, price, action groups and related products safely. |
| `app/templates/form.html` and `app/templates/_image_dropzone.html` | Add presentation hooks only where needed for premium form grouping. | Themes account/listing forms, upload states and AI vision controls. |
| `app/templates/cart.html` and `app/templates/order_success.html` | Add secondary/destructive/action classes where generic button styling would be ambiguous. | Keeps Checkout visually primary and Remove visually secondary. |
| `app/templates/dashboard.html`, `saved.html`, `seller.html`, `inbox.html` | Add minimal page/section classes where existing semantic hooks are insufficient. | Applies consistent premium panels and spacing. |
| `app/templates/conversation.html` | Add no behavioral hooks; only add a presentation class if the existing chat classes cannot express the theme. | MM-029 alignment, timestamps, polling and composer must remain intact. |
| `app/templates/_mobile_account_shortcuts.html` and `_shop_assistant.html` | Avoid changes unless a visual class is genuinely missing. | Their current IDs/classes already provide strong CSS hooks. |
| `app/templates/errors/404.html` and `errors/generic.html` | Normally no markup change because `.error-page` already exists. | Shared theme should style errors without duplication. |
| `tests/test_luxury_theme.py` | Add focused template, CSS token, component, accessibility-boundary and behavior-preservation contracts. | Provides the executable MM-030 specification before implementation. |
| `tests/030-red-verification.md` | Record intended failures against the unchanged site. | Preserves the SDD Red checkpoint. |
| `tests/030-green-verification.md` | Record focused, regression, full-suite and browser results. | Makes final claims auditable. |
| `tests/030-browser-checklist.md` | Record the repeatable visual/interaction story. | Separates actual browser evidence from static code inspection. |
| `docs/030-midnight-gold-design-guide.md` | Explain the design system and small student exercises in simple language. | Helps the student confidently present the redesign. |
| `docs/verification-matrix.md` | Add AC-030 traceability and honest browser limits. | Keeps the project evidence index current. |

The JavaScript, Python application modules, database models and migrations are
not planned for modification.

## 4. Theme token plan

At the top of `style.css`, replace the current generic light/adaptive values
with stable design tokens:

| Token purpose | Value |
| --- | --- |
| Main background | `#0A1128` |
| Deepest surface | `#05070D` |
| Raised surface/fallback | `#121B33` |
| Glass surface | `rgb(18 27 51 / 82%)` |
| Main gold | `#D4AF37` |
| Bright gold | `#F1D77A` |
| Dark gold | `#9A7514` |
| Main text | `#F7F3E8` |
| Secondary text | `#C9C1AE` |
| Gold-tinted line | `rgb(212 175 55 / 35%)` |
| Error text | `#FFB4B4` |
| Success text | `#A8E6B0` |

Additional named tokens will cover font stacks, maximum width, radii, shadows,
focus rings, spacing and transition duration. Derived colors may be introduced
only where measured contrast or a component state requires them.

The existing `prefers-color-scheme: dark` palette override will be removed or
reduced to rules that do not switch the main palette. Midnight & Gold is the
same intentional theme regardless of the operating-system color preference.

## 5. Typography and font-loading plan

`base.html` will load only the required font families and weights:

- Cinzel for the brand, H1, H2 and display-level titles;
- Montserrat for body text, navigation, labels, inputs and buttons;
- `display=swap` so fallback text appears immediately;
- preconnect to the Google stylesheet and font hosts; and
- `crossorigin` only on the font-file host where required.

CSS keeps complete fallbacks:

```text
"Cinzel", Georgia, "Times New Roman", serif
"Montserrat", Arial, Helvetica, sans-serif
```

No external JavaScript, analytics or marketplace information will be added to
the font URLs. If the internet is unavailable during a demo, the page will use
the fallback fonts and all functionality will continue.

## 6. Global layout and shared chrome

### 6.1 Page background and rhythm

- Apply the midnight color plus a very subtle non-animated gradient.
- Keep the existing readable content width.
- Increase section spacing using a small token scale and `clamp()`.
- Ensure long text, prices, filenames and usernames can wrap.
- Preserve bottom padding for the fixed mobile navigation.

### 6.2 Sticky top navigation

- Keep `.site-header` in normal document flow with `position: sticky` and
  `top: 0`.
- Use a nearly opaque dark surface, fine gold bottom border and controlled
  shadow.
- Use `backdrop-filter` as enhancement only; retain an opaque fallback.
- Give the brand Cinzel/gold styling.
- Give links off-white defaults, gold hover/focus states and a visible
  underline/border cue.
- Preserve Cart count, POST-only Sign out and the existing mobile breakpoint.
- Add appropriate `scroll-margin-top` to headed/anchored content if the sticky
  header could otherwise cover it.

### 6.3 Footer

- Use `#05070D`, a fine gold top border and muted-gold text.
- Increase vertical padding without pushing content behind mobile navigation.
- Reset to plain light print styling in `@media print`.

## 7. Product-card and Explore plan

### 7.1 Shared glass display cases

`.card` will receive:

- a solid `#121B33` fallback;
- a translucent navy surface as progressive enhancement;
- a fine gold-tinted border;
- a soft two-layer shadow;
- a restrained premium radius;
- safe overflow around the image; and
- a tiny pointer-only lift/border change that disappears for reduced motion.

Images keep their current dimensions, `object-fit`, links, alt text and
placeholder behavior. A subtle gold-tinted divider separates image and body.

Card titles use the display family, categories use spaced Montserrat, prices
use bright gold, and supporting text uses muted cream.

### 7.2 Gold Add to Cart bar

Only eligible `.cart-add-form` controls receive the primary card treatment:

- full available width;
- solid main-gold background and midnight text;
- bright-gold hover, dark-gold active and distinct disabled states;
- visible separated focus ring; and
- a confident bar shape with restrained radius.

The existing POST action, hidden `next`, CSRF value, availability checks and
cart count remain untouched.

### 7.3 Exclusive Explore spacing

The catalogue wrapper will scope Explore-specific rules:

- approximately `1.75rem–2rem` grid gaps at wide sizes;
- more space between Recently Viewed, heading, filters, live status,
  pagination and result cards;
- a premium raised filter panel;
- one-column reflow at narrow widths; and
- useful empty-results spacing without an empty decorative box.

The IDs `catalogue-search-form`, `product-results`, `product-grid`,
`product-pagination` and all spinner/feedback hooks remain exactly unchanged.

## 8. Controls, forms and feedback

### 8.1 Action hierarchy

- Primary buttons: gold background, midnight text.
- Secondary buttons: dark/transparent surface, gold border and gold text.
- Text buttons: visually quiet but still clearly interactive.
- Destructive/remove actions: secondary rather than gold-primary.
- Links: gold with bright-gold/underline interaction feedback.
- Disabled controls: legible, visibly inactive and `not-allowed` where
  appropriate.

All interactive states include keyboard focus, not just mouse hover.

### 8.2 Form fields

- Dark raised inputs with off-white content.
- Muted-cream placeholders and helper text.
- Gold-tinted borders and a clear gold/off-white focus ring.
- Readable browser autofill overrides.
- Native checkboxes/file controls remain operable.
- Existing validation associations and error text remain unchanged.

### 8.3 Upload and AI feedback

- Drag-over state becomes a bright-gold border with a subtle gold wash.
- Preview cards and remove controls stay legible on dark surfaces.
- AI vision checkbox, generated markers and spinner use theme tokens.
- Live-search spinner and result status use the same coherent accent.
- Reduced-motion mode removes spinner rotation while text status remains.

## 9. Page-family treatment

### 9.1 Product detail and gallery

- Use a premium dark panel structure without changing gallery HTML behavior.
- Give thumbnails gold-tinted borders and selected thumbnails a clear gold
  ring.
- Keep hover zoom, lightbox click, Escape/close/outside-click and image
  switching unchanged.
- Keep the lightbox near-black and restyle its close button as gold.
- Reuse product-card styling in You might also like.

### 9.2 Cart and order success

- Style cart rows and summary as raised premium surfaces.
- Make Checkout the gold primary action.
- Keep Remove secondary and unavailable items dashed/subdued.
- Use restrained gold rules in the receipt.
- Keep the no-real-payment classroom disclosure easy to notice.

### 9.3 Dashboard, Saved, seller and inbox

- Give stat blocks compact premium-tile styling.
- Keep active/unavailable saved products visually distinct.
- Give seller profile a refined header panel and gold divider.
- Keep Verified Seller wording/explanation and use an outlined gold badge.
- Increase inbox row spacing and dividers without changing private content or
  pagination.

### 9.4 Modern chat

- Keep outgoing bubbles right and incoming bubbles left.
- Use royal-midnight outgoing bubbles with a subtle gold edge.
- Use deep charcoal/navy incoming bubbles.
- Use readable cream/gold metadata and a gold Send button.
- Keep transcript scrolling, three-second polling, local times, history,
  read-state form, safe DOM appending and no-JavaScript form behavior intact.

### 9.5 AI Shop Assistant

- Use a gold launcher with midnight text.
- Use a glass/raised midnight panel with fine gold edge and shadow.
- Keep user/assistant messages distinct and disclosure text readable.
- Preserve focus management, Escape close, safe text insertion, Gemini calls
  and bottom-navigation offset.

## 10. Responsive, preference and accessibility plan

### 10.1 Responsive behavior

- Retain the approved 42rem mobile navigation breakpoint.
- Keep 44-pixel mobile targets and safe-area padding.
- Verify 320px and 360px widths without horizontal page scrolling.
- Verify 200% zoom reflow for filters, cards, cart, chat and forms.
- Keep the AI launcher/panel above the fixed mobile navigation.
- Ensure sticky/fixed elements never cover the last interactive control.

### 10.2 Motion

- Limit transitions to short color, border, shadow and tiny lift changes.
- Apply hover lift only within `(hover: hover) and (pointer: fine)`.
- Disable optional transitions/lifts/animations for
  `prefers-reduced-motion: reduce`.
- Do not add shimmer, sparkle, parallax or continuous decorative animation.

### 10.3 Contrast and focus

Automated tests will confirm required token values and state rules, while
browser/manual verification will measure representative computed color pairs.
Normal text targets WCAG AA 4.5:1. Focus must remain visible for navigation,
links, buttons, fields, gallery thumbnails, dialogs and chat/assistant controls.

### 10.4 Forced colors and print

- Add a small forced-colors section only where decorative borders/fills could
  hide a control boundary.
- Print removes gradients, dark fills, shadows and sticky/fixed positioning.
- Print hides nonessential mobile/AI/live controls while preserving meaningful
  product, order and message text.

## 11. Test-first plan

All focused tests will be written before `style.css` or application templates
are changed.

### 11.1 Focused tests — `tests/test_luxury_theme.py`

#### Theme tokens and typography

1. Assert every approved core color exists as a named CSS custom property.
2. Assert the main theme no longer depends on operating-system light/dark
   switching.
3. Assert body and display fallback stacks contain the approved local fonts.
4. Assert `base.html` uses HTTPS Google font/preconnect links with Cinzel,
   Montserrat and `display=swap`.
5. Assert no external script/analytics tag is introduced.

#### Shared chrome

6. Assert the site header has sticky/top/z-index/dark/gold-border rules.
7. Assert brand and navigation interaction/focus states use the display/gold
   system.
8. Assert the footer uses deepest background, gold treatment and print reset.
9. Assert main and anchor spacing accounts for sticky/fixed navigation.

#### Cards and Explore

10. Assert cards have solid fallback, glass enhancement, fine border and soft
    shadow.
11. Assert card hover enhancement is pointer-only and neutralized by reduced
    motion.
12. Assert price/category/title/image-divider rules use the approved hierarchy.
13. Assert cart-add form/button occupy the card width and define default,
    hover, active, disabled and focus states.
14. Assert Explore receives a scoped wide-screen gap of at least `1.75rem` and
    a narrow one-column reflow.
15. Render Explore and assert all AJAX IDs and live hooks remain present once.

#### Controls, forms and special components

16. Assert primary, secondary, text, disabled and focus-visible rules are
    visibly distinct.
17. Assert inputs, placeholders and autofill have dark-theme-readable rules.
18. Assert notices, errors, success text, upload drag state and both spinner
    types receive theme rules.
19. Assert gallery selected/close/lightbox, cart unavailable/summary, seller
    badge and order-receipt treatments exist.
20. Assert mobile navigation, account shortcuts, chat and Shop Assistant use
    the new tokens without generic unscoped message selectors.
21. Assert reduced-motion, hover-capability, forced-color and print sections
    exist and cover the affected components.

#### Markup and functional boundaries

22. Render representative anonymous, buyer and seller pages and assert no
    duplicate IDs, missing local static assets or invalid nested forms.
23. Snapshot every form's method, action and hidden security fields before and
    after the theme implementation.
24. Assert critical IDs/classes/data attributes for AJAX search, gallery,
    upload, chat, mobile navigation and Shop Assistant remain unchanged.
25. Assert no new inline handlers, external JavaScript, model/migration or
    route dependency is required.
26. Assert the stylesheet cache identifier is updated so browsers receive the
    new design after deployment/restart.

### 11.2 Existing regression suites

After focused Green, run the existing tests for:

- foundation/template/static asset loading;
- live AJAX search;
- cart and checkout;
- product image hover/lightbox and multi-image gallery;
- mobile navigation;
- drag-and-drop upload and AI vision;
- seller profile and recently viewed;
- modern chat rendering/assets/polling;
- AI Shop Assistant;
- marketplace authentication, authorization and CSRF hardening; and
- the complete pytest suite.

### 11.3 Red validation

After the focused test file is written:

1. collect it successfully;
2. run it against the unchanged application;
3. confirm failures describe missing MM-030 styles/links/hooks rather than
   broken fixtures or fragile whitespace assumptions;
4. record the command, counts and representative failures in
   `tests/030-red-verification.md`;
5. keep preservation tests Green where the old app already meets them; and
6. begin implementation only after valid Red evidence exists.

Static tests will inspect durable semantic contracts, not exact indentation or
the full textual order of every CSS declaration.

## 12. Implementation sequence after valid Red

1. Add/revise CSS token and font-stack declarations.
2. Add Google Font/preconnect links and update the stylesheet cache key.
3. Restyle base typography, background, panels, shared layout, header and
   footer.
4. Restyle links, buttons, forms, feedback, spinners and disabled/focus states.
5. Add minimal template classes for shared cards and Explore scoping.
6. Implement card glass fallback/enhancement, gold action bar and catalogue
   spacing.
7. Theme product/gallery/lightbox, cart/order, seller/dashboard/saved/inbox.
8. Theme modern chat and AI Shop Assistant using fully scoped selectors.
9. Complete mobile, 320px, zoom, hover, reduced-motion, forced-color and print
   rules.
10. Run the focused suite after each layer and fix only in-scope regressions.
11. Run related suites, then the complete suite.
12. Perform isolated browser verification and document evidence.

This order builds from shared foundations to special components. It reduces
the chance that a late generic rule overrides chat bubbles or the AI assistant.

## 13. Browser verification plan

Use the local app and fictional/test accounts; do not modify real listing or
message data merely to test the theme.

### 13.1 Desktop story

Verify Home, Explore, one product, Sell/Edit form, Dashboard, seller profile,
Saved, inbox/conversation, Cart and order success:

- body background and text are Midnight & Gold and readable;
- Cinzel/Montserrat are computed when online and fallbacks work when fonts are
  blocked;
- the header remains sticky while scrolling and never hides focused content;
- product cards look consistent and Add to Cart is a solid gold bar;
- Explore spacing feels deliberate and AJAX results do not lose styling;
- form hover/focus/error/disabled/autofill states remain clear;
- gallery/lightbox, cart, chat polling and assistant still operate;
- footer is deep black/gold; and
- the browser console contains no application errors.

### 13.2 Mobile and zoom story

At 320px, 360px and a supported 200% zoom level verify:

- no horizontal page scroll;
- desktop links hide and the five-item bottom navigation remains usable;
- single-column cards and filters have comfortable spacing;
- cart, product detail, form and chat composer reflow;
- last controls remain above the bottom navigation;
- Shop Assistant opens completely on screen; and
- long product/user/message text wraps without clipping.

### 13.3 Preference/failure story

Where browser controls support it:

- reduced motion removes lifts/transitions/rotating visual-only effects;
- keyboard-only navigation reveals every focus indicator;
- hover changes are absent on touch-only emulation;
- forced colors leaves operable control boundaries;
- print preview is light, readable and omits fixed interactive chrome; and
- blocking Google Fonts produces a usable fallback with no layout failure.

## 14. Acceptance-criteria traceability

| MM-030 criteria | Main evidence |
| --- | --- |
| AC-030-01 | Token/static tests, representative computed-color browser checks |
| AC-030-02 | Font-link/fallback tests and online/blocked-font browser story |
| AC-030-03 | Header CSS tests plus desktop/mobile scroll and keyboard checks |
| AC-030-04 | Footer CSS/static tests and desktop/print check |
| AC-030-05 | Card fallback/enhancement tests and Explore/product browser views |
| AC-030-06 | Card-form preservation tests and enabled/disabled browser states |
| AC-030-07 | AJAX-hook tests, live-search regressions and spacing browser check |
| AC-030-08 | Control/form state tests and representative contrast/focus checks |
| AC-030-09 | Representative render matrix and all-page browser story |
| AC-030-10 | MM-029 regressions and live conversation browser check |
| AC-030-11 | Upload/search/gallery/assistant regressions and browser interactions |
| AC-030-12 | 320/360/200%-zoom browser story and responsive static contracts |
| AC-030-13 | Preference sections plus supported reduced-motion/print checks |
| AC-030-14 | Form/hook snapshots, no Python/schema diff and full regressions |
| AC-030-15 | Focused, related, full pytest and documented browser evidence |

## 15. Edge-case matrix

| Case | Expected result |
| --- | --- |
| Google Fonts unavailable | Local serif/sans fallbacks appear; features still work |
| Very long title/username | Wraps within card, navigation or profile without overflow |
| Product has no image | Placeholder remains visible on a dark neutral surface |
| Add to Cart unavailable | No false gold action appears; existing eligibility text remains |
| Empty Explore results | Helpful message remains visible; no giant empty display case |
| AJAX replaces results | New cards immediately inherit all styles without JS changes |
| Browser lacks backdrop blur | Solid raised-surface card/panel remains attractive and readable |
| Keyboard-only user | Every interactive item has visible focus, not hover-only feedback |
| Touch device | No essential state depends on hover; no stuck lift effect |
| Reduced motion enabled | Optional lifts/transitions/spins stop; status text remains |
| Browser autofill | Filled values remain readable against a dark field |
| Disabled/processing control | Clearly inactive and legible, not confused with primary gold |
| 320px viewport | One-column reflow and no page-wide horizontal scrolling |
| 200% zoom | Navigation, cart, chat and forms remain reachable |
| Mobile nav + assistant | Launcher/panel stays above navigation and final controls stay reachable |
| Long chat message | Wraps inside correct-side bubble; polling/safe rendering unchanged |
| Print order/chat/product | Dark decoration removed; meaningful text prints clearly |
| Forced colors | Native/system outlines and boundaries remain operable |

## 16. Risks and controls

| Risk | Control |
| --- | --- |
| Gold text has weak contrast | Use gold selectively, measure representative pairs and prefer off-white body text |
| Generic CSS breaks chat/assistant | Use component-prefixed selectors and dedicated regression suites |
| Sticky header covers content | Preserve flow, add scroll margin and test anchor/focus behavior |
| Glass blur fails or performs poorly | Solid fallback first; enhancement only where supported |
| External fonts fail during presentation | `display=swap` and full local fallback stacks |
| Cache keeps old CSS | Update stylesheet version in `base.html` |
| Template class edit breaks AJAX/JS | Snapshot and assert all critical IDs/data hooks before/after |
| Button restyle disguises destructive action | Explicit primary/secondary/remove hierarchy |
| Dark theme creates unreadable autofill/placeholder | Add targeted field/autofill rules and browser check |
| Mobile fixed elements overlap | Preserve safe-area padding and verify bottom offsets at narrow widths |
| Static tests overclaim visual quality | Separate static contracts from computed-style and browser evidence |

## 17. Rollback boundary

MM-030 can be rolled back without data conversion:

1. restore the previous stylesheet;
2. remove the Google font/preconnect links and restore the old cache key;
3. remove only the presentation classes added by MM-030; and
4. remove MM-030 tests/docs if the feature is abandoned.

No database rollback, migration, message restoration or cart/order conversion
would be required.

## 18. Definition of done

PLAN-030 will be complete only when:

1. valid focused Red evidence predates implementation;
2. every approved color/font/component requirement is represented by a durable
   test or honest browser check;
3. product cards, gold cart bar, sticky header, footer and Explore spacing meet
   the approved design;
4. contrast, focus, responsive, reduced-motion, forced-color and print checks
   pass to the supported extent;
5. AJAX, cart, gallery, upload, mobile navigation, chat and AI assistant
   regressions remain Green;
6. all form actions, CSRF fields, IDs and behavioral hooks remain unchanged;
7. no Python route/model/migration/business-logic change is introduced;
8. focused, related and complete pytest suites pass;
9. isolated browser verification reports no application console error;
10. verification documents and the matrix record exact evidence and limits;
11. the beginner guide explains the design system and small practice tasks; and
12. specification and plan statuses accurately reflect completion.

## 19. SDD checkpoint and approval record

MM-030 was explicitly approved by the user on 2026-11-08.

PLAN-030 was explicitly approved by the user on 2026-11-08. Fourteen focused
tests were collected and validated Red before implementation. The completed
redesign passed 14 focused tests, 325 related tests, a 603-test complete run,
46 final affected tests after a browser-found mobile correction, package
consistency, and desktop/mobile browser verification with no console errors.
