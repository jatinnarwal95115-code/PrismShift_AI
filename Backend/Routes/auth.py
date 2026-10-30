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


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Return the authenticated user, or None when no bearer token is sent.

    Reality and Digital generation are usable without an account; when a
    token is supplied it must still be valid.
    """
    if not credentials:
        return None

    user = get_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid login session."
        )

    return user


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


@router.post("/register")
def register(data: RegisterRequest):

    try:
        user_id = create_user(
            data.name,
            data.email,
            data.password
        )

    except Exception as error:
        if "UNIQUE constraint failed" in str(error):
            raise HTTPException(
                status_code=409,
                detail="This email is already registered."
            )
        raise

    token = create_session(user_id)

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user_id,
            "name": data.name,
            "email": data.email
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