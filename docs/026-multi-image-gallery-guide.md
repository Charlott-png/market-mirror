# Understanding Market Mirror's product photo gallery

MM-026 lets a seller choose **zero to five photos** for one product. The first
photo is the cover shown on catalogue cards. On the product page, two or more
photos appear as small thumbnails; choosing a thumbnail changes the large
photo and the existing lightbox.

## The big idea: one product can have many photos

Earlier, a Product had one `image_filename`. That is like writing one photo
name directly on a product card. A gallery needs a separate list:

```text
Product: Silver laptop
    ├── ProductImage position 0: front.jpg  ← cover
    ├── ProductImage position 1: side.jpg
    └── ProductImage position 2: back.jpg
```

This is called a **one-to-many relationship**: one Product can own many
ProductImage rows. The position number keeps the order stable. Valid positions
are 0, 1, 2, 3 and 4, which means the maximum is five photos.

The older `Product.image_filename` field still stores the position-zero name.
That small duplication is intentional **backward compatibility**: catalogue,
cart and recommendation cards can keep loading one cover while older listings
continue to work.

## What happens after the seller chooses photos?

The browser first creates temporary local previews. It does not upload or save
anything yet. The first preview says **Cover photo** so the seller knows which
picture cards will use.

When Save Listing is pressed, the server checks every file:

1. there are no more than five files;
2. each is a real, nonempty JPEG or PNG no larger than 5 MiB;
3. the group is no larger than 25 MiB;
4. each image has one frame and at most 12 million pixels; and
5. every accepted image is re-encoded as a new, metadata-free JPEG.

Browser checks are friendly early warnings. Server checks are the real safety
boundary because a person can bypass or change browser code.

## Why the save is all-or-nothing

Imagine photos 1 and 2 are valid but photo 3 is corrupt. Saving only the first
two would surprise the seller. Market Mirror instead removes any new files it
already created and saves no listing.

The database can roll back its rows automatically. Ordinary image files cannot
join a database transaction, so the code tracks new filenames and removes them
after a failure. This is called **compensation**.

Editing is just as careful:

- selecting no new files keeps the existing gallery;
- selecting new files replaces the whole gallery;
- old files are removed only after the new rows commit successfully; and
- a failure removes the new files and leaves the old gallery untouched.

## How the gallery works in the page

Jinja first renders safe thumbnail buttons in database order. JavaScript adds
the convenient interaction: choosing a thumbnail updates the main image, its
link, accessible text, selected marker and the lightbox source together. The
page uses text properties rather than inserting filenames as raw HTML.

This is **progressive enhancement**. Without JavaScript, the server-rendered
cover and image links remain useful. With JavaScript, the experience becomes
faster because the page does not reload.

## AI Vision privacy rule

When the optional AI checkbox is enabled on Sell, only the first/cover photo is
analyzed for title and category suggestions. Photos 2–5 are not sent to the AI
provider. AI suggestions never save the listing or choose the photo order.

## Security and privacy

Image URLs are not a shortcut around product privacy. An active or sold
product's gallery is public. An archived product's images return 404 to anyone
except its seller. Random orphan filenames and invalid paths also return 404.

The maintenance command now counts every gallery row as a real reference and
reports missing images, orphan files and cover drift. It does not delete
orphans unless the operator explicitly requests deletion.

## Try the automated tests

In PowerShell, from the `market-mirror` folder:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_multi_image_gallery.py tests\test_multi_image_migration.py tests\test_image_dropzone.py -q --basetemp=.pytest-tmp\mm026-student
```

Expected result: `32 passed`.

## Small practice tasks

1. Predict the rows after saving three valid photos. Answer: positions 0, 1
   and 2, with position 0 also copied to `Product.image_filename`.
2. Predict what remains if photo 3 is corrupt. Answer: no new Product, no new
   ProductImage rows and no new image files.
3. Predict what an empty image field does on Edit. Answer: it keeps every old
   gallery row and file.
4. Explain why cards load only position 0. Answer: it keeps pages simple and
   avoids downloading up to five large pictures for every card.
5. Open a product with several images, choose thumbnail 2 and open the
   lightbox. Explain which JavaScript values changed and why the page did not
   reload.

## Current limits

MM-026 does not include drag-to-reorder, delete-one-photo, captions or a
remove-all-photos button. To change order, choose the replacement files again
in the desired order. These are deliberate limits that keep the feature easy
to test and explain.
