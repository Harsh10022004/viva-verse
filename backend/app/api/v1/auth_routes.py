from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.database_models import User
from app.utils.auth import verify_password, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from pydantic import BaseModel

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class LoginRequest(BaseModel):
    username: str
    password: str

class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

@router.post("/signup")
async def signup(req: SignupRequest, db: Session = Depends(get_db)):
    from app.utils.auth import get_password_hash
    # Check if user exists
    existing = db.query(User).filter((User.username == req.username) | (User.email == req.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")
        
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=get_password_hash(req.password),
        role="student"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"message": "User created successfully", "user_id": user.id}

@router.post("/login", response_model=Token)
async def login_for_access_token(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role
        }
    }

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role
    }
