import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from agents import SQLiteSession, Runner
from agent import create_agent
from google_auth import router as google_router

load_dotenv()

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

secret_key = os.getenv("SESSION_SECRET")

if not secret_key:
    raise RuntimeError("SESSION_SECRET is missing")

app.add_middleware(
    SessionMiddleware,
    secret_key=secret_key,
    same_site="lax",
    https_only=os.getenv("COOKIE_SECURE", "false").lower() == "true",
)

# Register Google OAuth routes.
app.include_router(google_router)


class ChatRequest(BaseModel):
    question: str
    





@app.get("/me")
async def get_current_user(request: Request):
    user = request.session.get("user")

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Please log in with Google first.",
        )

    return {"user": user}


@app.post("/chat")
async def chat(payload: ChatRequest, request: Request):
    user = request.session.get("user")

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Please log in with Google first.",
        )

    if not payload.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    # Use Google's stable user ID, not a client-supplied user_id.
    user_id = user["user_id"]

    async def generate():
        try:
            agent = create_agent(user_id=user_id)

            memory = SQLiteSession(
                session_id=user_id,
            )

            result = Runner.run_streamed(
                agent,
                payload.question,
                session=memory,
            )

            async for event in result.stream_events():
                if event.type == "raw_response_event":
                    data = event.data

                    if data.type == "response.output_text.delta":
                        yield data.delta

        except Exception:
            logger.exception(
                "Agent streaming failed for user: %s",
                user_id,
            )
            yield "\n\nSorry, something went wrong."

    return StreamingResponse(
        generate(),
        media_type="text/plain",
    )
