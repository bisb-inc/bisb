from app.core.config import Settings
from app.providers.base import SourceProvider
from app.providers.gnews import GNewsProvider
from app.providers.mock import MockNewsProvider, MockXProvider


def configured_providers(settings: Settings) -> list[SourceProvider]:
    """Use live GNews when configured; keep X local and predictable for now."""
    api_key = settings.gnews_api_key
    has_api_key = bool(api_key and api_key.get_secret_value().strip())
    news_provider = GNewsProvider(api_key) if has_api_key and api_key else MockNewsProvider()
    return [news_provider, MockXProvider()]


__all__ = ["GNewsProvider", "MockNewsProvider", "MockXProvider", "configured_providers"]
