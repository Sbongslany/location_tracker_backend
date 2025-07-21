from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from app.models.user import UserCreate, UserLogin, UserResponse, Token
from app.database.db import get_db
from app.utils.auth import hash_password, verify_password, create_access_token
from datetime import timedelta

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={401: {"description": "Unauthorized"}}
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user: UserCreate):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            hashed_password = hash_password(user.password)
            try:
                cursor.execute(
                    "INSERT INTO users (email, hashed_password) VALUES (?, ?)",
                    (user.email, hashed_password)
                )
                conn.commit()
                cursor.execute("SELECT id, email FROM users WHERE email = ?", (user.email,))
                user_data = cursor.fetchone()
                return UserResponse(**dict(user_data))
            except sqlite3.IntegrityError:
                raise HTTPException(status_code=400, detail="Email already registered")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register user: {str(e)}")

@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, hashed_password FROM users WHERE email = ?", (user.email,))
            user_data = cursor.fetchone()
            if not user_data or not verify_password(user.password, user_data["hashed_password"]):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            access_token = create_access_token(
                data={"sub": user_data["email"], "user_id": user_data["id"]},
                expires_delta=timedelta(minutes=700)
            )
            return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to login: {str(e)}")