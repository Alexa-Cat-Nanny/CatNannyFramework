from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

STATIC_DIR = Path(__file__).parent / "static"
router = APIRouter(include_in_schema=False)


@router.get("/")
def home():
    return RedirectResponse("/simulator")


@router.get("/simulator")
def simulator():
    return FileResponse(STATIC_DIR / "simulator.html")


@router.get("/photos/upload")
def upload_page():
    return FileResponse(STATIC_DIR / "upload.html")
