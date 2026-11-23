"""MM-029 client contracts, written before chat HTML/CSS/JavaScript changes."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "app" / "templates" / "conversation.html"
BASE = ROOT / "app" / "templates" / "base.html"
STYLE = ROOT / "app" / "static" / "css" / "style.css"
SCRIPT = ROOT / "app" / "static" / "js" / "conversation.js"


def read(path):
    return path.read_text(encoding="utf-8")


def test_template_and_base_have_progressive_chat_hooks():
    template = read(TEMPLATE)
    base = read(BASE)
    assert 'id="chat-shell"' in template
    assert 'id="chat-transcript"' in template and "<ol" in template
    assert 'id="chat-live-status"' in template
    assert 'aria-live="polite"' in template and 'role="status"' in template
    assert 'id="chat-composer"' in template
    assert 'id="chat-mark-read"' in template
    assert 'id="chat-read-message-id"' in template
    assert 'data-message-id="{{ message.id }}"' in template
    assert "|safe" not in template and "| safe" not in template
    assert "{% block scripts %}" in base
    assert "js/conversation.js" in template


def test_chat_css_defines_bubbles_scroll_composer_and_preferences():
    css = read(STYLE)
    for selector in (
        ".chat-shell", ".chat-transcript", ".chat-message--outgoing",
        ".chat-message--incoming", ".chat-bubble", ".chat-message-time",
        ".chat-composer",
    ):
        assert selector in css
    assert re.search(r"\.chat-message--outgoing[^}]*justify-content\s*:\s*flex-end", css, re.S)
    assert re.search(r"\.chat-message--incoming[^}]*justify-content\s*:\s*flex-start", css, re.S)
    assert re.search(r"\.chat-transcript[^}]*overflow-y\s*:\s*auto", css, re.S)
    assert re.search(r"\.chat-composer[^}]*position\s*:\s*sticky", css, re.S)
    assert re.search(r"\.chat-composer[^}]*bottom\s*:\s*0", css, re.S)
    assert "44px" in css and "overflow-wrap: anywhere" in css
    assert "@media (max-width: 42rem)" in css
    assert "@media (prefers-color-scheme: dark)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "@media print" in css


def test_chat_script_uses_safe_nonoverlapping_three_second_polling():
    javascript = read(SCRIPT)
    assert "3000" in javascript
    assert "setTimeout" in javascript
    assert "setInterval" not in javascript
    assert "document.hidden" in javascript
    assert "visibilitychange" in javascript
    assert "AbortController" in javascript and "pagehide" in javascript
    assert "credentials: 'same-origin'" in javascript or 'credentials: "same-origin"' in javascript
    assert "cache: 'no-store'" in javascript or 'cache: "no-store"' in javascript
    assert "Accept" in javascript and "application/json" in javascript


def test_chat_script_validates_deduplicates_and_builds_text_nodes():
    javascript = read(SCRIPT)
    assert "Array.isArray" in javascript
    assert "messages.length > 50" in javascript
    assert "Number.isSafeInteger" in javascript
    assert "new Set" in javascript
    assert "knownMessageIds" in javascript
    assert "document.createElement" in javascript
    assert ".textContent" in javascript
    assert ".innerHTML" not in javascript
    assert "insertAdjacentHTML" not in javascript
    assert "latest_id" in javascript and "has_more" in javascript


def test_chat_script_handles_time_scroll_status_and_never_submits_read_form():
    javascript = read(SCRIPT)
    assert "Intl.DateTimeFormat" in javascript
    assert "hour12: true" in javascript
    assert "scrollHeight" in javascript and "scrollTop" in javascript
    assert "New messages arrived." in javascript
    assert "Waiting to reconnect" in javascript
    assert "Your session ended" in javascript
    assert "chat-read-message-id" in javascript
    assert ".submit(" not in javascript
    assert ".requestSubmit(" not in javascript

