"""
Database Schemas for Workaround.io

Each Pydantic model maps to a MongoDB collection with the lowercase class name.
Examples:
- User -> "user"
- BlogPost -> "blogpost"
- ContactMessage -> "contactmessage"
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class User(BaseModel):
    """
    Users collection schema
    Fields for basic email/password auth. Passwords are stored hashed with a salt.
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password_hash: str = Field(..., description="Hashed password")
    password_salt: str = Field(..., description="Salt used to hash password")
    avatar: Optional[str] = Field(None, description="Optional avatar URL")
    role: str = Field("worker", description="Role: worker or admin")
    is_active: bool = Field(True, description="Whether user is active")

class BlogPost(BaseModel):
    """Blog posts for the marketing site"""
    title: str
    slug: str
    excerpt: str
    content: str
    cover_image: Optional[str] = None
    tags: List[str] = []
    published_at: Optional[datetime] = None
    author: Optional[str] = None

class ContactMessage(BaseModel):
    """Messages submitted from the contact form"""
    name: str
    email: EmailStr
    message: str
    company: Optional[str] = None
    topic: Optional[str] = Field(None, description="Reason for reaching out")
