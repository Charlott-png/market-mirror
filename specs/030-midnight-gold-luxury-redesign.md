# MM-030 — Midnight & Gold Luxury Visual Redesign

Status: IMPLEMENTED — MM-030 and PLAN-030 approved; verification complete

Date: 2026-11-08 (Asia/Shanghai)

## 1. Purpose

Redesign the complete Market Mirror interface with a luxurious, majestic and
high-end visual identity associated with wealth, confidence and exclusivity.

The approved direction is **Midnight & Gold**:

- deep midnight navy and near-black page backgrounds;
- metallic gold for actions, links and important accents;
- crisp warm off-white text;
- elegant serif display typography;
- clean sans-serif body typography;
- glass-display-case product cards;
- dark sticky navigation with gold interaction states;
- a deep-black footer with gold text; and
- more generous catalogue spacing.

This specification changes presentation only. It must not change marketplace
permissions, data, routes, form actions, JavaScript behavior, AI behavior,
message polling, checkout rules, database schema or stored content.

## 2. Relationship to existing features

MM-030 visually restyles all existing features, including:

- Home and error pages;
- Explore, AJAX search, filters and pagination;
- product cards, product details, gallery and lightbox;
- account, registration and listing forms;
- drag-and-drop upload and AI vision controls;
- seller profiles and badges;
- Dashboard, Saved and Recently Viewed;
- inbox and the MM-029 modern chat;
- Cart, checkout and order success;
- mobile top/bottom/account navigation; and
- the floating AI Shop Assistant.

All earlier functional specifications remain authoritative. When an earlier
specification names an old color, MM-030 may replace that color but not the
control's meaning, position, label, state or accessible behavior. For example,
MM-029 chat bubbles retain right/left ownership and readable contrast while
receiving Midnight & Gold styling.

## 3. Design principles

### 3.1 Luxurious, not noisy

The interface uses restraint: deep surfaces, fine gold borders, measured
shadows and generous space. Gold identifies important actions and details; it
must not cover every surface or make the app resemble a bright yellow theme.

### 3.2 Readability before decoration

Off-white body text remains easy to read. Gold is never used as small text on
an insufficiently contrasting light surface. Controls retain clear boundaries,
focus indicators and disabled states.

### 3.3 One coherent system

Colors, fonts, radii, spacing, shadows and control states are defined as CSS
custom properties. Pages reuse these tokens rather than inventing one-off
values.

### 3.4 Progressive enhancement

External fonts improve the look when available, but the application remains
usable offline with local serif/sans-serif fallback stacks. Glass effects use
ordinary opaque/dark fallbacks before optional `backdrop-filter` enhancement.

## 4. Approved color system

The default application theme is dark. It no longer switches the entire design
to a light palette based on operating-system preference.

### 4.1 Core tokens

| Purpose | Approved value | Use |
| --- | --- | --- |
| Midnight background | `#0A1128` | Main page background |
| Deepest background | `#05070D` | Footer and strongest dark sections |
| Raised surface | `#121B33` | Panels, forms and solid fallbacks |
| Glass surface | `rgb(18 27 51 / 82%)` | Product cards and elevated widgets |
| Gold | `#D4AF37` | Primary actions, links and major accents |
| Bright gold | `#F1D77A` | Hover/focus highlights and small emphasis |
| Dark gold | `#9A7514` | Pressed state and subtle gold depth |
| Off-white | `#F7F3E8` | Main text |
| Muted cream | `#C9C1AE` | Secondary text and helper copy |
| Gold line | `rgb(212 175 55 / 35%)` | Fine borders and dividers |
| Error | `#FFB4B4` | Error text on dark backgrounds |
| Success | `#A8E6B0` | Success feedback where needed |

Minor derived tokens may be added only to meet contrast, component state or
overlay requirements. They must remain visibly part of the Midnight & Gold
family.

### 4.2 Background treatment

The body uses `#0A1128` plus a very subtle non-animated radial/linear gradient
that creates depth without reducing text contrast. The gradient must not cause
banding that obscures content and must print as a plain readable background.

### 4.3 Gold usage

- Primary buttons use gold backgrounds and midnight text.
- Links use gold text, with bright-gold hover/focus states.
- Section accents may use fine gold borders or rules.
- Prices may use bright gold because they are key marketplace information.
- Gold is not used behind off-white text when contrast is insufficient.
- Destructive or secondary actions remain visually distinct from primary gold
  actions.

## 5. Typography

### 5.1 Font families

Use Google Fonts through `<link>` elements in the document head:

- **Cinzel** for the brand, H1, H2 and display titles; and
- **Montserrat** for body text, labels, inputs, buttons and navigation.

Use `display=swap` so text appears immediately with fallback fonts. Limit
requested weights to the actual design needs rather than loading every weight.

### 5.2 Fallbacks

```text
Display: "Cinzel", Georgia, "Times New Roman", serif
Body: "Montserrat", Arial, Helvetica, sans-serif
```

If Google Fonts is unavailable, the page must remain readable and structurally
stable with these fallbacks.

### 5.3 Hierarchy

- Brand and H1 use strong Cinzel weight with modest letter spacing.
- H2/H3 use Cinzel at smaller sizes without all-uppercase paragraphs.
- Body text uses Montserrat with comfortable line height.
- Eyebrows/tags may use uppercase Montserrat with increased letter spacing.
- Buttons use Montserrat and a strong weight for clarity.
- Very long titles and usernames continue to wrap.

## 6. Global page structure

### 6.1 Main content

- Preserve the existing maximum readable width.
- Increase vertical rhythm around major sections.
- Keep main content clear of sticky desktop navigation and fixed mobile
  navigation.
- Use fluid spacing through `clamp()` where helpful.

### 6.2 Panels

Panels use a raised midnight surface, fine gold-tinted border, restrained
radius and subtle shadow. They are quieter than product cards so product
inventory remains the visual focus.

### 6.3 Notices and errors

- Notices use a gold left border and dark raised background.
- Errors use the approved light-red text and a readable dark error surface.
- Success messages use the approved success color without depending on color
  alone.
- Existing roles and live-region behavior remain unchanged.

## 7. Sticky top navigation

The desktop/top site header must:

- use a dark, nearly opaque midnight surface;
- remain sticky at the top with `top: 0` and an appropriate z-index;
- use a subtle backdrop blur when supported, with a solid fallback;
- include a fine gold-tinted bottom border and controlled shadow;
- keep the Market Mirror brand in Cinzel with gold coloring;
- keep navigation links off-white/gold and large enough to select;
- show gold underline/border and bright-gold text on hover/focus;
- preserve visible keyboard focus;
- retain current Cart count and Sign out behavior; and
- never cover anchored headings or focused controls.

The sticky header height must remain compatible with desktop and narrow
screens. At the existing mobile breakpoint, desktop links remain hidden and
the mobile navigation remains the primary navigation.

## 8. Mobile navigation and account shortcuts

The fixed mobile bottom navigation must inherit Midnight & Gold styling:

- near-black/midnight background;
- gold-tinted top border and shadow;
- muted-cream inactive labels/icons;
- bright gold current-page state;
- a visible gold focus outline;
- existing safe-area padding and 44-pixel targets; and
- no overlap with forms, chat composer or Shop Assistant.

Mobile account shortcut cards and the cart-count badge use the same tokens.
The redesign must not reveal new private counts or change navigation grouping.

## 9. Footer

The footer uses:

- deepest black `#05070D` background;
- a thin gold top border;
- gold or muted-gold text;
- generous vertical padding; and
- the existing class-project statement.

It must remain readable above the mobile bottom-navigation padding and in
print, where dark backgrounds are removed.

## 10. Product cards as glass display cases

Every reusable product card must resemble a premium glass display case.

### 10.1 Card surface

- Solid fallback: raised midnight `#121B33`.
- Enhanced surface: subtly translucent dark navy.
- Fine gold-tinted border, not a thick bright frame.
- Soft layered shadow with no harsh black rectangle.
- Slightly larger radius than form inputs.
- `backdrop-filter: blur(...)` only inside a support query or with a complete
  fallback.
- No animation required to understand or operate the card.

### 10.2 Images

- Images keep their existing aspect ratio and object-fit behavior.
- Use a dark neutral image background.
- Add a subtle divider between photo and card body.
- Existing placeholders, alt text and links remain unchanged.
- Optional hover lift/shine must be very small, pointer-only and disabled for
  reduced-motion users.

### 10.3 Card content

- Category tag uses muted cream/gold.
- Title uses readable off-white display type.
- Price uses bright gold.
- Seller/status text uses off-white or muted cream.
- Links remain visibly interactive without relying only on hover.

### 10.4 Add to Cart gold bar

On cards where Add to Cart is allowed:

- the form/button fills the available card-body width;
- the button uses a solid `#D4AF37` background;
- text uses deep midnight for contrast;
- it has a confident rectangular/pill-bar shape with restrained radius;
- hover uses bright gold;
- active uses dark gold;
- focus uses a clearly separated bright/off-white outline; and
- loading/disabled states remain distinguishable.

The button's POST action, CSRF token, cart count and eligibility rules must not
change.

## 11. Explore catalogue exclusivity and spacing

The Explore page receives a page-level styling hook without changing its
search or AJAX structure.

- Increase product-grid gaps to approximately `1.75rem–2rem` on wide screens.
- Increase spacing between search controls, feedback, result count and cards.
- Keep one-column reflow at narrow widths.
- Preserve the AJAX IDs: `catalogue-search-form`, `product-results`,
  `product-grid`, `product-pagination` and feedback/spinner hooks.
- Filters use a premium raised panel with dark inputs and gold focus borders.
- Recently Viewed remains visually separate from search results.
- Empty results remain understandable and do not leave a decorative blank area.

Other grids may use improved spacing, but Explore should feel the most
deliberate and gallery-like.

## 12. Buttons, links and controls

### 12.1 Primary buttons

- Gold background, midnight text and gold border.
- Strong Montserrat weight.
- Bright-gold hover and dark-gold active states.
- Visible off-white/bright-gold focus ring separated from the button edge.
- Minimum target size remains at least 44 pixels where previously required.

### 12.2 Secondary buttons

- Transparent/raised-midnight background.
- Gold border and gold text.
- Subtle gold-tinted background on hover.
- Must not look identical to primary actions.

### 12.3 Text buttons and links

- Gold by default; bright gold with underline or border on interaction.
- Sign out remains visually lighter than primary marketplace actions.
- Visited links remain distinguishable without becoming low contrast.

### 12.4 Disabled controls

Disabled controls use reduced contrast and a `not-allowed` cursor but remain
legible. They must never look active merely because the default gold token is
present.

## 13. Forms and inputs

- Inputs, selects and textareas use deep raised surfaces and off-white text.
- Borders use muted cream/gold-tinted lines.
- Focus uses a strong gold outline plus sufficient offset.
- Placeholder/helper text remains readable but visually secondary.
- Validation errors retain semantic associations and visible text.
- Browser autofill must not produce unreadable light text/light background.
- Checkbox and file controls remain native/usable.
- Drag-and-drop highlight becomes a bright-gold border and subtle gold wash.
- AI suggestion markers/spinners adopt gold accents without altering behavior.

## 14. Product detail and image experiences

- Product detail panels receive the premium raised/glass surface.
- Main images and thumbnails receive subtle gold-tinted borders.
- Selected thumbnail uses a clear gold ring.
- The image hover zoom and lightbox behavior remain unchanged.
- The lightbox stays near-black for image focus; its close button uses a gold
  action treatment with readable text.
- Price and category receive gold emphasis.
- Contact, Save, Edit and status controls retain their existing hierarchy and
  form behavior.
- Related-product cards reuse the shared display-case card.

## 15. Cart, checkout and order success

- Cart items and summary use premium dark surfaces and gold price emphasis.
- Checkout is a primary gold action.
- Remove actions use secondary styling so they are not confused with Checkout.
- Unavailable items retain a visibly different dashed/subdued treatment.
- Order receipt uses restrained gold rules and a formal document-like layout.
- The classroom no-payment disclosure remains prominent and readable.

No checkout or order behavior changes.

## 16. Seller, Dashboard, Saved and inbox

- Seller profile header uses a refined midnight panel and gold divider.
- Verified Seller remains an activity badge, not an identity-verification claim;
  it receives gold outline styling while its explanation remains visible.
- Dashboard stat panels resemble compact premium tiles and retain exact links.
- Saved product and unavailable states remain distinct.
- Inbox conversation entries gain spacing/dividers without changing pagination
  or private content.

## 17. Modern chat integration

MM-029 behavior remains unchanged.

- Outgoing bubbles remain right-aligned and incoming left-aligned.
- Outgoing bubbles use a rich royal-midnight blue surface with a subtle gold
  edge rather than becoming an unreadable bright decoration.
- Incoming bubbles use deep charcoal/navy.
- Sender labels and timestamps use gold/muted cream with sufficient contrast.
- The sticky composer uses a midnight surface and gold Send action.
- Polling, local timestamps, safe text nodes, scroll behavior, history links,
  read form and no-JavaScript fallback remain unchanged.

## 18. AI Shop Assistant integration

- Floating launcher becomes a gold primary control with midnight text.
- Panel uses raised/glass midnight styling and gold border/shadow.
- User/assistant messages remain visually distinct.
- Product recommendations reuse the theme without pretending to be product
  catalogue cards.
- Disclosure/helper text remains readable and is not hidden by decoration.
- Mobile offset, focus management, Escape behavior and safe DOM rendering remain
  unchanged.

## 19. Motion and interaction

Optional motion is limited to short, subtle transitions for color, border,
shadow or a tiny card lift.

- No continuous decorative animation.
- No parallax, flashing, shimmer loop or gold sparkle effect.
- `prefers-reduced-motion: reduce` removes lifts/transitions/spinners where the
  spinner is not the only loading signal.
- Hover enhancements are restricted to devices that actually support hover.
- Keyboard and touch users receive equal information and functionality.

## 20. Accessibility

### 20.1 Contrast

The implemented colors must be checked, not assumed. Normal text targets at
least WCAG AA 4.5:1 contrast; large text and non-text controls target their
applicable AA requirements.

Particular checks include:

- off-white on midnight;
- muted cream on raised surfaces;
- midnight text on gold buttons;
- gold links on midnight;
- metadata inside both chat bubble types;
- form placeholders and disabled controls; and
- footer gold on deepest black.

### 20.2 Focus and keyboard

- All links, buttons, inputs, thumbnails, navigation and dialogs keep visible
  focus.
- Sticky navigation never hides focused content.
- No required state depends on color alone.
- Existing semantic headings, landmarks, form labels, ARIA and live regions are
  preserved.

### 20.3 Zoom and reflow

- No horizontal page scrolling at 320 CSS pixels.
- At 200% zoom, navigation, forms, cards, chat and cart reflow.
- Long titles, usernames, prices, filenames and messages wrap.
- Fixed bottom navigation and Shop Assistant do not cover final controls.

### 20.4 Forced colors and print

The app remains operable when decorative backgrounds or shadows disappear.
Print removes dark backgrounds, excessive shadows, sticky/fixed positioning
and nonessential controls while keeping important text readable.

## 21. Google Fonts privacy, reliability and performance

Loading fonts from Google makes browser requests to Google font domains. No
Market Mirror account, product, message, cart or AI data may be placed in those
URLs.

Requirements:

- use stylesheet/font links only, never external font JavaScript;
- use HTTPS;
- load only Cinzel and Montserrat with necessary weights;
- use `display=swap`;
- add appropriate preconnect hints without cookies;
- keep complete local fallback stacks;
- do not block functionality when fonts fail; and
- document the external dependency for local/offline demonstrations.

Self-hosting the same font files is a possible later privacy/offline
enhancement but is outside MM-030 unless approved separately.

## 22. HTML template changes allowed

The redesign may add presentation-only:

- `<link>` elements for fonts/preconnect in `base.html`;
- page wrapper classes/sections;
- component classes on existing elements;
- decorative spans with `aria-hidden="true"`; and
- theme/cache-version identifiers.

It must not:

- change route URLs or form methods/actions;
- remove CSRF or request-token fields;
- rename JavaScript IDs/data attributes used by features/tests;
- move controls into invalid nested forms;
- add duplicate IDs;
- insert decorative text into accessible names unexpectedly;
- turn buttons into non-semantic clickable elements; or
- expose private data.

## 23. CSS organization

The stylesheet should be reorganized only as much as needed to create a clear
token/component structure. The implementation plan must prevent accidental
selector conflicts with product chat bubbles versus AI assistant messages.

Preferred organization:

1. theme tokens and font stacks;
2. reset/base typography;
3. layout/header/footer/navigation;
4. buttons/forms/feedback;
5. panels/cards/catalogue;
6. product/gallery/cart/order/seller;
7. chat and AI Assistant;
8. mobile breakpoints;
9. dark-theme-specific exceptions only if necessary;
10. reduced motion; and
11. print.

Existing functionality may continue using one stylesheet. Introducing a CSS
framework or build pipeline is outside scope.

## 24. Security and functional boundaries

MM-030 makes no network requests except the approved Google font stylesheet
and font files loaded by the browser.

It must not:

- add third-party analytics or scripts;
- send marketplace data to font providers;
- alter authentication or authorization;
- weaken CSRF, content escaping or safe DOM construction;
- change database or upload paths;
- add inline event handlers;
- modify AI prompts/providers; or
- make checkout look like a real payment service.

## 25. Out of scope

- New logo artwork or image generation;
- animated gold particles, video backgrounds or audio;
- a theme switcher;
- user-selectable palettes;
- self-hosted font files;
- Tailwind, Bootstrap or another design framework;
- route, database or business-logic changes;
- a mobile native application;
- new product/card content; and
- new AI behavior.

## 26. Acceptance criteria

| ID | Requirement |
| --- | --- |
| AC-030-01 | The app uses the approved Midnight & Gold token system with off-white readable text and no remaining accidental light-theme surfaces. |
| AC-030-02 | Cinzel display and Montserrat body fonts load through bounded Google Font links with swap and complete fallbacks. |
| AC-030-03 | The top navigation is sticky, dark and gold-accented with preserved desktop/mobile behavior and visible keyboard states. |
| AC-030-04 | The footer is deepest black with readable gold text and appropriate print/mobile behavior. |
| AC-030-05 | Reusable product cards have glass-case fallback/enhancement, subtle gold borders, soft shadows and unchanged semantic/card behavior. |
| AC-030-06 | Eligible Add to Cart controls render as full-width solid gold bars while retaining POST, CSRF, eligibility and cart-count behavior. |
| AC-030-07 | Explore uses increased grid/section spacing without breaking AJAX hooks, filters, pagination, Recently Viewed or narrow reflow. |
| AC-030-08 | Buttons, links, forms, errors, disabled states and focus indicators follow the theme with verified readable contrast. |
| AC-030-09 | Product detail/gallery/lightbox, Cart/order, seller, Dashboard, Saved, inbox and forms share the theme without functional changes. |
| AC-030-10 | MM-029 chat retains ownership alignment, polling, timestamps, safety and composer behavior with coherent Midnight & Gold presentation. |
| AC-030-11 | AI Vision, drag/drop, AJAX loading and Shop Assistant retain all hooks/behavior while receiving readable themed states. |
| AC-030-12 | At 320/360 pixels and 200% zoom, cards and controls reflow with no horizontal overflow or fixed-navigation overlap. |
| AC-030-13 | Reduced-motion, hover capability, forced-color resilience and print rules preserve usability without decoration. |
| AC-030-14 | No route, form action/method, CSRF/request token, JavaScript hook, database row or migration changes as a result of the redesign. |
| AC-030-15 | Focused visual contracts, related UI regressions, complete pytest suite and supported browser checks pass with honest evidence. |

## 27. Required tests after approval

The later PLAN-030 must map every acceptance criterion to evidence and define at
least:

### Static/template tests

- exact palette and font tokens;
- bounded Google Font/preconnect links with fallbacks;
- sticky header and footer contracts;
- primary/secondary/disabled/focus states;
- product card glass fallback/support query and shadow/border;
- full-width gold Add to Cart rule;
- Explore-only generous grid spacing;
- input/autofill/drop-zone/spinner states;
- mobile/reduced-motion/hover/print/forced-color rules;
- preservation of every critical template ID, form method/action and script
  hook; and
- absence of external scripts/analytics.

### Integration/regression tests

- render every main template for anonymous/buyer/seller states;
- scan for accidental missing assets, duplicate IDs and invalid nested forms;
- existing card/cart/search/chat/gallery/AI/mobile tests;
- route/form/database snapshots proving the redesign is presentation-only; and
- complete pytest suite.

### Browser checks

- desktop Home, Explore, product, form, Dashboard, chat, Cart and order pages;
- computed theme colors/fonts and sticky header behavior;
- card glass appearance and gold Add to Cart bar;
- wider Explore spacing;
- link/button hover, keyboard focus and disabled states;
- 320/360-pixel and 200%-zoom reflow;
- mobile bottom navigation and Shop Assistant clearance;
- font failure/offline fallback where tooling supports it;
- reduced motion and print where tooling supports it; and
- no console/network errors other than an honestly documented unavailable
  external font in offline mode.

## 28. Beginner concepts to explain

The final guide must explain at high-school level:

- what a color palette and CSS custom property are;
- why dark navy, gold and off-white need contrast checks;
- the difference between serif and sans-serif fonts;
- how fallback fonts and `display=swap` work;
- how sticky differs from fixed positioning;
- how a translucent card needs a solid fallback;
- why whitespace makes a layout feel more premium;
- what hover, focus, active and disabled states mean;
- why responsive CSS and reduced motion matter; and
- why a visual redesign should not change form actions or application data.

## 29. SDD checkpoint

This document is the Specification stage only. It makes no CSS, HTML,
JavaScript, route, test, database or asset change.

After explicit approval of **MM-030**:

1. create PLAN-030 with a file-by-file implementation and test plan;
2. wait for explicit PLAN-030 approval;
3. write and validate failing pytest visual/structure contracts;
4. implement the redesign only after valid Red evidence; and
5. run focused, related-regression, complete and browser verification.

## 30. Approval record

MM-030 was explicitly approved by the user on 2026-11-08. PLAN-030 was then
approved, the focused suite was validated Red before implementation, and the
completed redesign passed focused, related, complete and browser verification.

