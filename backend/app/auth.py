"""
Authentication and Authorization Module
JWT-based authentication with role-based access control
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Request, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import uuid
import secrets
import os

from app.database import get_db, User

# Supabase Auth Integration
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    Client = None

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()

supabase_auth: Optional[Client] = None
if HAS_SUPABASE and SUPABASE_URL and SUPABASE_KEY:
    try:
        # Validate URL format
        if not SUPABASE_URL.startswith("https://"):
            print(f"[AUTH WARNING] Invalid SUPABASE_URL format. Must start with https://")
        else:
            supabase_auth = create_client(SUPABASE_URL, SUPABASE_KEY)
            print(f"[AUTH] Supabase Authentication Engine Initialized: {SUPABASE_URL[:30]}...")
    except Exception as e:
        print(f"[AUTH WARNING] Supabase connection failed: {e}")
else:
    if not HAS_SUPABASE:
        print("[AUTH] Supabase package not installed. Using local authentication only.")
    elif not SUPABASE_URL or not SUPABASE_KEY:
        print("[AUTH] Supabase credentials not configured. Using local authentication only.")

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
API_KEY_EXPIRE_DAYS = 365

# Password hashing using bcrypt directly
security = HTTPBearer(auto_error=False)

# Pydantic Models
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None
    scopes: list = []

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

# Password Utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using bcrypt directly"""
    try:
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Generate password hash using bcrypt directly"""
    # bcrypt has 72 byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12))
    return hashed.decode('utf-8')

def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"sa_{secrets.token_urlsafe(32)}"

# JWT Token Utilities
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None

# User CRUD Operations
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_api_key(db: Session, api_key: str) -> Optional[User]:
    """Get user by API key"""
    user = db.query(User).filter(User.api_key == api_key).first()
    if user and user.api_key_expires and user.api_key_expires > datetime.utcnow():
        return user
    return None

def create_user(db: Session, user_data: UserCreate) -> User:
    """Create a new user using Supabase Auth and local mirror (STRICT MODE)"""
    # Check if email or username already exists locally
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # STRICT MODE: Supabase is REQUIRED for registration
    if not supabase_auth:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable. Please try again later."
        )

    # 1. Create user in Supabase Auth (REQUIRED - no fallback)
    try:
        res = supabase_auth.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "full_name": user_data.full_name or "",
                    "username": user_data.username
                }
            }
        })
        if not res.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supabase Auth rejected signup"
            )
        print(f"[AUTH] Supabase user created: {res.user.id}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH ERROR] Supabase signup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )

    # 2. Create local mirror ONLY after Supabase succeeds
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_verified=True  # Mark as verified since Supabase accepted
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate user prioritizing Supabase Auth, falling back to local credentials"""

    is_email = '@' in username

    # Try Supabase Auth First (if email-based login)
    if supabase_auth and is_email:
        try:
            res = supabase_auth.auth.sign_in_with_password({
                "email": username,
                "password": password
            })
            if res.user:
                # Successfully authenticated with Supabase. Ensure local mirror exists.
                user = get_user_by_email(db, username)
                if not user:
                    user_name_derived = username.split('@')[0]
                    # Create mirror dynamically
                    user = User(
                        email=username,
                        username=user_name_derived,
                        hashed_password=get_password_hash(password),
                        full_name=user_name_derived,
                        is_verified=True
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                else:
                    # Update last login
                    user.last_login = datetime.utcnow()
                    db.commit()
                return user
        except Exception as e:
            error_msg = str(e)
            # Check if this is an email confirmation error
            if "Email not confirmed" in error_msg or "email_not_confirmed" in error_msg:
                print(f"[AUTH] Supabase: Email not confirmed for {username}, falling back to local auth")
                # Fall through to local auth
            elif "Invalid login credentials" in error_msg or "invalid_credentials" in error_msg:
                print(f"[AUTH] Supabase: Invalid credentials for {username}")
                # Fall through to local auth to check local credentials
            else:
                print(f"[AUTH WARNING] Supabase auth error: {e}, falling back to local auth")
                # Fall through to local auth

    # Try local authentication (username or email)
    user = get_user_by_username(db, username)
    if not user:
        user = get_user_by_email(db, username)

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    # Update last login on successful local auth
    user.last_login = datetime.utcnow()
    db.commit()

    return user

def generate_user_api_key(db: Session, user_id: int) -> str:
    """Generate new API key for user"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    api_key = generate_api_key()
    user.api_key = api_key
    user.api_key_expires = datetime.utcnow() + timedelta(days=API_KEY_EXPIRE_DAYS)
    
    db.commit()
    db.refresh(user)
    
    return api_key

def revoke_api_key(db: Session, user_id: int) -> bool:
    """Revoke user's API key"""
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    
    user.api_key = None
    user.api_key_expires = None
    db.commit()
    
    return True

# Authentication Dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    payload = decode_token(credentials.credentials, "access")
    if payload is None:
        raise credentials_exception
    
    email: str = payload.get("sub")
    user_id: int = payload.get("user_id")
    
    if email is None or user_id is None:
        raise credentials_exception
    
    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user

async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None"""
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure user is active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure user is admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_user_from_api_key(
    api_key: str,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get user from API key"""
    if not api_key:
        return None
    return get_user_by_api_key(db, api_key)

async def get_current_user_ws(
    websocket: WebSocket,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user from WebSocket connection"""
    # Try to get token from query params or headers
    token = websocket.query_params.get("token")
    if not token:
        return None
    
    payload = decode_token(token, "access")
    if payload is None:
        return None
    
    user_id: int = payload.get("user_id")
    if not user_id:
        return None
    
    return get_user_by_id(db, user_id)

# Audit Logging
def log_audit_event(
    db: Session,
    action: str,
    resource_type: str,
    user_id: Optional[int] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict] = None,
    request: Optional[Request] = None,
    success: bool = True,
    error_message: Optional[str] = None
):
    """Log an audit event"""
    from app.database import AuditLog
    
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
        success=success,
        error_message=error_message
    )
    
    db.add(audit_log)
    db.commit()

# Login/Token Functions
def login_user(db: Session, username: str, password: str, request: Optional[Request] = None) -> Token:
    """Authenticate user and generate tokens"""
    user = authenticate_user(db, username, password)

    if not user:
        # Log failed login attempt
        log_audit_event(
            db=db,
            action="LOGIN_FAILED",
            resource_type="user",
            details={"username": username},
            request=request,
            success=False,
            error_message="Invalid credentials"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Note: last_login is already updated in authenticate_user for local auth
    # For Supabase auth, we update it there too. But ensure it's set here as well for safety.
    if not user.last_login:
        user.last_login = datetime.utcnow()
        db.commit()

    # Generate tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "username": user.username},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.email, "user_id": user.id}
    )

    # Log successful login
    log_audit_event(
        db=db,
        action="LOGIN_SUCCESS",
        resource_type="user",
        user_id=user.id,
        resource_id=str(user.id),
        request=request,
        success=True
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_admin": user.is_admin
        }
    )

def refresh_access_token(db: Session, refresh_token: str) -> Dict[str, str]:
    """Generate new access token from refresh token"""
    payload = decode_token(refresh_token, "refresh")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: int = payload.get("user_id")
    user = get_user_by_id(db, user_id)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate new access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "username": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

def logout_user(db: Session, user_id: int, request: Optional[Request] = None):
    """Log user logout (mainly for audit purposes)"""
    log_audit_event(
        db=db,
        action="LOGOUT",
        resource_type="user",
        user_id=user_id,
        resource_id=str(user_id),
        request=request,
        success=True
    )
