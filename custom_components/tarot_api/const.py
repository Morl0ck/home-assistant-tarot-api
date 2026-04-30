"""Constants for Tarot API integration."""

DOMAIN = "tarot_api"

CONF_BASE_URL = "base_url"
CONF_PROVIDER = "provider"

PROVIDER_EKELEN = "ekelen"
PROVIDER_KRATES = "krates"

DEFAULT_BASE_URL = "https://tarotapi.dev"

SIGNAL_CARD_UPDATED = "tarot_api_card_updated"

EKELEN_RANDOM_PATH = "/api/v1/cards/random"
KRATES_RANDOM_PATH = "/cards/onecard"

METABISMUTH_IMAGE_BASE = (
    "https://raw.githubusercontent.com/metabismuth/tarot-json/master/cards"
)

# Neutral card-back art so Picture entity cards always have an image URL before/during setup.
PLACEHOLDER_CARD_IMAGE = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/"
    "Card_back_red.svg/200px-Card_back_red.svg.png"
)
