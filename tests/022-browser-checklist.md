# MM-022 browser acceptance checklist

Status: defined before implementation

Use only the isolated port-5022 fixture database/uploads and its synthetic
draggable files for stateful checks. Never drop or submit the user's personal
files and never create a listing in the real local database.

| # | Browser check | Expected result |
| --- | --- | --- |
| 1 | Open signed-in `/listings/new` at desktop width. | One dashed zone contains the native labelled file input, drag instruction, JPEG/PNG and 5 MiB help. Preview/status begin empty and Save remains the only submit action. |
| 2 | Drag a valid synthetic JPEG across the zone instruction, input and help before dropping. | Highlight appears and remains stable across children; cursor indicates copy; drop clears highlight and does not navigate. |
| 3 | Inspect the result after the JPEG drop. | Real input contains exactly one file; one thumbnail appears with correct aspect ratio, safe filename text and polite Photo selected feedback; URL/page and database remain unchanged. |
| 4 | Drop a valid PNG replacement. | Exactly one new preview replaces the first; the old object URL is revoked and no second thumbnail/filename is added. |
| 5 | Try zero files, multiple files, zero-byte, unsupported type, over-5-MiB and directory-like fixture sources. | Each rejected case clears input/preview/highlight, shows an understandable message, and causes no navigation, submission, server request or stored file. |
| 6 | Try corrupt image bytes with a supported name/type. | Decode failure removes the broken preview, clears input, revokes the object URL and asks for a readable JPEG/PNG. |
| 7 | Exercise ordinary file-picker selection with fixture files if the browser supports authorized test-file selection. | It uses the same preview/status path as drop; keyboard focus stays where the user left it. Record an honest limitation if native picker control is unavailable. |
| 8 | Select an image, then request category and price AI suggestions. | Suggestions still work; no image bytes or object URL are sent to AI and no server upload exists before Save. |
| 9 | Fill required fields and Save once in the fixture. | Existing CSRF/request-token route creates one owner listing, stores one normalized JPEG, and redirects to owner preview. |
| 10 | Submit once with invalid title/price after selecting a file. | Server returns the form error; browser file input/preview reset honestly instead of claiming the file was retained. |
| 11 | Use Tab/Shift+Tab through the image input and Save. | Native chooser is keyboard reachable, focus is visible, reading order is logical and preview does not steal focus. |
| 12 | Test at 320×800 and a short landscape viewport. | Zone, preview, long/HTML-like/Unicode filename and messages wrap; `scrollWidth <= innerWidth`; mobile bottom bar does not cover Save/errors. |
| 13 | Use a controlled no-script response. | Complete native input and normal multipart Save remain usable; no empty/broken preview UI is exposed as interactive. |
| 14 | Visit Edit listing, Home, Explore and a product detail. | Edit retains the ordinary input, other pages have no zone, existing lightbox/search/mobile behavior works and shared script reports no error. |
| 15 | Check available dark mode, reduced motion and 200% zoom capabilities. | Theme/focus/drag states remain readable and operable. Unsupported emulation is reported, never claimed. |
| 16 | Inspect console/network and capture evidence if export is supported. | No new warning/error; preview activity makes no request. Only the final fixture Save sends the multipart image. |

Afterward stop the disposable server, reset viewport/media overrides, restart the
real local server, and perform only a read-only real Sell-page/startup check.
