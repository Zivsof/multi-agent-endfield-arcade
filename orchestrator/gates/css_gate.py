"""Deterministic gate for art-director ``common.css`` (Step 4).

This is plain Python string checks — not an LLM and not a browser. It catches the
failure mode where generated CSS underlines all ``a`` tags (e.g. ``border-bottom``)
without resetting ``a.btn``, so hub CTAs look broken.

Used by:
  - ``site_build.art_director.author_style`` after generate / repair
  - ``css_passes`` / ``agent._ensure_site`` at end of run
  - ``tests/test_css_gate.py``
"""

from __future__ import annotations

from orchestrator.content.lore import DESIGN_TOKENS

_YELLOW_HINTS = (
    DESIGN_TOKENS["accent"].lower(),
    "#ffcc00",
    "#f0c000",
    "#ffd100",
    "#e8b923",
)

# Substrings hub template + games expect to exist in common.css.
REQUIRED_CSS_MARKERS = (
    ":root",
    "--bg",
    "--accent",
    ".btn",
    ".ghost",
    ".nav-grid",
    ".card",
    ".hero",
    ".disclaimer",
    ".correct",
    ".wrong",
)


def check_common_css(css: str) -> dict:
    """Return ``{"ok": bool, "failures": list[str]}`` for a candidate ``common.css``.

    Failure codes (examples):
      - ``too_short`` — empty or tiny output (API failure often becomes "")
      - ``missing_palette`` — no yellow + dark background hints
      - ``banned_accent`` — cyan/purple neon crept in
      - ``missing:.btn`` — required selector/class string absent
      - ``btn_link_underline_conflict`` — global link underline without ``a.btn`` reset
    """
    failures: list[str] = []
    if len(css.strip()) < 120:
        failures.append("too_short")

    low = css.lower()
    compact = low.replace(" ", "")

    if not _has_palette(low):
        failures.append("missing_palette")
    if any(x in low for x in ("#00d4ff", "#7c3aed", "#a855f7", "purple")):
        failures.append("banned_accent")

    for marker in REQUIRED_CSS_MARKERS:
        if marker.lower().replace(" ", "") not in compact:
            failures.append(f"missing:{marker}")

    # Link-as-button: global underline on all anchors breaks .btn pills on the hub.
    if "border-bottom" in low and ".btn" in low:
        has_btn_reset = (
            "a.btn" in compact
            or ("text-decoration:none" in compact and ".btn" in compact)
        )
        if not has_btn_reset:
            failures.append("btn_link_underline_conflict")

    return {"ok": not failures, "failures": failures}


def _has_palette(low: str) -> bool:
    """Rough check for Endfield black + yellow tokens somewhere in the CSS."""
    has_yellow = any(y in low for y in _YELLOW_HINTS) or (
        "--accent" in low and "f5c" in low
    )
    has_dark = "#0a0a0a" in low or "#000" in low or "--bg" in low
    return has_yellow and has_dark
