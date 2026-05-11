from fastapi import APIRouter, HTTPException
from sqlalchemy import select, delete as sql_delete
from pydantic import BaseModel, Field
from typing import Optional
import uuid

from app.core.deps import CurrentUser, DB
from app.models.course import Course, CourseHole

router = APIRouter()


class CourseCreate(BaseModel):
    name: str
    club_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    cover_url: Optional[str] = None
    holes_count: int = 18
    par_total: Optional[int] = None
    course_rating: Optional[float] = None
    slope_rating: Optional[int] = None


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    club_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    cover_url: Optional[str] = None
    holes_count: Optional[int] = None
    par_total: Optional[int] = None
    course_rating: Optional[float] = None
    slope_rating: Optional[int] = None


class HoleData(BaseModel):
    hole_number: int = Field(ge=1, le=18)
    par: int = Field(ge=3, le=6)
    stroke_index: Optional[int] = Field(default=None, ge=1, le=18)
    distance_meters: Optional[int] = None
    distance_yards: Optional[int] = None
    distance_yards_black: Optional[int] = None
    distance_yards_blue: Optional[int] = None
    distance_yards_white: Optional[int] = None
    distance_yards_red: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    # GPS
    green_latitude: Optional[float] = None
    green_longitude: Optional[float] = None
    tee_latitude: Optional[float] = None
    tee_longitude: Optional[float] = None


def _course_to_dict(c: Course) -> dict:
    return {
        "id": str(c.id),
        "name": c.name,
        "description": c.description,
        "club_id": str(c.club_id) if c.club_id else None,
        "country": c.country,
        "city": c.city,
        "address": c.address,
        "latitude": float(c.latitude) if c.latitude is not None else None,
        "longitude": float(c.longitude) if c.longitude is not None else None,
        "cover_url": c.cover_url,
        "holes_count": c.holes_count,
        "par_total": c.par_total,
        "course_rating": float(c.course_rating) if c.course_rating is not None else None,
        "slope_rating": c.slope_rating,
        "is_active": c.is_active,
        "created_by": str(c.created_by) if c.created_by else None,
    }


def _hole_to_dict(h: CourseHole) -> dict:
    return {
        "hole_number": h.hole_number,
        "par": h.par,
        "stroke_index": h.stroke_index,
        "distance_meters": h.distance_meters,
        "distance_yards": h.distance_yards,
        "distance_yards_black": h.distance_yards_black,
        "distance_yards_blue": h.distance_yards_blue,
        "distance_yards_white": h.distance_yards_white,
        "distance_yards_red": h.distance_yards_red,
        "description": h.description,
        "image_url": h.image_url,
        "green_latitude": float(h.green_latitude) if h.green_latitude is not None else None,
        "green_longitude": float(h.green_longitude) if h.green_longitude is not None else None,
        "tee_latitude": float(h.tee_latitude) if h.tee_latitude is not None else None,
        "tee_longitude": float(h.tee_longitude) if h.tee_longitude is not None else None,
    }


async def _can_edit(course: Course, current_user, db) -> bool:
    """Solo el creador del campo o un superadmin puede editarlo. Para campos
    creados antes de la columna created_by (legacy), cualquier usuario autenticado
    puede editar."""
    if current_user.is_superadmin:
        return True
    if course.created_by is None:
        return True  # legacy course, anyone can claim/edit
    return str(course.created_by) == str(current_user.id)


@router.get("")
async def list_courses(db: DB, search: Optional[str] = None):
    query = select(Course).where(Course.is_active == True).order_by(Course.name)
    if search:
        query = query.where(Course.name.ilike(f"%{search}%"))
    result = await db.execute(query)
    courses = result.scalars().all()
    return [_course_to_dict(c) for c in courses]


@router.post("")
async def create_course(data: CourseCreate, current_user: CurrentUser, db: DB):
    course = Course(**data.model_dump(), created_by=current_user.id)
    db.add(course)
    await db.flush()
    return _course_to_dict(course)


@router.get("/{course_id}")
async def get_course(course_id: uuid.UUID, db: DB):
    result = await db.execute(select(Course).where(Course.id == course_id, Course.is_active == True))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Campo no encontrado")

    holes_result = await db.execute(
        select(CourseHole).where(CourseHole.course_id == course_id).order_by(CourseHole.hole_number)
    )
    holes = holes_result.scalars().all()

    data = _course_to_dict(course)
    data["holes"] = [_hole_to_dict(h) for h in holes]
    return data


@router.put("/{course_id}")
async def update_course(course_id: uuid.UUID, data: CourseUpdate, current_user: CurrentUser, db: DB):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course or not course.is_active:
        raise HTTPException(status_code=404, detail="Campo no encontrado")
    if not await _can_edit(course, current_user, db):
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este campo")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(course, field, value)
    await db.flush()
    return _course_to_dict(course)


@router.delete("/{course_id}")
async def delete_course(course_id: uuid.UUID, current_user: CurrentUser, db: DB):
    """Soft delete — marca el campo como inactivo. No borra los hoyos ni las rondas históricas."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Campo no encontrado")
    if not await _can_edit(course, current_user, db):
        raise HTTPException(status_code=403, detail="No tienes permiso para borrar este campo")
    course.is_active = False
    await db.flush()
    return {"message": "Campo desactivado", "id": str(course.id)}


@router.post("/{course_id}/holes")
async def set_course_holes(course_id: uuid.UUID, holes: list[HoleData], current_user: CurrentUser, db: DB):
    """Crea o actualiza hoyos en batch. Validación: stroke_index único 1-18."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Campo no encontrado")
    if not await _can_edit(course, current_user, db):
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este campo")

    # Validar SI único si vienen todos
    si_values = [h.stroke_index for h in holes if h.stroke_index is not None]
    if len(si_values) != len(set(si_values)):
        raise HTTPException(status_code=400, detail="Stroke Index duplicado entre hoyos")

    for h in holes:
        existing = await db.execute(
            select(CourseHole).where(CourseHole.course_id == course_id, CourseHole.hole_number == h.hole_number)
        )
        hole_row = existing.scalar_one_or_none()
        if hole_row:
            for field, value in h.model_dump(exclude_none=True).items():
                setattr(hole_row, field, value)
        else:
            db.add(CourseHole(course_id=course_id, **h.model_dump()))

    await db.flush()

    # Recalcular par_total si todos los hoyos están definidos
    all_holes_res = await db.execute(
        select(CourseHole).where(CourseHole.course_id == course_id)
    )
    all_holes = all_holes_res.scalars().all()
    if len(all_holes) == course.holes_count:
        course.par_total = sum(h.par for h in all_holes)
        await db.flush()

    return {"message": f"{len(holes)} hoyos actualizados", "par_total": course.par_total}


@router.put("/{course_id}/holes/{hole_number}")
async def update_single_hole(course_id: uuid.UUID, hole_number: int, data: HoleData, current_user: CurrentUser, db: DB):
    """Edita un solo hoyo (cómodo para correcciones puntuales)."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Campo no encontrado")
    if not await _can_edit(course, current_user, db):
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este campo")
    if data.hole_number != hole_number:
        raise HTTPException(status_code=400, detail="hole_number en URL y body no coinciden")

    existing = await db.execute(
        select(CourseHole).where(CourseHole.course_id == course_id, CourseHole.hole_number == hole_number)
    )
    hole_row = existing.scalar_one_or_none()
    if hole_row:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(hole_row, field, value)
    else:
        hole_row = CourseHole(course_id=course_id, **data.model_dump())
        db.add(hole_row)

    await db.flush()
    return _hole_to_dict(hole_row)
