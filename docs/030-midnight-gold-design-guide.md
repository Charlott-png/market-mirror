# MM-030 Midnight & Gold Design Guide

## What we built

Market Mirror now uses one visual system across the whole application:

- midnight navy backgrounds communicate depth and confidence;
- gold identifies important links, prices and primary actions;
- warm off-white keeps paragraphs comfortable to read;
- Cinzel gives headings a formal, prestigious character;
- Montserrat keeps forms, buttons and ordinary text clear;
- product cards look like dark glass display cases; and
- generous spacing makes the catalogue feel calmer and more exclusive.

The important idea is **consistency**. A luxurious interface is not created by
putting gold everywhere. It comes from repeating a small group of colors,
fonts, borders, shadows and spacing rules with restraint.

## How the code works

### 1. CSS variables are named design choices

The `:root` section in `style.css` contains variables such as `--midnight`,
`--gold` and `--off-white`. A variable is like a labeled container. Components
refer to the label instead of copying a color value everywhere.

If the gold changes later, one variable can update every component using it.
This is called a **design token system**.

### 2. Two font jobs

Cinzel is a serif font. Its small decorative strokes help headings feel formal.
Montserrat is a sans-serif font. Its simpler shapes are easier to scan in body
text and controls.

Google Fonts uses `display=swap`, which means the browser shows a local fallback
immediately instead of hiding text while the font downloads. If there is no
internet, the website still works with Georgia and Arial-family fallbacks.

### 3. Fallback first, enhancement second

Cards first receive a solid raised-navy background. Browsers supporting
`backdrop-filter` may then add a subtle translucent glass effect. This is
**progressive enhancement**: the basic version works everywhere, and capable
browsers receive extra polish.

### 4. Sticky and fixed are different

The top header is `sticky`. It begins in the normal page layout and stays at the
top after scrolling reaches it. The mobile bottom navigation and Shop Assistant
are `fixed`, so they stay attached to the viewport.

Because fixed elements can cover content, mobile safe-area padding and offsets
must be tested carefully.

### 5. Responsive CSS changes layout, not content

At the 42rem breakpoint, desktop navigation hides and the five-item bottom bar
appears. At small widths, forms and product grids become one column. The same
HTML and product data remain; only their layout changes.

### 6. Accessibility is part of the visual design

Gold and midnight were measured for contrast. Keyboard focus has an obvious
outline. Reduced-motion users do not receive card lifts or long transitions.
Print styles remove dark ink-heavy backgrounds. Forced-color rules keep borders
visible when Windows controls the colors.

## Why working features were protected

The redesign did not rename the IDs used by AJAX search, the gallery, image
upload, chat or Shop Assistant. It did not change form actions, CSRF fields,
routes or database tables.

This is an important professional lesson: a visual change should not silently
change how data is saved, who has permission, or where a form is sent.

## Small practice tasks

Complete these one at a time and refresh the browser after each change:

1. Find `--gold` in `style.css`. Temporarily change it to another gold shade,
   observe which components update, then restore `#D4AF37`.
2. Find `.catalogue-page #product-grid`. Change its `gap` from `2rem` to
   `1rem`, compare how crowded it feels, then restore `2rem`.
3. Use the Tab key on Explore. Confirm every link, field and button has visible
   focus.
4. Narrow the browser slowly. Explain the point where desktop navigation is
   replaced by bottom navigation.
5. Disconnect from the internet and refresh. Explain why text still displays
   even if Google Fonts cannot load.
6. Open print preview. Confirm the page becomes light and readable instead of
   printing large dark backgrounds.

## Presentation explanation

A clear class explanation could be:

> I created a reusable Midnight & Gold design system with CSS variables. Cinzel
> is used for prestigious display headings, while Montserrat keeps interface
> text readable. Product cards have a solid fallback and an optional glass
> effect. Responsive and accessibility rules protect mobile, keyboard,
> reduced-motion, forced-color and print users. I changed presentation without
> changing routes, database behavior or security fields, then verified that all
> 603 project tests still passed.
