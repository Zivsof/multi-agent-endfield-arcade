"""Endfield lore + curriculum locks for builders and the designer.

Keeps content on *Arknights: Endfield* (Talos-II), not classic Arknights tower-defense.
"""

from __future__ import annotations

# Locked visual system (designer + templates must honor this).
DESIGN_TOKENS = {
    "bg": "#0a0a0a",
    "panel": "#141414",
    "fg": "#f5f5f5",
    "muted": "#a8a8a8",
    "accent": "#f5c518",  # Endfield-leaning yellow
    "accent_dim": "#c9a012",
    "good": "#e8e8e8",
    "bad": "#ff5a5a",
    "font": '"Segoe UI", "Helvetica Neue", Arial, sans-serif',
}

# Prefer these Endfield-facing terms in copy and quizzes.
ALLOWED_FOCUS = [
    "Talos-II",
    "Endministrator",
    "Perlica",
    "Operators (Endfield squad / weapons / classes — not Rhodes Island TD)",
    "AIC (Automated Industry Complex) — factory lines, power, logistics",
    "Exploration / surveying ruins and materials on Talos-II",
    "Progression — leveling, gear, protocol / facility growth",
    "Real-time combat basics — positioning, skills, enemy types (Aggeloi / local threats)",
]

# Classic Arknights (mobile TD) tropes — do not teach these as Endfield.
BANNED_TROPES = [
    "Rhodes Island / Doctor as protagonist framing",
    "Deployment Points (DP), redeploy timers, tile grid tower defense",
    "Classic Operators as the lesson cast (Amiya, Exusiai, SilverAsh, Texas, Chen, etc.)",
    "Oripathy / Originium as the main teaching spine (unless clearly Endfield-context)",
    "Side-view tower-defense lane defense as the core mechanic",
]

# Seeded objectives the orchestrator should prefer (one per default_role).
ROLE_BRIEFS: dict[str, dict[str, str]] = {
    "combat": {
        "title": "Real-time combat on Talos-II",
        "objective": (
            "Teach Arknights: Endfield real-time combat basics on Talos-II: "
            "positioning, skill timing, and reading enemy pressure — not classic Arknights DP/tile TD. "
            "Use Endfield-facing names (e.g. Endministrator, Perlica, Aggeloi) or clearly labeled invent-ons; "
            "never Amiya/Exusiai-style Rhodes Island roster quizzes."
        ),
    },
    "operators": {
        "title": "Endfield Operators & loadouts",
        "objective": (
            "Teach Arknights: Endfield Operator roles and loadouts on Talos-II "
            "(class/weapon fantasy, squad synergy for Endfield missions). "
            "Do NOT recreate classic Arknights tower-defense operator meta, DP costs, or Rhodes Island casts."
        ),
    },
    "aic_factory": {
        "title": "AIC factory loop",
        "objective": (
            "Teach the AIC (Automated Industry Complex) on Talos-II: "
            "production lines, power/logistics balance, and why factories matter to Endfield operations."
        ),
    },
    "exploration": {
        "title": "Talos-II exploration",
        "objective": (
            "Teach Talos-II exploration and surveying: routes, materials, ruin hazards, "
            "and preparing an Endfield outing — not city-building or classic AK stages."
        ),
    },
    "progression": {
        "title": "Progression & gear",
        "objective": (
            "Teach Endfield progression: Operator leveling, gear/protocol upgrades, and "
            "efficient growth choices for Talos-II missions — evergreen systems, not patch meta."
        ),
    },
}


def brief_for_role(role: str) -> dict[str, str]:
    return ROLE_BRIEFS.get(role) or {
        "title": "Endfield systems",
        "objective": (
            "Teach an evergreen Arknights: Endfield systems topic for Talos-II players. "
            "Do not use classic Arknights tower-defense framing."
        ),
    }


def preferred_objective(role: str) -> str:
    return brief_for_role(role)["objective"]


def lore_block_for_prompt() -> str:
    allowed = "\n".join(f"- {x}" for x in ALLOWED_FOCUS)
    banned = "\n".join(f"- {x}" for x in BANNED_TROPES)
    return (
        "LORE LOCK — this is Arknights: Endfield (Talos-II), NOT classic Arknights mobile TD.\n"
        f"Prefer teaching about:\n{allowed}\n"
        f"Hard bans (do not center the game on these):\n{banned}\n"
        "If you invent characters, label them clearly as fan/demo names; never quiz Rhodes Island roster trivia."
    )


def design_block_for_prompt() -> str:
    t = DESIGN_TOKENS
    return (
        "DESIGN LOCK — black / yellow / white Endfield-leaning UI.\n"
        f"- Background near {t['bg']}, panels {t['panel']}, text {t['fg']}, muted {t['muted']}.\n"
        f"- Accent yellow {t['accent']} (buttons, links, focus rings). No cyan/purple neon.\n"
        "- High contrast, industrial/sci-fi, sharp corners or slight radius only.\n"
        "- Reuse shared classes from ../common.css; game.css may add layout only.\n"
        "- No external fonts/CDN; system font stack is fine."
    )


def curriculum_lines_for_team(workers: list[dict]) -> str:
    """Lines for the orchestrator prompt: preferred objective per builder."""
    lines = []
    for w in workers:
        role = w.get("default_role", "")
        brief = brief_for_role(role)
        lines.append(
            f"- {w['name']} (key: {w['key']}, folder: {w['slug']}/, role: {role}): "
            f"prefer objective ≈ \"{brief['objective']}\""
        )
    return "\n".join(lines)
