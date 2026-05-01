from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
import re
from datetime import datetime, timezone, timedelta
import httpx
import base64
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'unison_ratings')]

# Spotify credentials
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')

# Spotify client - will be initialized lazily
_spotify_client = None
USE_MOCK_DATA = False  # Using real Spotify API now!

# Mock data for testing
MOCK_ALBUMS = [
    {
        "id": "mock_abbey_road",
        "name": "Abbey Road",
        "artist": "The Beatles",
        "artwork": "https://i.scdn.co/image/ab67616d0000b273dc30583ba717007b00cceb25",
        "release_date": "1969-09-26",
        "total_tracks": 17
    },
    {
        "id": "mock_thriller",
        "name": "Thriller",
        "artist": "Michael Jackson",
        "artwork": "https://i.scdn.co/image/ab67616d0000b27343656f978c0d77d1dd1c6a09",
        "release_date": "1982-11-30",
        "total_tracks": 9
    },
    {
        "id": "mock_dark_side",
        "name": "The Dark Side of the Moon",
        "artist": "Pink Floyd",
        "artwork": "https://i.scdn.co/image/ab67616d0000b273ea7caaff71dea1051d49b2fe",
        "release_date": "1973-03-01",
        "total_tracks": 10
    },
    {
        "id": "mock_rumours",
        "name": "Rumours",
        "artist": "Fleetwood Mac",
        "artwork": "https://i.scdn.co/image/ab67616d0000b273e52a59a28efa4773dd2bfe1b",
        "release_date": "1977-02-04",
        "total_tracks": 11
    },
    {
        "id": "mock_nevermind",
        "name": "Nevermind",
        "artist": "Nirvana",
        "artwork": "https://i.scdn.co/image/ab67616d0000b2739ca50874c03fb8ef4c7da4b9",
        "release_date": "1991-09-24",
        "total_tracks": 12
    },
    {
        "id": "mock_back_to_black",
        "name": "Back to Black",
        "artist": "Amy Winehouse",
        "artwork": "https://i.scdn.co/image/ab67616d0000b27376ffb5b5ab045d22c81235c1",
        "release_date": "2006-10-27",
        "total_tracks": 11
    },
    {
        "id": "mock_good_kid",
        "name": "good kid, m.A.A.d city",
        "artist": "Kendrick Lamar",
        "artwork": "https://i.scdn.co/image/ab67616d0000b2736b85cdbf28d5b2e0e96a1b08",
        "release_date": "2012-10-22",
        "total_tracks": 12
    },
    {
        "id": "mock_lemonade",
        "name": "Lemonade",
        "artist": "Beyoncé",
        "artwork": "https://i.scdn.co/image/ab67616d0000b2737ec5d4579b65f74579e2ae52",
        "release_date": "2016-04-23",
        "total_tracks": 12
    },
    {
        "id": "mock_blonde",
        "name": "Blonde",
        "artist": "Frank Ocean",
        "artwork": "https://i.scdn.co/image/ab67616d0000b273c5649add07ed3720be9d5526",
        "release_date": "2016-08-20",
        "total_tracks": 17
    },
    {
        "id": "mock_1989",
        "name": "1989",
        "artist": "Taylor Swift",
        "artwork": "https://i.scdn.co/image/ab67616d0000b2739abdf14e6058bd3903686148",
        "release_date": "2014-10-27",
        "total_tracks": 13
    }
]

MOCK_ALBUM_DETAILS = {
    "mock_abbey_road": {
        "id": "mock_abbey_road",
        "name": "Abbey Road",
        "artist": "The Beatles",
        "artists": ["The Beatles"],
        "artwork": "https://i.scdn.co/image/ab67616d0000b273dc30583ba717007b00cceb25",
        "release_date": "1969-09-26",
        "release_year": "1969",
        "total_tracks": 17,
        "tracks": [
            {"id": "t1", "name": "Come Together", "track_number": 1, "duration": "4:20", "artists": ["The Beatles"]},
            {"id": "t2", "name": "Something", "track_number": 2, "duration": "3:03", "artists": ["The Beatles"]},
            {"id": "t3", "name": "Maxwell's Silver Hammer", "track_number": 3, "duration": "3:27", "artists": ["The Beatles"]},
            {"id": "t4", "name": "Oh! Darling", "track_number": 4, "duration": "3:27", "artists": ["The Beatles"]},
            {"id": "t5", "name": "Octopus's Garden", "track_number": 5, "duration": "2:51", "artists": ["The Beatles"]},
            {"id": "t6", "name": "I Want You (She's So Heavy)", "track_number": 6, "duration": "7:47", "artists": ["The Beatles"]},
            {"id": "t7", "name": "Here Comes the Sun", "track_number": 7, "duration": "3:06", "artists": ["The Beatles"]},
            {"id": "t8", "name": "Because", "track_number": 8, "duration": "2:45", "artists": ["The Beatles"]},
        ],
        "genres": ["rock", "british invasion"],
        "label": "Apple Records",
        "popularity": 85
    },
    "mock_thriller": {
        "id": "mock_thriller",
        "name": "Thriller",
        "artist": "Michael Jackson",
        "artists": ["Michael Jackson"],
        "artwork": "https://i.scdn.co/image/ab67616d0000b27343656f978c0d77d1dd1c6a09",
        "release_date": "1982-11-30",
        "release_year": "1982",
        "total_tracks": 9,
        "tracks": [
            {"id": "t1", "name": "Wanna Be Startin' Somethin'", "track_number": 1, "duration": "6:03", "artists": ["Michael Jackson"]},
            {"id": "t2", "name": "Baby Be Mine", "track_number": 2, "duration": "4:20", "artists": ["Michael Jackson"]},
            {"id": "t3", "name": "The Girl Is Mine", "track_number": 3, "duration": "3:42", "artists": ["Michael Jackson", "Paul McCartney"]},
            {"id": "t4", "name": "Thriller", "track_number": 4, "duration": "5:57", "artists": ["Michael Jackson"]},
            {"id": "t5", "name": "Beat It", "track_number": 5, "duration": "4:18", "artists": ["Michael Jackson"]},
            {"id": "t6", "name": "Billie Jean", "track_number": 6, "duration": "4:54", "artists": ["Michael Jackson"]},
            {"id": "t7", "name": "Human Nature", "track_number": 7, "duration": "4:06", "artists": ["Michael Jackson"]},
            {"id": "t8", "name": "P.Y.T. (Pretty Young Thing)", "track_number": 8, "duration": "3:59", "artists": ["Michael Jackson"]},
            {"id": "t9", "name": "The Lady in My Life", "track_number": 9, "duration": "4:59", "artists": ["Michael Jackson"]},
        ],
        "genres": ["pop", "r&b"],
        "label": "Epic",
        "popularity": 90
    }
}

def get_spotify_client():
    """Get or create Spotify client with fresh token"""
    global _spotify_client
    try:
        # Always create fresh auth manager to ensure valid token
        auth_manager = SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        )
        _spotify_client = spotipy.Spotify(auth_manager=auth_manager)
        return _spotify_client
    except Exception as e:
        logger.error(f"Failed to create Spotify client: {e}")
        raise

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ======================= Constants =======================
SCORE_OPTIONS = [
    {"value": 0.0, "label": "Worthless"},
    {"value": 1.0, "label": "Terrible and symptomatic of some kind of larger problem in music or the world"},
    {"value": 2.0, "label": "Terrible"},
    {"value": 3.0, "label": "Really bad. Incompetent and thoughtless"},
    {"value": 4.0, "label": "Pretty bad"},
    {"value": 5.0, "label": "Not very good, but not a total disaster"},
    {"value": 5.6, "label": "Decent record, a few things going on for it, but a handful of major issues overwhelm the experience"},
    {"value": 6.0, "label": "Pretty good, not great, some unavoidable issues, but interesting. Fans of the band or genre will get the most out of it"},
    {"value": 6.6, "label": "Good record, a few issues, but worth your attention if you're into the band or genre. Maybe starts strong and fades a little by the end, includes a few songs that don't move the needle, but also has a handful of outstanding moments"},
    {"value": 7.0, "label": "Very good record, recommend checking it out. Hardly a dull moment, a great hang, maybe plays it safe but executes everything very well, maybe takes some risks but doesn't land everything perfectly"},
    {"value": 7.6, "label": "Excellent record, highly recommended. 'Best in class' for its genre. Not a bad song on it"},
    {"value": 8.0, "label": "Essential listening, among the best records of the year. Shows a mastery of craft or taps into the sublime, feels a part of the zeitgeist, steps out of its genre, takes big risks that pay off"},
    {"value": 8.6, "label": "A major statement, worthy of your time and energy, no matter your taste. Transcends genre, claims new ground, a total and intentional work of art, possesses an aura that makes it vital to its genre, its era, or the artist's career"},
    {"value": 9.1, "label": "A monument, an instant classic. Sounds ahead of its time, sounds timeless, immediately belongs in the canon. Entire genres could be created in its wake"},
    {"value": 10.0, "label": "A masterpiece, one of the best albums of all time. Will be culturally and aesthetically important many years from now in some way"},
]

TAG_OPTIONS = ["lyrics", "production", "track list", "features", "instrumentals", "melodies", "beats"]

# ======================= Models =======================
class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    user_tag: Optional[str] = None
    password_hash: Optional[str] = None  # Only for email/password auth
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Rating(BaseModel):
    rating_id: str = Field(default_factory=lambda: f"rating_{uuid.uuid4().hex[:12]}")
    user_id: str
    album_id: str  # Spotify album ID
    album_name: str
    artist_name: str
    album_artwork: Optional[str] = None  # URL or base64
    release_year: Optional[str] = None
    score: float
    tags: List[str] = Field(default_factory=list, max_length=3)
    headline: str = Field(max_length=300)
    favorite_tracks: List[dict] = Field(default_factory=list)  # Up to 3 tracks: [{id, name, track_number}]
    least_favorite_tracks: List[dict] = Field(default_factory=list)  # Up to 2 tracks: [{id, name, track_number}]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RatingCreate(BaseModel):
    album_id: str
    album_name: str
    artist_name: str
    album_artwork: Optional[str] = None
    release_year: Optional[str] = None
    score: float
    tags: List[str] = Field(default_factory=list)
    headline: str = Field(max_length=300)
    favorite_tracks: List[dict] = Field(default_factory=list)  # Up to 3 tracks
    least_favorite_tracks: List[dict] = Field(default_factory=list)  # Up to 2 tracks

class RatingUpdate(BaseModel):
    score: Optional[float] = None
    tags: Optional[List[str]] = None
    headline: Optional[str] = None
    favorite_tracks: Optional[List[dict]] = None
    least_favorite_tracks: Optional[List[dict]] = None

class ProfileUpdate(BaseModel):
    user_tag: Optional[str] = None
    profile_picture: Optional[str] = None  # base64 encoded image

class FavoriteAlbum(BaseModel):
    album_id: str
    album_name: str
    artist_name: str
    album_artwork: Optional[str] = None

class FavoritesUpdate(BaseModel):
    favorites: List[FavoriteAlbum] = Field(default_factory=list)  # Up to 5 albums

class EmailPasswordRegister(BaseModel):
    email: str
    password: str
    name: str

class EmailPasswordLogin(BaseModel):
    email: str
    password: str

class UserTagUpdate(BaseModel):
    user_tag: str

# ======================= Auth Helper =======================
async def get_current_user(request: Request) -> User:
    """Extract and verify user from session token"""
    # Try cookie first
    session_token = request.cookies.get("session_token")
    
    # Fallback to Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Find session
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiry
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Get user
    user_doc = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    return User(**user_doc)

# ======================= Auth Endpoints =======================
@api_router.post("/auth/session")
async def exchange_session(request: Request, response: Response):
    """Exchange session_id from Emergent Auth for session_token"""
    body = await request.json()
    session_id = body.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    # Call Emergent Auth to get user data
    async with httpx.AsyncClient() as client:
        auth_response = await client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        )
        
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session_id")
        
        user_data = auth_response.json()
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    email = user_data.get("email")
    name = user_data.get("name", "")
    picture = user_data.get("picture", "")
    session_token = user_data.get("session_token")
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing_user:
        user_id = existing_user["user_id"]
        # Update user data
        await db.users.update_one(
            {"email": email},
            {"$set": {"name": name, "picture": picture}}
        )
    else:
        # Create new user
        new_user = User(
            user_id=user_id,
            email=email,
            name=name,
            picture=picture
        )
        await db.users.insert_one(new_user.model_dump())
    
    # Create session
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at
    )
    
    # Delete old sessions for this user
    await db.user_sessions.delete_many({"user_id": user_id})
    
    # Insert new session
    await db.user_sessions.insert_one(session.model_dump())
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    # Get full user data
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    # Check if user needs onboarding (no user_tag set)
    needs_onboarding = not user_doc.get("user_tag")
    
    return {"user": user_doc, "session_token": session_token, "needs_onboarding": needs_onboarding}

@api_router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user"""
    return user.model_dump()

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    session_token = request.cookies.get("session_token")
    
    if session_token:
        await db.user_sessions.delete_many({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}

@api_router.post("/auth/apple")
async def apple_auth(request: Request, response: Response):
    """Authenticate with Apple Sign In"""
    import jwt
    
    body = await request.json()
    identity_token = body.get("identityToken")
    user_identifier = body.get("user")  # Apple's unique user ID
    email = body.get("email")  # Only provided on first sign-in
    full_name = body.get("fullName")  # Only provided on first sign-in
    
    if not identity_token or not user_identifier:
        raise HTTPException(status_code=400, detail="identityToken and user are required")
    
    # Decode the Apple identity token (without full verification for now - 
    # Apple's token is signed by Apple and contains the user's info)
    try:
        # Decode without verification to extract claims
        # In production, verify with Apple's public keys
        decoded = jwt.decode(identity_token, options={"verify_signature": False})
        token_email = decoded.get("email")
        token_sub = decoded.get("sub")  # Apple user ID
    except Exception as e:
        logger.error(f"Apple token decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid Apple identity token")
    
    # Use email from token if not provided in body
    if not email:
        email = token_email
    
    if not email:
        # Apple "Hide My Email" - generate a placeholder with Apple user ID
        email = f"apple_{user_identifier[:12]}@privaterelay.appleid.com"
    
    # Build name from fullName object
    name = ""
    if full_name:
        given = full_name.get("givenName") or ""
        family = full_name.get("familyName") or ""
        name = f"{given} {family}".strip()
    
    # Check if user exists by Apple user identifier or email
    existing_user = await db.users.find_one(
        {"$or": [{"apple_user_id": user_identifier}, {"email": email}]},
        {"_id": 0}
    )
    
    if existing_user:
        user_id = existing_user["user_id"]
        # Update Apple user ID if not set
        update_fields = {"apple_user_id": user_identifier}
        if name and not existing_user.get("name"):
            update_fields["name"] = name
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": update_fields}
        )
    else:
        # Create new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        new_user_data = {
            "user_id": user_id,
            "email": email,
            "name": name or "Apple User",
            "picture": None,
            "apple_user_id": user_identifier,
            "created_at": datetime.now(timezone.utc),
        }
        await db.users.insert_one(new_user_data)
    
    # Create session
    session_token = f"apple_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at
    )
    
    # Delete old sessions for this user
    await db.user_sessions.delete_many({"user_id": user_id})
    
    # Insert new session
    await db.user_sessions.insert_one(session.model_dump())
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    # Get full user data
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    # Check if user needs onboarding (no user_tag set)
    needs_onboarding = not user_doc.get("user_tag")
    
    return {"user": user_doc, "session_token": session_token, "needs_onboarding": needs_onboarding}

@api_router.post("/auth/register")
async def register_with_email(data: EmailPasswordRegister, response: Response):
    """Register with email and password"""
    email = data.email.lower().strip()
    password = data.password
    name = data.name.strip()
    
    # Validate email format
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Validate password strength
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Validate name
    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
    
    # Check if user already exists
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create new user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    new_user = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": None,
        "user_tag": None,  # Will be set in onboarding
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc)
    }
    await db.users.insert_one(new_user)
    
    # Create session
    session_token = f"email_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at
    )
    
    await db.user_sessions.insert_one(session.model_dump())
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    # Get full user data (exclude password_hash)
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    
    return {"user": user_doc, "session_token": session_token, "needs_onboarding": True}

@api_router.post("/auth/login")
async def login_with_email(data: EmailPasswordLogin, response: Response):
    """Login with email and password"""
    email = data.email.lower().strip()
    password = data.password
    
    # Find user
    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if user has password_hash (might be OAuth-only user)
    if not user_doc.get("password_hash"):
        raise HTTPException(status_code=400, detail="This account uses social login. Please sign in with Google or Apple")
    
    # Verify password
    if not bcrypt.checkpw(password.encode('utf-8'), user_doc["password_hash"].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user_id = user_doc["user_id"]
    
    # Create session
    session_token = f"email_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at
    )
    
    # Delete old sessions for this user
    await db.user_sessions.delete_many({"user_id": user_id})
    
    # Insert new session
    await db.user_sessions.insert_one(session.model_dump())
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    # Get full user data (exclude password_hash)
    user_doc_clean = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    
    # Check if user needs onboarding (no user_tag set)
    needs_onboarding = not user_doc_clean.get("user_tag")
    
    return {"user": user_doc_clean, "session_token": session_token, "needs_onboarding": needs_onboarding}

@api_router.post("/auth/onboarding/user-tag")
async def set_user_tag_onboarding(data: UserTagUpdate, user: User = Depends(get_current_user)):
    """Set user tag during onboarding (first-time setup)"""
    tag = data.user_tag.strip().lower()
    
    # Validate tag
    if not tag or len(tag) < 3:
        raise HTTPException(status_code=400, detail="User tag must be at least 3 characters")
    
    if len(tag) > 20:
        raise HTTPException(status_code=400, detail="User tag must be at most 20 characters")
    
    if not re.match(r'^[a-z0-9_]+$', tag):
        raise HTTPException(status_code=400, detail="User tag can only contain lowercase letters, numbers, and underscores")
    
    # Check if tag is taken
    existing = await db.users.find_one({"user_tag": tag, "user_id": {"$ne": user.user_id}}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="This user tag is already taken")
    
    # Update user tag
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": {"user_tag": tag}}
    )
    
    # Get updated user data
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0, "password_hash": 0})
    
    return {"user": user_doc, "message": "User tag set successfully"}

# ======================= Profile Endpoints =======================
@api_router.get("/profile/me")
async def get_my_profile(user: User = Depends(get_current_user)):
    """Get current user's full profile"""
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get friend count (people following me)
    followers_count = await db.friends.count_documents({"following_id": user.user_id})
    following_count = await db.friends.count_documents({"follower_id": user.user_id})
    ratings_count = await db.ratings.count_documents({"user_id": user.user_id})
    
    return {
        **user_doc,
        "followers_count": followers_count,
        "following_count": following_count,
        "ratings_count": ratings_count,
    }

@api_router.put("/profile/tag")
async def update_user_tag(request: Request, user: User = Depends(get_current_user)):
    """Update user tag (unique username)"""
    body = await request.json()
    tag = body.get("user_tag", "").strip().lower()
    
    if not tag:
        raise HTTPException(status_code=400, detail="Tag is required")
    
    # Validate tag format: alphanumeric, underscores, dots, 3-20 chars
    if not re.match(r'^[a-z0-9_.]{3,20}$', tag):
        raise HTTPException(status_code=400, detail="Tag must be 3-20 characters, only lowercase letters, numbers, underscores, and dots")
    
    # Check uniqueness
    existing = await db.users.find_one({"user_tag": tag, "user_id": {"$ne": user.user_id}}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=409, detail="This tag is already taken")
    
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": {"user_tag": tag}}
    )
    
    return {"user_tag": tag, "message": "Tag updated successfully"}

@api_router.get("/profile/check-tag/{tag}")
async def check_tag_availability(tag: str, user: User = Depends(get_current_user)):
    """Check if a user tag is available"""
    tag = tag.strip().lower()
    
    if not re.match(r'^[a-z0-9_.]{3,20}$', tag):
        return {"available": False, "reason": "Invalid format"}
    
    existing = await db.users.find_one({"user_tag": tag, "user_id": {"$ne": user.user_id}}, {"_id": 0})
    return {"available": existing is None}

@api_router.put("/profile/picture")
async def update_profile_picture(request: Request, user: User = Depends(get_current_user)):
    """Update profile picture (base64 encoded)"""
    body = await request.json()
    picture = body.get("profile_picture", "")
    
    if not picture:
        raise HTTPException(status_code=400, detail="Profile picture is required")
    
    # Limit size (roughly 5MB base64)
    if len(picture) > 7_000_000:
        raise HTTPException(status_code=400, detail="Image too large. Max 5MB")
    
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": {"profile_picture": picture}}
    )
    
    return {"message": "Profile picture updated successfully"}

@api_router.put("/profile/favorites")
async def update_favorites(data: FavoritesUpdate, user: User = Depends(get_current_user)):
    """Update user's favorite albums (max 5)"""
    if len(data.favorites) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 favorite albums allowed")
    
    # Validate each album exists in user's ratings
    user_ratings = await db.ratings.find(
        {"user_id": user.user_id},
        {"album_id": 1, "_id": 0}
    ).to_list(1000)
    rated_album_ids = {r["album_id"] for r in user_ratings}
    
    for fav in data.favorites:
        if fav.album_id not in rated_album_ids:
            raise HTTPException(status_code=400, detail=f"You haven't rated album: {fav.album_name}")
    
    favorites_data = [f.model_dump() for f in data.favorites]
    
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": {"favorites": favorites_data}}
    )
    
    return {"favorites": favorites_data, "message": "Favorites updated successfully"}

@api_router.get("/profile/{user_id}")
async def get_user_profile(user_id: str):
    """Get a user's public profile"""
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get counts
    followers_count = await db.friends.count_documents({"following_id": user_id})
    following_count = await db.friends.count_documents({"follower_id": user_id})
    ratings_count = await db.ratings.count_documents({"user_id": user_id})
    
    return {
        "user_id": user_doc.get("user_id"),
        "name": user_doc.get("name"),
        "user_tag": user_doc.get("user_tag"),
        "profile_picture": user_doc.get("profile_picture"),
        "picture": user_doc.get("picture"),
        "favorites": user_doc.get("favorites", []),
        "followers_count": followers_count,
        "following_count": following_count,
        "ratings_count": ratings_count,
        "created_at": user_doc.get("created_at"),
    }

# ======================= Social / Friends Endpoints =======================
@api_router.get("/users/search")
async def search_users(q: str, user: User = Depends(get_current_user)):
    """Search users by tag"""
    if not q or len(q) < 2:
        return {"users": []}
    
    query = q.strip().lower()
    
    users = await db.users.find(
        {
            "user_tag": {"$regex": query, "$options": "i"},
            "user_id": {"$ne": user.user_id}  # Exclude self
        },
        {"_id": 0, "user_id": 1, "name": 1, "user_tag": 1, "profile_picture": 1, "picture": 1}
    ).limit(20).to_list(20)
    
    # For each user, check if the current user is following them
    for u in users:
        is_following = await db.friends.find_one({
            "follower_id": user.user_id,
            "following_id": u["user_id"]
        })
        u["is_following"] = is_following is not None
    
    return {"users": users}

@api_router.post("/friends/follow/{target_user_id}")
async def follow_user(target_user_id: str, user: User = Depends(get_current_user)):
    """Follow a user (instant, one-way)"""
    if target_user_id == user.user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    # Check target exists
    target = await db.users.find_one({"user_id": target_user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already following
    existing = await db.friends.find_one({
        "follower_id": user.user_id,
        "following_id": target_user_id
    })
    
    if existing:
        return {"message": "Already following this user"}
    
    await db.friends.insert_one({
        "follower_id": user.user_id,
        "following_id": target_user_id,
        "created_at": datetime.now(timezone.utc)
    })
    
    return {"message": "Followed successfully"}

@api_router.delete("/friends/unfollow/{target_user_id}")
async def unfollow_user(target_user_id: str, user: User = Depends(get_current_user)):
    """Unfollow a user"""
    result = await db.friends.delete_one({
        "follower_id": user.user_id,
        "following_id": target_user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not following this user")
    
    return {"message": "Unfollowed successfully"}

@api_router.get("/friends")
async def get_my_friends(user: User = Depends(get_current_user)):
    """Get list of users the current user is following"""
    friends = await db.friends.find(
        {"follower_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    
    # Get user details for each friend
    friend_details = []
    for f in friends:
        friend_user = await db.users.find_one(
            {"user_id": f["following_id"]},
            {"_id": 0, "user_id": 1, "name": 1, "user_tag": 1, "profile_picture": 1, "picture": 1}
        )
        if friend_user:
            friend_user["followed_at"] = f["created_at"]
            friend_details.append(friend_user)
    
    return {"friends": friend_details, "count": len(friend_details)}

@api_router.get("/friends/check/{target_user_id}")
async def check_following(target_user_id: str, user: User = Depends(get_current_user)):
    """Check if current user follows target user"""
    existing = await db.friends.find_one({
        "follower_id": user.user_id,
        "following_id": target_user_id
    })
    return {"is_following": existing is not None}

# ======================= User Ratings Endpoints (Public) =======================
@api_router.get("/ratings/user/{user_id}/latest")
async def get_user_latest_ratings(user_id: str):
    """Get another user's latest 5 ratings"""
    ratings = await db.ratings.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    return {"ratings": ratings}

@api_router.get("/ratings/user/{user_id}/all")
async def get_user_all_ratings(user_id: str, limit: int = 100, skip: int = 0):
    """Get all of another user's ratings"""
    ratings = await db.ratings.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.ratings.count_documents({"user_id": user_id})
    return {"ratings": ratings, "total": total}

@api_router.get("/ratings/user/{user_id}/distribution")
async def get_user_score_distribution(user_id: str):
    """Get score distribution for a user"""
    pipeline = [
        {"$match": {"user_id": user_id}},
        {
            "$group": {
                "_id": "$score",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    
    results = await db.ratings.aggregate(pipeline).to_list(100)
    
    # Build complete distribution with all score values
    score_values = [s["value"] for s in SCORE_OPTIONS]
    distribution = {}
    for sv in score_values:
        distribution[str(sv)] = 0
    
    for r in results:
        distribution[str(r["_id"])] = r["count"]
    
    return {"distribution": distribution, "total": sum(r["count"] for r in results)}

# ======================= Community Feed & Likes Endpoints =======================
@api_router.get("/feed")
async def get_community_feed(limit: int = 30, skip: int = 0, user: User = Depends(get_current_user)):
    """Get community feed: ratings from followed users + self, ordered by most recent"""
    # Get list of users we follow
    friends = await db.friends.find(
        {"follower_id": user.user_id},
        {"following_id": 1, "_id": 0}
    ).to_list(500)
    
    following_ids = [f["following_id"] for f in friends]
    # Include self
    feed_user_ids = following_ids + [user.user_id]
    
    # Fetch ratings from those users
    ratings = await db.ratings.find(
        {"user_id": {"$in": feed_user_ids}},
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.ratings.count_documents({"user_id": {"$in": feed_user_ids}})
    
    # Enrich each rating with user info and like status
    enriched = []
    for r in ratings:
        # Get user info
        rating_user = await db.users.find_one(
            {"user_id": r["user_id"]},
            {"_id": 0, "user_id": 1, "name": 1, "user_tag": 1, "profile_picture": 1, "picture": 1}
        )
        
        # Get like count
        like_count = await db.likes.count_documents({"rating_id": r["rating_id"]})
        
        # Check if current user liked it
        user_liked = await db.likes.find_one({
            "user_id": user.user_id,
            "rating_id": r["rating_id"]
        })
        
        enriched.append({
            **r,
            "user_info": rating_user,
            "like_count": like_count,
            "user_liked": user_liked is not None,
            "is_own": r["user_id"] == user.user_id,
        })
    
    return {"ratings": enriched, "total": total}

@api_router.post("/ratings/{rating_id}/like")
async def like_rating(rating_id: str, user: User = Depends(get_current_user)):
    """Like a rating"""
    # Check rating exists
    rating = await db.ratings.find_one({"rating_id": rating_id}, {"_id": 0})
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")
    
    # Cannot like own rating
    if rating["user_id"] == user.user_id:
        raise HTTPException(status_code=400, detail="Cannot like your own rating")
    
    # Check if already liked
    existing = await db.likes.find_one({
        "user_id": user.user_id,
        "rating_id": rating_id
    })
    if existing:
        return {"message": "Already liked", "like_count": await db.likes.count_documents({"rating_id": rating_id})}
    
    await db.likes.insert_one({
        "user_id": user.user_id,
        "rating_id": rating_id,
        "created_at": datetime.now(timezone.utc)
    })
    
    like_count = await db.likes.count_documents({"rating_id": rating_id})
    return {"message": "Liked", "like_count": like_count}

@api_router.delete("/ratings/{rating_id}/unlike")
async def unlike_rating(rating_id: str, user: User = Depends(get_current_user)):
    """Unlike a rating"""
    result = await db.likes.delete_one({
        "user_id": user.user_id,
        "rating_id": rating_id
    })
    
    like_count = await db.likes.count_documents({"rating_id": rating_id})
    
    if result.deleted_count == 0:
        return {"message": "Was not liked", "like_count": like_count}
    
    return {"message": "Unliked", "like_count": like_count}

# ======================= Spotify Endpoints =======================
@api_router.get("/spotify/search")
async def search_albums(q: str, limit: int = 10):
    """Search for albums on Spotify"""
    logger.info(f"Search called with USE_MOCK_DATA={USE_MOCK_DATA}")
    # Try real Spotify API first
    if not USE_MOCK_DATA:
        try:
            spotify = get_spotify_client()
            logger.info("Calling Spotify search API...")
            # Cap limit at 10 to avoid API issues
            safe_limit = min(limit, 10)
            results = spotify.search(q=q, type='album', limit=safe_limit)
            logger.info(f"Spotify returned {len(results['albums']['items'])} albums")
            albums = []
            
            for item in results['albums']['items']:
                albums.append({
                    "id": item['id'],
                    "name": item['name'],
                    "artist": item['artists'][0]['name'] if item['artists'] else "Unknown",
                    "artwork": item['images'][0]['url'] if item['images'] else None,
                    "release_date": item.get('release_date', ''),
                    "total_tracks": item.get('total_tracks', 0)
                })
            
            return {"albums": albums}
        except Exception as e:
            logger.error(f"Spotify search error: {e}")
            # Fall through to mock data
    
    # Use mock data
    logger.info("Using mock data")
    query_lower = q.lower()
    filtered = [
        album for album in MOCK_ALBUMS
        if query_lower in album['name'].lower() or query_lower in album['artist'].lower()
    ]
    # If no matches, return all mock albums
    if not filtered:
        filtered = MOCK_ALBUMS[:limit]
    return {"albums": filtered[:limit]}

@api_router.get("/spotify/album/{album_id}")
async def get_album(album_id: str):
    """Get album details including tracks"""
    # Check mock data first
    if album_id in MOCK_ALBUM_DETAILS:
        return MOCK_ALBUM_DETAILS[album_id]
    
    # For any mock album, generate basic details
    mock_album = next((a for a in MOCK_ALBUMS if a['id'] == album_id), None)
    if mock_album:
        return {
            "id": mock_album['id'],
            "name": mock_album['name'],
            "artist": mock_album['artist'],
            "artists": [mock_album['artist']],
            "artwork": mock_album['artwork'],
            "release_date": mock_album['release_date'],
            "release_year": mock_album['release_date'][:4],
            "total_tracks": mock_album['total_tracks'],
            "tracks": [
                {"id": f"t{i}", "name": f"Track {i}", "track_number": i, "duration": "3:30", "artists": [mock_album['artist']]}
                for i in range(1, mock_album['total_tracks'] + 1)
            ],
            "genres": [],
            "label": "Mock Records",
            "popularity": 75
        }
    
    # Try real Spotify API
    if not USE_MOCK_DATA:
        try:
            spotify = get_spotify_client()
            album = spotify.album(album_id)
            
            tracks = []
            for track in album['tracks']['items']:
                duration_ms = track.get('duration_ms', 0)
                minutes = duration_ms // 60000
                seconds = (duration_ms % 60000) // 1000
                
                tracks.append({
                    "id": track['id'],
                    "name": track['name'],
                    "track_number": track['track_number'],
                    "duration": f"{minutes}:{seconds:02d}",
                    "artists": [artist['name'] for artist in track['artists']]
                })
            
            return {
                "id": album['id'],
                "name": album['name'],
                "artist": album['artists'][0]['name'] if album['artists'] else "Unknown",
                "artists": [artist['name'] for artist in album['artists']],
                "artwork": album['images'][0]['url'] if album['images'] else None,
                "release_date": album.get('release_date', ''),
                "release_year": album.get('release_date', '')[:4] if album.get('release_date') else '',
                "total_tracks": album.get('total_tracks', 0),
                "tracks": tracks,
                "genres": album.get('genres', []),
                "label": album.get('label', ''),
                "popularity": album.get('popularity', 0)
            }
        except Exception as e:
            logger.error(f"Spotify album error: {e}")
    
    raise HTTPException(status_code=404, detail="Album not found")

@api_router.get("/spotify/new-releases")
async def get_new_releases(limit: int = 10):
    """Get new album releases"""
    # Use mock data
    if USE_MOCK_DATA:
        return {"albums": MOCK_ALBUMS[:limit]}
    
    try:
        spotify = get_spotify_client()
        # Calculate date range for last 2 months
        from datetime import date
        today = date.today()
        year = today.year
        
        # Cap limit at 10 to avoid API issues
        safe_limit = min(limit, 10)
        
        # Search for popular new albums using year filter
        results = spotify.search(
            q=f"year:{year} tag:new",
            type='album',
            limit=safe_limit
        )
        
        albums = []
        for item in results['albums']['items']:
            albums.append({
                "id": item['id'],
                "name": item['name'],
                "artist": item['artists'][0]['name'] if item['artists'] else "Unknown",
                "artwork": item['images'][0]['url'] if item['images'] else None,
                "release_date": item.get('release_date', ''),
                "total_tracks": item.get('total_tracks', 0)
            })
        
        return {"albums": albums}
    except Exception as e:
        logger.error(f"Spotify new releases error: {e}")
        # Return mock data as fallback
        return {"albums": MOCK_ALBUMS[:limit]}

@api_router.get("/spotify/popular")
async def get_popular_albums(limit: int = 10):
    """Get popular/trending albums from Spotify"""
    # Use mock data
    if USE_MOCK_DATA:
        return {"albums": MOCK_ALBUMS[:limit]}
    
    try:
        spotify = get_spotify_client()
        
        # Search for albums from popular artists to ensure we get good results
        popular_queries = [
            "Taylor Swift", "Drake", "The Weeknd", "Beyonce", "Ed Sheeran", 
            "Billie Eilish", "Kendrick Lamar", "Dua Lipa", "Bad Bunny", "Ariana Grande",
            "Post Malone", "Harry Styles", "Rihanna", "Bruno Mars", "SZA",
            "Travis Scott", "Olivia Rodrigo", "Justin Bieber", "Doja Cat", "Adele",
            "Kanye West", "Lady Gaga", "Miley Cyrus", "Coldplay", "Imagine Dragons"
        ]
        
        all_albums = []
        for artist_query in popular_queries[:limit]:
            try:
                results = spotify.search(
                    q=artist_query,
                    type='album',
                    limit=1
                )
                if results['albums']['items']:
                    item = results['albums']['items'][0]
                    all_albums.append({
                        "id": item['id'],
                        "name": item['name'],
                        "artist": item['artists'][0]['name'] if item['artists'] else "Unknown",
                        "artwork": item['images'][0]['url'] if item['images'] else None,
                        "release_date": item.get('release_date', ''),
                        "total_tracks": item.get('total_tracks', 0)
                    })
            except Exception as e:
                logger.error(f"Error fetching album for {artist_query}: {e}")
                continue
        
        return {"albums": all_albums[:limit]}
    except Exception as e:
        logger.error(f"Spotify popular albums error: {e}")
        # Return mock data as fallback
        return {"albums": MOCK_ALBUMS[:limit]}

# ======================= Rating Endpoints =======================
@api_router.post("/ratings", response_model=dict)
async def create_rating(rating_data: RatingCreate, user: User = Depends(get_current_user)):
    """Create a new album rating"""
    # Validate score
    valid_scores = [s["value"] for s in SCORE_OPTIONS]
    if rating_data.score not in valid_scores:
        raise HTTPException(status_code=400, detail="Invalid score value")
    
    # Validate tags
    if len(rating_data.tags) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 tags allowed")
    for tag in rating_data.tags:
        if tag not in TAG_OPTIONS:
            raise HTTPException(status_code=400, detail=f"Invalid tag: {tag}")
    
    # Validate headline length
    if len(rating_data.headline) > 300:
        raise HTTPException(status_code=400, detail="Headline must be 300 characters or less")
    
    # Validate favorite tracks (max 3)
    if len(rating_data.favorite_tracks) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 favorite tracks allowed")
    
    # Validate least favorite tracks (max 2)
    if len(rating_data.least_favorite_tracks) > 2:
        raise HTTPException(status_code=400, detail="Maximum 2 least favorite tracks allowed")
    
    # Check for overlap between favorite and least favorite
    fav_ids = {t.get('id') for t in rating_data.favorite_tracks if t.get('id')}
    least_ids = {t.get('id') for t in rating_data.least_favorite_tracks if t.get('id')}
    if fav_ids & least_ids:
        raise HTTPException(status_code=400, detail="A track cannot be both favorite and least favorite")
    
    # Check if user already rated this album
    existing = await db.ratings.find_one(
        {"user_id": user.user_id, "album_id": rating_data.album_id},
        {"_id": 0}
    )
    
    if existing:
        raise HTTPException(status_code=400, detail="You have already rated this album")
    
    # Create rating
    rating = Rating(
        user_id=user.user_id,
        **rating_data.model_dump()
    )
    
    await db.ratings.insert_one(rating.model_dump())
    
    return rating.model_dump()

@api_router.get("/ratings/my")
async def get_my_ratings(
    limit: int = 100,
    skip: int = 0,
    user: User = Depends(get_current_user)
):
    """Get current user's ratings"""
    ratings = await db.ratings.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.ratings.count_documents({"user_id": user.user_id})
    
    return {"ratings": ratings, "total": total}

@api_router.get("/ratings/my/latest")
async def get_my_latest_ratings(user: User = Depends(get_current_user)):
    """Get current user's latest 5 ratings"""
    ratings = await db.ratings.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    return {"ratings": ratings}

@api_router.get("/ratings/community/top")
async def get_community_top_albums(limit: int = 10):
    """Get top albums with most ratings and their average scores"""
    pipeline = [
        {
            "$group": {
                "_id": "$album_id",
                "album_name": {"$first": "$album_name"},
                "artist_name": {"$first": "$artist_name"},
                "album_artwork": {"$first": "$album_artwork"},
                "release_year": {"$first": "$release_year"},
                "rating_count": {"$sum": 1},
                "average_score": {"$avg": "$score"},
                "latest_rating": {"$max": "$created_at"}
            }
        },
        {
            "$sort": {"rating_count": -1, "latest_rating": -1}
        },
        {
            "$limit": limit
        },
        {
            "$project": {
                "_id": 0,
                "album_id": "$_id",
                "album_name": 1,
                "artist_name": 1,
                "album_artwork": 1,
                "release_year": 1,
                "rating_count": 1,
                "average_score": {"$round": ["$average_score", 1]}
            }
        }
    ]
    
    results = await db.ratings.aggregate(pipeline).to_list(limit)
    return {"albums": results}

@api_router.get("/ratings/album/{album_id}")
async def get_album_rating(album_id: str, user: User = Depends(get_current_user)):
    """Get user's rating for a specific album"""
    rating = await db.ratings.find_one(
        {"user_id": user.user_id, "album_id": album_id},
        {"_id": 0}
    )
    
    if not rating:
        return {"rating": None}
    
    return {"rating": rating}

@api_router.put("/ratings/{rating_id}")
async def update_rating(
    rating_id: str,
    rating_data: RatingUpdate,
    user: User = Depends(get_current_user)
):
    """Update a rating"""
    # Find existing rating
    existing = await db.ratings.find_one(
        {"rating_id": rating_id, "user_id": user.user_id},
        {"_id": 0}
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail="Rating not found")
    
    update_data = {}
    
    if rating_data.score is not None:
        valid_scores = [s["value"] for s in SCORE_OPTIONS]
        if rating_data.score not in valid_scores:
            raise HTTPException(status_code=400, detail="Invalid score value")
        update_data["score"] = rating_data.score
    
    if rating_data.tags is not None:
        if len(rating_data.tags) > 3:
            raise HTTPException(status_code=400, detail="Maximum 3 tags allowed")
        for tag in rating_data.tags:
            if tag not in TAG_OPTIONS:
                raise HTTPException(status_code=400, detail=f"Invalid tag: {tag}")
        update_data["tags"] = rating_data.tags
    
    if rating_data.headline is not None:
        if len(rating_data.headline) > 300:
            raise HTTPException(status_code=400, detail="Headline must be 300 characters or less")
        update_data["headline"] = rating_data.headline
    
    if rating_data.favorite_tracks is not None:
        if len(rating_data.favorite_tracks) > 3:
            raise HTTPException(status_code=400, detail="Maximum 3 favorite tracks allowed")
        update_data["favorite_tracks"] = rating_data.favorite_tracks
    
    if rating_data.least_favorite_tracks is not None:
        if len(rating_data.least_favorite_tracks) > 2:
            raise HTTPException(status_code=400, detail="Maximum 2 least favorite tracks allowed")
        update_data["least_favorite_tracks"] = rating_data.least_favorite_tracks
    
    # Check for overlap between favorite and least favorite
    fav_tracks = rating_data.favorite_tracks if rating_data.favorite_tracks is not None else existing.get('favorite_tracks', [])
    least_tracks = rating_data.least_favorite_tracks if rating_data.least_favorite_tracks is not None else existing.get('least_favorite_tracks', [])
    fav_ids = {t.get('id') for t in fav_tracks if t.get('id')}
    least_ids = {t.get('id') for t in least_tracks if t.get('id')}
    if fav_ids & least_ids:
        raise HTTPException(status_code=400, detail="A track cannot be both favorite and least favorite")
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)
        await db.ratings.update_one(
            {"rating_id": rating_id},
            {"$set": update_data}
        )
    
    updated = await db.ratings.find_one({"rating_id": rating_id}, {"_id": 0})
    return updated

@api_router.delete("/ratings/{rating_id}")
async def delete_rating(rating_id: str, user: User = Depends(get_current_user)):
    """Delete a rating"""
    result = await db.ratings.delete_one(
        {"rating_id": rating_id, "user_id": user.user_id}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rating not found")
    
    return {"message": "Rating deleted successfully"}

# ======================= Constants Endpoints =======================
@api_router.get("/constants/scores")
async def get_scores():
    """Get all score options"""
    return {"scores": SCORE_OPTIONS}

@api_router.get("/constants/tags")
async def get_tags():
    """Get all tag options"""
    return {"tags": TAG_OPTIONS}

# ======================= Health Check =======================
@api_router.get("/")
async def root():
    return {"message": "Unison Music Ratings API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_db_indexes():
    """Create MongoDB indexes for performance"""
    try:
        # Use partial index for user_tag to allow multiple null values
        await db.users.create_index(
            "user_tag", 
            unique=True, 
            partialFilterExpression={"user_tag": {"$exists": True, "$type": "string"}}
        )
        await db.friends.create_index([("follower_id", 1), ("following_id", 1)], unique=True)
        await db.friends.create_index("follower_id")
        await db.friends.create_index("following_id")
        await db.likes.create_index([("user_id", 1), ("rating_id", 1)], unique=True)
        await db.likes.create_index("rating_id")
        logger.info("MongoDB indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
