from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from pydantic import BaseModel
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
    holes_count: int = 18
    par_total: Optional[int] = None
    course_rating: Optional[float] = None
    slope_rating: Optional[int] = None


class HoleCreate(BaseModel):
    hole_number: int
    par: int
    stroke_index: Optional[int] = None
    distance_meters: Optional[int] = None
    distance_yards: Optional[int] = None
    distance_yards_black: Optional[int] = None
    distance_yards_blue: Optional[int] = None
    distance_yards_white: Optional[int] = None
    distance_yards_red: Optional[int] = None


@router.get("")
async def list_courses(db: DB, search: Optional[str] = None):
    query = select(Course).where(Course.is_active == True).order_by(Course.name)
    if search:
        query = query.where(Course.name.ilike(f"%{search}%"))
    result = await db.execute(query)
    courses = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "city": c.city,
            "country": c.country,
            "holes_count": c.holes_count,
            "par_total": c.par_total,
            "course_rating": float(c.course_rating) if c.course_rating else None,
            "slope_rating": c.slope_rating,
        }
        for c in courses
    ]


@router.post("")
async def create_course(data: CourseCreate, current_user: CurrentUser, db: DB):
    course = Course(**data.model_dump())
    db.add(course)
    await db.flush()
    return {"id": str(course.id), "name": course.name}


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

    return {
        "id": str(course.id),
        "name": course.name,
        "holes_count": course.holes_count,
        "par_total": course.par_total,
        "course_rating": float(course.course_rating) if course.course_rating else None,
        "slope_rating": course.slope_rating,
        "holes": [
            {
                "hole_number": h.hole_number,
                "par": h.par,
                "stroke_index": h.stroke_index,
                "distance_yards_black": h.distance_yards_black,
                "distance_yards_blue": h.distance_yards_blue,
                "distance_yards_white": h.distance_yards_white,
                "distance_yards_red": h.distance_yards_red,
            }
            for h in holes
        ],
    }


@router.post("/{course_id}/holes")
async def set_course_holes(course_id: uuid.UUID, holes: list[HoleCreate], current_user: CurrentUser, db: DB):
    result = await db.execute(select(Course).where(Course.id == course_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Campo no encontrado")

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

    return {"message": f"{len(holes)} hoyos actualizados"}
