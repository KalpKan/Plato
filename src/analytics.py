"""Server-side PostHog events (pdf_uploaded, pdf_parsed, ics_downloaded).

Everything here is a no-op unless POSTHOG_API_KEY is set, so local runs and
tests never talk to the network. The key is the public project token that
also ships in the browser snippet; it is not a secret.
"""
import os
from typing import Any, Dict, Optional

_client = None


def _get_client():
    """Lazily build the posthog client; None when analytics is off."""
    global _client
    key = os.getenv("POSTHOG_API_KEY")
    if not key:
        return None
    if _client is None:
        from posthog import Posthog
        _client = Posthog(
            project_api_key=key,
            host=os.getenv("POSTHOG_HOST", "https://us.i.posthog.com"),
            sync_mode=True,  # serverless: send before the response returns
        )
    return _client


def capture(distinct_id: Optional[str], event: str, properties: Optional[Dict[str, Any]] = None) -> bool:
    """Send one event. Returns True when it was handed to PostHog, False when off/failed."""
    client = _get_client()
    if client is None:
        return False
    try:
        client.capture(distinct_id=distinct_id or "anonymous", event=event,
                       properties={**(properties or {}), "app": "plato"})
        return True
    except Exception:
        return False
