import logging
from typing import Optional
import httpx
from ..config import settings

logger = logging.getLogger(__name__)

class WAHAService:
    """Outbound WAHA messaging service for ConvoHub.

    Mirrors the minimal functionality of the waha-integrator service so the
    adapter can actively push responses back to the WAHA instance instead of
    only returning JSON in the webhook response.
    """
    def __init__(self):
        self.base_url = settings.WAHA_BASE_URL.rstrip("/")
        self.api_key = settings.WAHA_API_KEY
        self.timeout = settings.WAHA_RESPONSE_TIMEOUT
        if not self.api_key:
            logger.warning("WAHA_API_KEY not configured - outbound WAHA messages may be rejected.")

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers

    async def send_text(self, session: str, chat_id: str, text: str) -> bool:
        """Send a text message via WAHA API.

        Returns True on success, False otherwise.
        """
        payload = {
            "session": session,
            "chatId": chat_id,
            "text": text,
        }
        try:
            timeout = httpx.Timeout(self.timeout)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{self.base_url}/api/sendText", headers=self._headers(), json=payload)
            if resp.status_code in (200, 201):
                logger.info(f"WAHA sendText success chat_id={chat_id}")
                return True
            logger.error(f"WAHA sendText failure status={resp.status_code} body={resp.text[:200]}")
            return False
        except httpx.TimeoutException:
            logger.error("Timeout sending WAHA message")
            return False
        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending WAHA message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending WAHA message: {e}")
            return False

    def is_available(self) -> bool:
        return bool(self.base_url and self.api_key)
