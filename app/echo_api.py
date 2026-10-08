import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent / "echo"))

import openai
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import current_user
from client import MODEL, EchoSession, api_key

log = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/echo", tags=["echo"])

_sessions = {}


class ChatRequest(BaseModel):
    message: str


@router.get("/status")
def status():
    return {"status": "ok", "key_set": bool(api_key()), "model": MODEL}


@router.post("/chat")
def chat(body: ChatRequest, user=Depends(current_user)):
    username = user["username"]
    session = _sessions.get(username)
    if session is None:
        try:
            session = EchoSession(username)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        _sessions[username] = session

    try:
        reply = session.ask(body.message)
    except openai.APIStatusError as exc:
        log.exception("echo: Gemini returned an error")
        code = 429 if exc.status_code == 429 else 502
        raise HTTPException(status_code=code, detail=f"Gemini error {exc.status_code}: {str(exc.message)[:300]}")
    except openai.APITimeoutError:
        log.exception("echo: Gemini request timed out")
        raise HTTPException(status_code=504, detail="Gemini did not answer in time, try again.")
    except openai.APIConnectionError as exc:
        log.exception("echo: could not reach Gemini")
        raise HTTPException(status_code=502, detail=f"could not reach Gemini: {exc}")
    except Exception as exc:
        log.exception("echo: unexpected failure")
        raise HTTPException(status_code=502, detail=f"echo backend error: {exc}")

    return {"reply": reply, "tools": session.last_tools}


@router.post("/reset")
def reset(user=Depends(current_user)):
    _sessions.pop(user["username"], None)
    return {"status": "reset"}
