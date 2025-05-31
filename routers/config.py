from fastapi import APIRouter
from typing import List

router = APIRouter(prefix="/api/config", tags=["config"])

@router.get("/languages")
async def get_supported_languages():
    # This could be fetched from a database in a real application
    languages = [
        {"code": "en", "name": "English"},
        {"code": "am", "name": "Amharic"},
        {"code": "om", "name": "Oromo"},
        {"code": "ti", "name": "Tigrinya"}
    ]
    return languages