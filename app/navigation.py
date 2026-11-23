"""Small, exact endpoint groups used by the responsive navigation."""

from types import MappingProxyType


_ENDPOINT_SECTIONS = MappingProxyType({
    "main.home": "home",
    "market.browse": "explore",
    "market.detail": "explore",
    "market.seller_profile": "explore",
    "market.create_listing": "sell",
    "market.edit_listing": "sell",
    "market.preview": "sell",
    "market.own_listings": "sell",
    "engagement.inbox": "messages",
    "engagement.thread": "messages",
    "auth.profile": "profile",
    "engagement.dashboard": "profile",
    "engagement.saved": "profile",
    "cart.review": "profile",
})


def mobile_nav_section(endpoint):
    """Return the one mobile section for an exact Flask endpoint, if any."""
    return _ENDPOINT_SECTIONS.get(endpoint)
