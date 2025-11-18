import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timezone
import hashlib
import secrets

from database import db, create_document, get_documents
from schemas import User, BlogPost, ContactMessage

app = FastAPI(title="Workaround.io API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"name": "Workaround.io", "message": "API running", "tagline": "Don't work around the clock."}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# Utilities for auth

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 100_000)
    return salt, pwd_hash.hex()

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    token: str
    name: str
    email: EmailStr

# In a real app we'd use JWT. For this demo we'll mint a simple opaque token stored in DB.

@app.post("/auth/signup", response_model=AuthResponse)
def signup(payload: SignupRequest):
    existing = db["user"].find_one({"email": payload.email}) if db else None
    if existing:
        raise HTTPException(status_code=400, detail="Email already in use")
    salt, pwd_hash = hash_password(payload.password)
    user = User(name=payload.name, email=payload.email, password_hash=pwd_hash, password_salt=salt)
    user_id = create_document("user", user)
    token = secrets.token_hex(24)
    db["session"].insert_one({
        "user_id": user_id,
        "token": token,
        "created_at": datetime.now(timezone.utc)
    })
    return {"token": token, "name": user.name, "email": user.email}

@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    record = db["user"].find_one({"email": payload.email})
    if not record:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    salt = record.get("password_salt")
    _, verify_hash = hash_password(payload.password, salt)
    if verify_hash != record.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_hex(24)
    db["session"].insert_one({
        "user_id": str(record.get("_id")),
        "token": token,
        "created_at": datetime.now(timezone.utc)
    })
    return {"token": token, "name": record.get("name"), "email": record.get("email")}

# Marketing blog endpoints

@app.get("/blog", response_model=List[BlogPost])
def list_blog():
    docs = get_documents("blogpost", {}, limit=20)
    # Convert Mongo _id to string and ensure fields exist
    results: List[BlogPost] = []
    for d in docs:
        d.pop("_id", None)
        if not d.get("published_at"):
            d["published_at"] = None
        results.append(BlogPost(**d))
    return results

class BlogCreate(BaseModel):
    title: str
    slug: str
    excerpt: str
    content: str
    cover_image: Optional[str] = None
    tags: List[str] = []
    author: Optional[str] = None

@app.post("/blog")
def create_blog(payload: BlogCreate):
    post = BlogPost(**payload.model_dump())
    _id = create_document("blogpost", post)
    return {"id": _id}

# Contact form

class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str
    company: Optional[str] = None
    topic: Optional[str] = None

@app.post("/contact")
def submit_contact(payload: ContactRequest):
    msg = ContactMessage(**payload.model_dump())
    _id = create_document("contactmessage", msg)
    return {"id": _id, "status": "received"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
