"""
User-related Pydantic schemas for request/response validation
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# Base User schema
class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None


# Schema for user registration
class UserCreate(UserBase):
    """Schema for user registration request"""
    password: str = Field(..., min_length=8, max_length=100)


# Schema for user update
class UserUpdate(BaseModel):
    """Schema for user update request"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    finlab_api_token: Optional[str] = None
    is_active: Optional[bool] = None
    member_level: Optional[int] = Field(None, ge=0, le=6)
    cash: Optional[Decimal] = Field(None, ge=0)
    credit: Optional[Decimal] = Field(None, ge=0)


# Schema for user in database (with all fields)
class UserInDB(UserBase):
    """Schema for user as stored in database"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_superuser: bool
    member_level: int
    cash: Decimal
    credit: Decimal
    finlab_api_token: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None


# Schema for user response (public fields only)
class User(BaseModel):
    """Schema for user response (public fields)"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    member_level: int
    cash: Decimal
    credit: Decimal
    created_at: datetime
    last_login: Optional[datetime] = None


# Schema for login request
class UserLogin(BaseModel):
    """Schema for login request"""
    username: str
    password: str


# Schema for token response
class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# Schema for token payload
class TokenPayload(BaseModel):
    """Schema for JWT token payload"""
    sub: Optional[int] = None
    exp: Optional[int] = None
