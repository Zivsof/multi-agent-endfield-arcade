"""Lore / design lock smoke tests."""

from __future__ import annotations

from pathlib import Path

from orchestrator.content import lore
from orchestrator.gates import game_gate
from orchestrator.site_build import art_director
from orchestrator.tools.launch import _prefer_endfield_objective


def test_role_briefs_cover_catalog_roles():
    for role in ("combat", "operators", "aic_factory", "exploration", "progression"):
        brief = lore.brief_for_role(role)
        assert "Endfield" in brief["objective"] or "Talos" in brief["objective"]
        assert not brief["objective"].lower().startswith("teach rhodes")


def test_prefer_swaps_classic_ak_objective():
    swapped = _prefer_endfield_objective("operators", "Teach Amiya and Rhodes Island DP meta")
    assert "Amiya" not in swapped
    assert "Endfield" in swapped or "Talos" in swapped


def test_template_css_is_black_yellow_white():
    css = art_director._template_css().lower()
    assert lore.DESIGN_TOKENS["accent"].lower() in css
    assert lore.DESIGN_TOKENS["bg"].lower() in css
    assert "#00d4ff" not in css


def test_template_hub_has_hero_and_cards():
    html = art_director._template_hub("Endfield", [{"label": "Drill", "slug": "strands"}])
    assert "hero" in html and "nav-grid" in html and "card" in html
    assert "strands/game.html?difficulty=beginner" in html
    assert "strands/game.html?difficulty=veteran" in html


def test_gate_flags_classic_ak_smell(tmp_path: Path):
    folder = tmp_path / "bad"
    folder.mkdir()
    (folder / "game.css").write_text("body{}", encoding="utf-8")
    (folder / "game.js").write_text(
        "const q='difficulty'; if(location.search.includes('beginner')){}",
        encoding="utf-8",
    )
    (folder / "game.html").write_text(
        '<link rel="stylesheet" href="../common.css">'
        "<p>AI-generated content: take with a grain of salt</p>"
        "<p>Quiz: Amiya DP cost on Rhodes Island</p>"
        "<button>Beginner</button><button>Veteran</button>",
        encoding="utf-8",
    )
    result = game_gate.check_game(folder)
    assert not result["ok"]
    assert "classic_arknights_lore_smell" in result["failures"]
