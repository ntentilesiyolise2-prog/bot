from fastapi import APIRouter
from ai.learning.lesson_db import LessonManager

router = APIRouter()
lesson_manager = LessonManager()

@router.get("/api/learning/lessons")
async def get_lessons(level: str = "beginner"):
    return LESSONS.get(level, [])

@router.get("/api/learning/next")
async def get_next_lesson(level: str, current_id: int):
    next_lesson = lesson_manager.get_next_lesson(level, current_id)
    if next_lesson:
        return next_lesson
    return {"message": "No more lessons"}

@router.post("/api/learning/complete")
async def mark_complete(user_id: str, lesson_id: int):
    progress = lesson_manager.mark_complete(user_id, lesson_id)
    return progress
