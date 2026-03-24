"""Pydantic schemas for event requests and responses."""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class EventResponse(BaseModel):
    """Response model for an event."""

    id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    location: str | None = None
    description: str | None = None


class EventCreateRequest(BaseModel):
    """Request model for creating an event."""

    title: str = Field(..., min_length=1)
    starts_at: datetime
    ends_at: datetime
    location: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def validate_time_order(self) -> "EventCreateRequest":
        """Validate that ends_at is later than starts_at."""
        if self.ends_at <= self.starts_at:
            message = "ends_at must be later than starts_at."
            raise ValueError(message)
        return self


class EventUpdateRequest(BaseModel):
    """Request model for updating an event (partial update)."""

    title: str | None = Field(default=None, min_length=1)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "EventUpdateRequest":
        """Validate that the patch contains at least one field and valid time order."""
        if all(
            value is None
            for value in (
                self.title,
                self.starts_at,
                self.ends_at,
                self.location,
                self.description,
            )
        ):
            message = "At least one field must be provided for update."
            raise ValueError(message)

        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at <= self.starts_at
        ):
            message = "ends_at must be later than starts_at."
            raise ValueError(message)

        return self
