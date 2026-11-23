# MM-028 Browser Checklist

Status: EXECUTED on 2026-11-07 against the isolated Waitress fixture.

Use only `python -m tests.preview_recently_viewed`. It creates a temporary
database under `.pytest-tmp` and never reads the real marketplace database.

| Step | Expected result |
| --- | --- |
| Anonymous Explore | No Recently Viewed section appears. |
| Sign in to the fixture | Explore shows the empty-state sentence. |
| Open camera, laptop and mouse | Explore and Dashboard show mouse, laptop, camera newest first. |
| Reopen camera | Camera moves to the first position with no duplicate. |
| Open three additional products | Only the five newest distinct products remain. |
| Product electronics page | Up to three distinct active electronics alternatives appear; current product is absent. |
| Book product page | Same-category section is absent because there is no alternative book. |
| Add `?fixture_no_script=1` | Related cards remain because Flask rendered them; history does not update without the view POST script. |
| AJAX search | Recently Viewed remains in place while only search results change. |
| Dashboard | Recently Viewed remains separate from Discover more. |
| 320/360 px and keyboard | Cards wrap, links/buttons remain reachable and mobile navigation is not covered. |

## Recorded result

The anonymous, empty-state, order, repeat-view, five-item cap,
same-category, no-alternative, no-JavaScript, AJAX and Dashboard checks passed.
The browser console contained no JavaScript errors. This browser session did
not provide viewport resizing, so the narrow-width rule is covered by the
existing mobile-navigation automated/static tests and remains a short manual
presentation rehearsal rather than a falsely claimed browser result.

