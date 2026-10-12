
import logging
import os

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from authlib.integrations.starlette_client import OAuth
from access_token import create_access_token

load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter()

client_id = os.getenv("GOOGLE_CLIENT_ID_1")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET_1")

if not client_id or not client_secret:
    raise RuntimeError("Missing Google OAuth environment variables")

oauth = OAuth()

oauth.register(
    name="google",
    client_id=client_id,
    client_secret=client_secret,
    server_metadata_url=(
        "https://accounts.google.com/.well-known/openid-configuration"
    ),
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = str(request.url_for("google_callback"))

    result = await oauth.google.create_authorization_url(
        redirect_uri
    )

    await oauth.google.save_authorize_data(
        request,
        redirect_uri=redirect_uri,
        **result,
    )

    return {"login_url": result["url"]}


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        logger.exception("Google OAuth callback failed")
        raise HTTPException(
            status_code=400,
            detail="Google authentication failed.",
        )

    user_info = token.get("userinfo")

    if (
        not user_info
        or not user_info.get("sub")
        or not user_info.get("email")
        or not user_info.get("email_verified")
    ):
        raise HTTPException(
            status_code=401,
            detail="Google user information is invalid or unverified.",
        )

    access_token = create_access_token(
        user_id=user_info["sub"],
        email=user_info["email"],
    )

    return {
        "message": "Google login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": user_info["sub"],
            "email": user_info["email"],
            "name": user_info.get("name"),
        },
    }
    


@router.post("/google/logout")
async def google_logout(request: Request):
    if not request.session.get("user"):
        return {"message": "You are not logged in."}

    request.session.clear()
    return {"message": "Logout successful"}
