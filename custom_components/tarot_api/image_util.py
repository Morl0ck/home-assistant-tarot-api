"""Map ekelen/tarot-api name_short codes to public-domain RWS filenames."""

from __future__ import annotations

from .const import METABISMUTH_IMAGE_BASE


def image_url_for_ekelen_card(card: dict) -> str | None:
    """Return a JPG URL for Rider–Waite–Smith scans (metabismuth/tarot-json)."""
    name_short = card.get("name_short")
    if not name_short or not isinstance(name_short, str):
        return None
    filename = filename_for_name_short(name_short.lower())
    if not filename:
        return None
    return f"{METABISMUTH_IMAGE_BASE}/{filename}"


def filename_for_name_short(ns: str) -> str | None:
    """Convert tarotapi.dev name_short to m00.jpg / w01.jpg style names."""
    if ns.startswith("ar") and len(ns) >= 3 and ns[2:].isdigit():
        num = int(ns[2:])
        if 0 <= num <= 21:
            return f"m{num:02d}.jpg"
        return None

    if len(ns) < 4:
        return None

    suit_prefix, suffix = ns[:2], ns[2:]
    suit_letter = {"wa": "w", "cu": "c", "pe": "p", "sw": "s"}.get(suit_prefix)
    if not suit_letter:
        return None

    if suffix == "ac":
        return f"{suit_letter}01.jpg"
    if suffix.isdigit() and len(suffix) == 2:
        value = int(suffix)
        if 2 <= value <= 10:
            return f"{suit_letter}{suffix}.jpg"
        return None
    if suffix == "pa":
        return f"{suit_letter}11.jpg"
    if suffix == "kn":
        return f"{suit_letter}12.jpg"
    if suffix == "qu":
        return f"{suit_letter}13.jpg"
    if suffix == "ki":
        return f"{suit_letter}14.jpg"
    return None
