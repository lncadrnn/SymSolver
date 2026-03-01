"""
DualSolver — Colour / theme definitions

Immutable palette dicts and mutable module-level shortcuts that are updated
by ``apply_theme()`` whenever the user toggles between dark and light mode.
"""

# ── Immutable palette dicts ────────────────────────────────────────────────

DARK_PALETTE = dict(
    BG           = "#0a0a0a",
    BG_DARKER    = "#050505",
    HEADER_BG    = "#111111",
    ACCENT       = "#1a8cff",
    ACCENT_HOVER = "#0a70d4",
    TEXT         = "#d0d0d0",
    TEXT_DIM     = "#ffffff",
    TEXT_BRIGHT  = "#f0f0f0",
    USER_BG      = "#1a1a1a",
    BOT_BG       = "#121212",
    STEP_BG      = "#181818",
    STEP_BORDER  = "#2a2a2a",
    SUCCESS      = "#4caf50",
    ERROR        = "#ff5555",
    INPUT_BG     = "#181818",
    INPUT_BORDER = "#2a2a2a",
    VERIFY_BG    = "#0f1a0f",
    SCROLLBAR_BG = "#2a2a2a",
    SCROLLBAR_ACT= "#444444",
    SCROLLBAR_ARR= "#555555",
)

LIGHT_PALETTE = dict(
    BG           = "#f2f4f7",
    BG_DARKER    = "#e4e8ee",
    HEADER_BG    = "#ffffff",
    ACCENT       = "#0F4C75",
    ACCENT_HOVER = "#0a3a5c",
    TEXT         = "#444444",
    TEXT_DIM     = "#000000",
    TEXT_BRIGHT  = "#111111",
    USER_BG      = "#e6eaf0",
    BOT_BG       = "#ffffff",
    STEP_BG      = "#f7f9fc",
    STEP_BORDER  = "#dde2ea",
    SUCCESS      = "#2e7d32",
    ERROR        = "#c62828",
    INPUT_BG     = "#ffffff",
    INPUT_BORDER = "#c5ccd6",
    VERIFY_BG    = "#e8f5e9",
    SCROLLBAR_BG = "#c5ccd6",
    SCROLLBAR_ACT= "#9baabb",
    SCROLLBAR_ARR= "#888888",
)

# ── Case-badge colour tables (graph analysis card) ────────────────────────

DARK_CASE_COLORS = {
    "one_solution":              {"bg": "#0d1f0d", "border": "#4caf50", "fg": "#4caf50"},
    "infinite":                  {"bg": "#1a1500", "border": "#f0c040", "fg": "#f0c040"},
    "no_solution":               {"bg": "#1f0d0d", "border": "#ff5555", "fg": "#ff5555"},
    "degenerate_identity":       {"bg": "#1a1500", "border": "#f0c040", "fg": "#f0c040"},
    "degenerate_contradiction":  {"bg": "#1f0d0d", "border": "#ff5555", "fg": "#ff5555"},
}

LIGHT_CASE_COLORS = {
    "one_solution":              {"bg": "#e8f5e9", "border": "#2e7d32", "fg": "#1b5e20"},
    "infinite":                  {"bg": "#fff8e1", "border": "#f57f17", "fg": "#e65100"},
    "no_solution":               {"bg": "#ffebee", "border": "#c62828", "fg": "#b71c1c"},
    "degenerate_identity":       {"bg": "#fff8e1", "border": "#f57f17", "fg": "#e65100"},
    "degenerate_contradiction":  {"bg": "#ffebee", "border": "#c62828", "fg": "#b71c1c"},
}

# ── Mutable "active" colour shortcuts ─────────────────────────────────────
# These start with dark-mode values and are refreshed by ``apply_theme()``.

BG           = DARK_PALETTE["BG"]
BG_DARKER    = DARK_PALETTE["BG_DARKER"]
HEADER_BG    = DARK_PALETTE["HEADER_BG"]
ACCENT       = DARK_PALETTE["ACCENT"]
ACCENT_HOVER = DARK_PALETTE["ACCENT_HOVER"]
TEXT         = DARK_PALETTE["TEXT"]
TEXT_DIM     = DARK_PALETTE["TEXT_DIM"]
TEXT_BRIGHT  = DARK_PALETTE["TEXT_BRIGHT"]
USER_BG      = DARK_PALETTE["USER_BG"]
BOT_BG       = DARK_PALETTE["BOT_BG"]
STEP_BG      = DARK_PALETTE["STEP_BG"]
STEP_BORDER  = DARK_PALETTE["STEP_BORDER"]
SUCCESS      = DARK_PALETTE["SUCCESS"]
ERROR        = DARK_PALETTE["ERROR"]
INPUT_BG     = DARK_PALETTE["INPUT_BG"]
INPUT_BORDER = DARK_PALETTE["INPUT_BORDER"]
VERIFY_BG    = DARK_PALETTE["VERIFY_BG"]


def palette(theme: str) -> dict:
    """Return the palette dict for *theme* (``"dark"`` or ``"light"``)."""
    return DARK_PALETTE if theme == "dark" else LIGHT_PALETTE


def apply_theme(theme: str) -> None:
    """Update the mutable module-level colour shortcuts for *theme*."""
    import sys
    p = palette(theme)
    mod = sys.modules[__name__]
    for k, v in p.items():
        if k in ("SCROLLBAR_BG", "SCROLLBAR_ACT", "SCROLLBAR_ARR"):
            continue
        setattr(mod, k, v)
