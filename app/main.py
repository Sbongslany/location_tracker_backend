from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import location, auth
from app.database.db import init_db

app = FastAPI(
    title="Live Location Tracker API",
    description="API for receiving and storing device location data with JWT authentication and WebSocket",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(location.router)
app.include_router(auth.router)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)