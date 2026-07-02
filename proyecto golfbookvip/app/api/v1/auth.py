from fastapi import APIRouter, HTTPException, Request, Response, status, BackgroundTasks
from sqlalchemy import select
from jose import JWTError
from datetime import datetime, timezone
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.deps import DB
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token, create_reset_token, verify_reset_token
from app.models.user import User
from app.models.handicap import PlayerStats
from app.models.club import Club, ClubMember
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, ForgotPasswordRequest, ResetPasswordRequest
from app.services.notifications import notify_user
from app.services.email_templates import tpl_password_reset, tpl_welcome_to_club
from app.services.mailer import send_email
from app.services.telegram_templates import tg_welcome_to_club
from app.services.plans import enforce_club_member_limit
import base64
from datetime import date

router = APIRouter()
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
RESET_MESSAGE = "Si el email está registrado, te enviamos un enlace de restablecimiento."


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=(settings.COOKIE_DOMAIN or None),
        path="/api/v1/auth",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        domain=(settings.COOKIE_DOMAIN or None),
        path="/api/v1/auth",
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(request: Request, response: Response, data: RegisterRequest, background_tasks: BackgroundTasks, db: DB):
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
    club_join_warning: str | None = None
    if data.club_code:
        code = data.club_code.strip().upper()
        club_res = await db.execute(select(Club).where(Club.invite_code == code, Club.is_active == True))
        club = club_res.scalar_one_or_none()
        if club:
            try:
                await enforce_club_member_limit(db, club)
            except HTTPException as exc:
                if exc.status_code != 402:
                    raise
                club_join_warning = "No se pudo vincular el club: límite de socios del plan alcanzado."
            else:
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
                # Notificación bienvenida (v1.20.0 + v1.21.0). Nota: Telegram aún no está
                # vinculado en este momento (el usuario acaba de registrarse), pero el
                # template se pasa por si en el futuro lo vincula y aún tiene la notification.
                panel_url = f"https://golfbookvip.com/es/club/{club.id}"
                invite_link = f"https://golfbookvip.com/es/join-club/{club.invite_code}" if club.invite_code else None
                user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
                subject, html = tpl_welcome_to_club(user_name, club.name, panel_url, invite_link)
                tg_text = tg_welcome_to_club(user_name, club.name, panel_url, invite_link)
                await notify_user(
                    db, user.id, "welcome_club",
                    f"Bienvenido a {club.name}",
                    "Te registraste a través del link de invitación. Visita tu panel del club.",
                    data={"club_id": str(club.id)},
                    email_subject=subject, email_html=html,
                    telegram_text=tg_text,
                    background_tasks=background_tasks,
                )
        else:
            club_join_warning = "Código de club inválido."
        # Si el código es inválido, registramos al usuario sin fallar; el frontend muestra warning

    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    _set_refresh_cookie(response, refresh)
    return TokenResponse(
        access_token=access, refresh_token=refresh,
        joined_club_id=joined_club_id, joined_club_name=joined_club_name,
        club_join_warning=club_join_warning,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, response: Response, data: LoginRequest, db: DB):
    result = await db.execute(select(User).where(User.email == data.email, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    user.last_login = datetime.now(timezone.utc)

    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, response: Response, db: DB, data: RefreshRequest | None = None):
    refresh = request.cookies.get(settings.REFRESH_COOKIE_NAME) or (data.refresh_token if data else None)
    if not refresh:
        raise HTTPException(status_code=401, detail="Token inválido")
    try:
        payload = decode_token(refresh)
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
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout")
async def logout(response: Response):
    _clear_refresh_cookie(response)
    return {"message": "ok"}


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(request: Request, data: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: DB):
    """Send a password reset link without leaking account existence."""
    result = await db.execute(select(User).where(User.email == data.email, User.is_active == True))
    user = result.scalar_one_or_none()
    if user:
        token = create_reset_token(str(user.id), user.password_hash)
        reset_url = f"https://golfbookvip.com/es/auth/reset-password?token={token}"
        user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
        subject, html = tpl_password_reset(user_name, reset_url)
        background_tasks.add_task(send_email, user.email, subject, html)
    return {"message": RESET_MESSAGE}


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
