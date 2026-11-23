# MM-030 Green Verification

Date: 2026-11-08 (Asia/Shanghai)

## SDD sequence

1. MM-030 was explicitly approved.
2. PLAN-030 was explicitly approved.
3. Fourteen focused contracts were written and collected against the unchanged
   website.
4. The valid Red run produced 12 intended failures and 2 passing preservation
   contracts.
5. The Red evidence was recorded before any CSS or application-template
   implementation change.
6. Implementation began only after those checkpoints.

## Automated results

| Check | Result |
| --- | --- |
| Focused MM-030 contracts | **14 passed in 0.48 seconds** |
| Related search/cart/image/mobile/chat/AI regressions | **325 passed in 135.23 seconds** |
| Complete project suite | **603 passed in 571.78 seconds** |
| Final MM-030 + mobile tests after browser correction | **46 passed in 24.64 seconds** |
| Installed-package consistency | `pip check`: no broken requirements |

The first related run used the Windows-managed temporary location. Ninety-three
tests passed, while 232 stopped during setup because pytest could not create a
numbered folder there. These were environment setup errors, not assertion
failures. The exact suite was rerun with `--basetemp` inside the project and all
325 tests passed. The complete suite used the same isolated workspace approach.

## Contrast calculations

Representative WCAG contrast ratios calculated from the exact theme tokens:

| Pair | Ratio |
| --- | ---: |
| Off-white `#F7F3E8` on Midnight `#0A1128` | 16.85:1 |
| Muted cream `#C9C1AE` on Raised `#121B33` | 9.53:1 |
| Midnight text on Gold `#D4AF37` | 8.89:1 |
| Gold link on Midnight | 8.89:1 |
| Gold footer text on Deepest `#05070D` | 9.58:1 |
| Error `#FFB4B4` on Raised | 10.11:1 |

These representative pairs exceed the 4.5:1 normal-text target. Browser and
assistive-technology checks still matter because opacity, images and operating
system modes can affect a complete interface.

## Browser result

The actual local app was checked at desktop, the browser's default narrow size
and an explicit 320×700 viewport. The browser verified:

- luxurious Home hero typography and action hierarchy;
- sticky dark navigation with gold brand/links;
- premium Explore filter panel, spacious card grid and product images;
- deep-black footer and floating gold AI Assistant;
- product detail, related cards and near-black image lightbox;
- one-column 320-pixel reflow with no horizontal overflow;
- desktop links hidden and five-item mobile navigation visible at narrow width;
- Shop Assistant expansion and readable anonymous fallback; and
- zero JavaScript console errors.

The first live narrow view found a duplicate-navigation cascade issue. It was
fixed, reloaded and verified before completion. Details are in
`tests/030-browser-checklist.md`.

## Functional boundary

MM-030 changed presentation only:

- no Python application module changed;
- no route, model or migration changed;
- no JavaScript behavior changed;
- no database or uploaded media changed;
- existing form methods/actions, CSRF fields and JavaScript IDs remain; and
- Google Fonts adds only stylesheet/font requests with local fallback stacks.

## Honest limits

The session did not claim a real screen-reader audit, printed-paper result,
forced-colors browser emulation, blocked-font network rehearsal or 200%-zoom
task walkthrough. Those remain valuable manual class-presentation exercises.
