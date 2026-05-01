# Unison Backend - FastAPI

Backend API for Unison Music Ratings app.

## Features
- 🔐 Authentication (Google OAuth, Apple Sign In, Email/Password)
- 🎵 Spotify API integration (search, albums, tracks)
- ⭐ Album ratings with scores, tags, and reviews
- 👥 Social features (follow users, community feed, likes)
- 📊 User profiles and statistics

## Production Deployment

**Your app is currently running on Emergent's preview environment.**

To deploy to production and run 24/7:
1. **Set up MongoDB Atlas** (cloud database)
2. **Deploy to Railway** (backend hosting)
3. **Update Netlify** (point frontend to new backend)

**📖 See:** `/app/PRODUCTION_DEPLOYMENT.md` for step-by-step guide

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- MongoDB running locally
- Spotify API credentials

### Install Dependencies
```bash
cd /app/backend
pip install -r requirements.txt
```

### Environment Variables
Create `.env` file:
```bash
MONGO_URL=mongodb://localhost:27017
DB_NAME=unison_development
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```

### Run
```bash
uvicorn server:app --reload --port 8001
```

API will be available at http://localhost:8001

---

## Files Created for Production

- ✅ `Procfile` - Railway start command
- ✅ `railway.json` - Railway configuration
- ✅ `.env.production` - Example production env vars
- ✅ `requirements.txt` - Python dependencies

---

## API Documentation

Once running, visit:
- **Swagger UI:** http://localhost:8001/docs
- **ReDoc:** http://localhost:8001/redoc

---

## Deployment Guides

- **Quick Reference:** `/app/PRODUCTION_DEPLOYMENT.md`
- **MongoDB Atlas:** `/app/MONGODB_ATLAS_GUIDE.md`
- **Railway Setup:** `/app/RAILWAY_DEPLOYMENT_GUIDE.md`

---

## Tech Stack

- **Framework:** FastAPI
- **Database:** MongoDB (Motor async driver)
- **Auth:** Emergent OAuth, Apple Sign In, bcrypt
- **External APIs:** Spotify Web API
- **Server:** Uvicorn (ASGI)

---

## Environment Variables

### Required
- `MONGO_URL` - MongoDB connection string
- `DB_NAME` - Database name
- `SPOTIFY_CLIENT_ID` - Spotify API client ID
- `SPOTIFY_CLIENT_SECRET` - Spotify API client secret

### Optional
- `PORT` - Server port (default: 8001, Railway sets automatically)
- `PYTHON_VERSION` - Python version (3.11)

---

## Need Help?

See comprehensive guides in `/app/` directory or check Railway/MongoDB Atlas documentation.
