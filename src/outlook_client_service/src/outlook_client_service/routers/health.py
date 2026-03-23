"""Health-check route for the Outlook client service."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "ok"}
