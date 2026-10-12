"""Resolve bundled card fronts and the current solar theme without disk I/O."""

from pathlib import Path

from homeassistant.helpers.sun import is_up

from .const import PROVIDER_KRATES
from .readings import normalize_card_name

DAY_THEME = "mother_nature"
NIGHT_THEME = "purple_goddess"
ARTWORK_ROOT = Path(__file__).with_name("artwork")
RANKS = ("ac", *(f"{rank:02d}" for rank in range(2, 11)), "pa", "kn", "qu", "ki")
CARD_IDS = frozenset(
    [f"ar{number:02d}" for number in range(22)]
    + [f"{suit}{rank}" for suit in ("wa", "cu", "sw", "pe") for rank in RANKS]
)


def current_theme(hass) -> str:
    """Use sun.sun, or the configured home location if Sun is unavailable."""
    sun = hass.states.get("sun.sun")
    if sun is not None and sun.state in ("above_horizon", "below_horizon"):
        daytime = sun.state == "above_horizon"
    else:
        try:
            daytime = is_up(hass)
        except ValueError:
            daytime = False
    return DAY_THEME if daytime else NIGHT_THEME


def card_id_for(hub) -> str | None:
    """Use raw canonical IDs or the same exact name matching as the readings."""
    card = hub.last_card or {}
    if hub.provider == PROVIDER_KRATES:
        name = card.get("name")
        card_id = (
            hub.readings.name_index.get(normalize_card_name(name))
            if isinstance(name, str) else None
        )
    else:
        card_id = card.get("name_short")
    return card_id if isinstance(card_id, str) and card_id in CARD_IDS else None
