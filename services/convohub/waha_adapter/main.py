import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from ..config import settings
from ..orchestrator import Orchestrator
from .waha_service import WAHAService

logger = logging.getLogger(__name__)
app = FastAPI(title="WAHA Adapter")

orchestrator = Orchestrator()
waha_service = WAHAService()

class WAHAWebhookReq(BaseModel):
    event: str
    session: str
    payload: Dict[str, Any]

@app.get("/healthz")
async def healthz():
    return {"ok": True, "waha_available": waha_service.is_available()}

@app.post("/webhook")
async def waha_webhook(req: WAHAWebhookReq):
    logger.info(f"Full request: {req.json()}")
    logger.info(f"Received webhook event: {req.event} for session {req.session}")
    if req.event != "message":
        logger.info("Ignoring non-message event")
        return {"status": "ignored"}

    body = (req.payload.get("body") or "").strip()
    chat_id = req.payload.get("from") or req.payload.get("chatId")
    if not body or not chat_id:
        logger.warning("Missing body or chat identifier; ignoring.")
        return {"status": "ignored"}

    logger.info(f"Processing message from {chat_id}: {body[:100]}")
    try:
        response_text = orchestrator.invoke(body)
        logger.debug(f"Orchestrator response: {response_text[:100]}")
    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")

    # Attempt outbound WAHA send
    send_ok = await waha_service.send_text(req.session, chat_id, response_text)
    if not send_ok:
        logger.error("Failed sending WAHA outbound message; returning locally only")
        return {"status": "error", "message": response_text, "details": "WAHA send failed"}

    resp = {"status": "sent", "message": response_text}
    logger.debug(f"WAHA response envelope: {resp}")
    return resp
