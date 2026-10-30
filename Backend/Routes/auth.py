import sqlite3

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from Backend.Schemas.auth_schema import (
    RegisterRequest,
    LoginRequest
)

from Backend.services.auth_service import (
    create_user,
    authenticate_user,
    create_session,
    get_user_from_token,
    delete_session
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Please log in first."
        )

    user = get_user_from_token(credentials.credentials)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid login session."
        )

    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """No token -> None (anonymous). A token that is invalid or expired -> 401,
    so the frontend knows to send the user back to the login page instead of
    silently not saving their work."""

    if not credentials:
        return None

    user = get_user_from_token(credentials.credentials)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Your session has expired. Please log in again."
        )

    return user


@router.post("/register")
def register(data: RegisterRequest):

    name = data.name.strip()
    email = data.email.lower().strip()

    if len(name) < 2:
        raise HTTPException(
            status_code=422,
            detail="Please enter your name (at least 2 characters)."
        )

    try:
        user_id = create_user(name, email, data.password)

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="This email is already registered."
        )

    token = create_session(user_id)

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user_id,
            "name": name,
            "email": email
        }
    }


@router.post("/login")
def login(data: LoginRequest):

    user = authenticate_user(
        data.email,
        data.password
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password."
        )

    token = create_session(user["id"])

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    }


@router.get("/me")
def get_me(user=Depends(get_current_user)):
    # Never expose password_hash or internal session-related fields.
    return {
        "success": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    }


@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if not credentials:
        raise HTTPException(401, "Not logged in.")

    delete_session(credentials.credentials)

    return {
        "success": True,
        "message": "Logged out successfully."
    }