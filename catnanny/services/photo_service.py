from datetime import datetime, timezone

from fastapi import UploadFile

from catnanny.config import PUBLIC_BASE_URL, UPLOAD_DIR
from catnanny.domain.models import Photo
from catnanny.storage.repositories import get_event, save_photo

MAX_PHOTO_BYTES = 8 * 1024 * 1024


class PhotoValidationError(ValueError):
    pass


def _image_suffix(content):
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    raise PhotoValidationError("Please choose a JPEG, PNG, or WebP image.")


def save_event_photo(event_id: str, upload: UploadFile) -> Photo:
    event = get_event(event_id)
    if event is None:
        raise ValueError(f"No event found for event_id={event_id}")

    content = upload.file.read(MAX_PHOTO_BYTES + 1)
    if not content or len(content) > MAX_PHOTO_BYTES:
        raise PhotoValidationError("The image must not be empty or exceed 8 MB.")
    suffix = _image_suffix(content)
    event_dir = UPLOAD_DIR / "events" / event_id
    event_dir.mkdir(parents=True, exist_ok=True)

    photo = Photo(
        event_id=event.event_id,
        household_id=event.household_id,
        cat_id=event.cat_id,
        url="",
        uploaded_at=datetime.now(timezone.utc),
    )
    target = event_dir / f"{photo.photo_id}{suffix}"
    with target.open("wb") as f:
        f.write(content)

    photo.url = f"{PUBLIC_BASE_URL}/uploads/events/{event_id}/{target.name}"
    return save_photo(photo)
