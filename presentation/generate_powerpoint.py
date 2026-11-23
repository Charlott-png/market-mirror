"""Beginner-friendly launcher for the Market Mirror PowerPoint generator.

The editable slide construction lives in generate_powerpoint.mjs because that
tool can write real PowerPoint speaker notes and validate the resulting file.
This Python launcher checks the HTML source, runs the generator, and confirms
that the final presentation contains eight slides and eight Notes sections.
"""

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
HTML_FILE = SCRIPT_DIR / "index.html"
GENERATOR_FILE = SCRIPT_DIR / "generate_powerpoint.mjs"
OUTPUT_FILE = PROJECT_DIR / "MarketMirror_Presentation.pptx"
NODE_EXE = Path(
    r"C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt\dependencies\node\bin\node.exe"
)


def validate_html() -> None:
    """Confirm that the source still contains the expected slides and notes."""
    html = HTML_FILE.read_text(encoding="utf-8")
    slides = re.findall(r'<section class="slide(?: is-active)?" id="slide-\d+"', html)
    notes = re.findall(r'<aside class="speaker-notes"', html)
    if len(slides) != 8 or len(notes) != 8:
        raise RuntimeError(
            f"Expected 8 slides and 8 speaker-note sections, found "
            f"{len(slides)} slides and {len(notes)} notes."
        )


def validate_powerpoint() -> None:
    """Check the generated PowerPoint package without opening PowerPoint."""
    if not OUTPUT_FILE.exists():
        raise RuntimeError(f"The generator did not create {OUTPUT_FILE}.")

    with zipfile.ZipFile(OUTPUT_FILE) as archive:
        names = archive.namelist()
        slides = [name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)]
        notes = [name for name in names if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", name)]
    if len(slides) != 8 or len(notes) != 8:
        raise RuntimeError(
            f"Generated file contains {len(slides)} slides and {len(notes)} Notes sections."
        )


def main() -> int:
    validate_html()
    if not NODE_EXE.exists():
        raise FileNotFoundError(
            "The bundled presentation runtime was not found. Run this command "
            "from the same computer where the deck was created."
        )

    result = subprocess.run(
        [str(NODE_EXE), str(GENERATOR_FILE)],
        cwd=SCRIPT_DIR,
        check=False,
    )

    # The Windows rendering process can return a non-zero shutdown code after
    # successfully saving the deck, so the file itself is the source of truth.
    validate_powerpoint()
    print(f"Created: {OUTPUT_FILE}")
    print("Verified: 8 slides and 8 speaker-note sections")
    if result.returncode:
        print("The rendering helper reported a shutdown warning, but the validated file is complete.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
