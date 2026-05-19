from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from jose import JWTError
from datetime import datetime, timezone

from app.core.deps import DB
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token, create_reset_token, verify_reset_token
from app.models.user import User
from app.models.handicap import PlayerStats
from app.models.club import Club, ClubMember
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, ForgotPasswordRequest, ResetPasswordRequest
import base64
from datetime import date

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: DB):
    # Verificar duplicados
    existing = await db.execute(
        select(User).where((User.email == data.email) | (User.username == data.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email o username ya registrado")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        username=data.username,
        phone=data.phone,
        initial_handicap=data.initial_handicap,
        handicap_index=data.initial_handicap,
    )
    db.add(user)
    await db.flush()

    # Crear registro de estadísticas vacío
    stats = PlayerStats(user_id=user.id)
    db.add(stats)

    # Si el registro viene con club_code, vincular como ClubMember (escenario A — v1.16.0)
    joined_club_id: str | None = None
    joined_club_name: str | None = None
    if data.club_code:
        code = data.club_code.strip().upper()
        club_res = await db.execute(select(Club).where(Club.invite_code == code, Club.is_active == True))
        club = club_res.scalar_one_or_none()
        if club:
            member = ClubMember(
                club_id=club.id,
                user_id=user.id,
                membership_type_id=club.default_membership_type_id,
                joined_at=date.today(),
                status="active",
                onboarding_source="invite_link",
            )
            db.add(member)
            joined_club_id = str(club.id)
            joined_club_name = club.name
        # Si el código es inválido, registramos al usuario sin fallar; el frontend muestra warning

    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenResponse(
        access_token=access, refresh_token=refresh,
        joined_club_id=joined_club_id, joined_club_name=joined_club_name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: DB):
    result = await db.execute(select(User).where(User.email == data.email, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    user.last_login = datetime.now(timezone.utc)

    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest, db: DB):
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token inválido")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expirado o inválido")

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    access = create_access_token(user_id)
    new_refresh = create_refresh_token(user_id)
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: DB):
    """Generate a password reset token. Returns the token directly (email SMTP not configured yet)."""
    result = await db.execute(select(User).where(User.email == data.email, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        # Don't reveal whether email exists — but since no SMTP, show generic message
        return {"token": None, "message": "Si el email está registrado, copia el enlace de restablecimiento."}
    token = create_reset_token(str(user.id), user.password_hash)
    # TODO: send via email when SMTP is configured. For now the frontend displays the link.
    return {"token": token, "message": "Enlace generado correctamente"}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: DB):
    """Validate the reset token and update the password."""
    # Decode user_id from token to fetch the current password_hash for HMAC verification
    try:
        raw = base64.urlsafe_b64decode(data.token.encode()).decode()
        _, user_id, _ = raw.split(":", 2)
    except Exception:
        raise HTTPException(status_code=400, detail="Token inválido")

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido")

    if not verify_reset_token(data.token, user.password_hash):
        raise HTTPException(status_code=400, detail="Token expirado o inválido. Solicita uno nuevo.")

    user.password_hash = hash_password(data.new_password)
    return {"message": "Contraseña actualizada correctamente"}
