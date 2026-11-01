"""Authentication schemas."""
from datetime import datetime
from typing import Annotated, Optional
from pydantic import BaseModel, StringConstraints, Field, ConfigDict

# Robust email validator supporting standard domains as well as local dev/test domains (.local, .internal)
EmailAddress = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
    ),
]


class UserRegisterRequest(BaseModel):
    email: EmailAddress
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    role: Optional[str] = Field(default="engineer", pattern="^(admin|engineer|viewer)$")


class UserLoginRequest(BaseModel):
    email: EmailAddress
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: EmailAddress
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
