"""
Pure Supabase Authentication Module
Replaces SQLite-based auth with Supabase Auth exclusively
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from fastapi import Depends, HTTPException, status, Request, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import os
import uuid
import secrets

from supabase import create_client, Client

# Load Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

# Initialize Supabase clients
supabase_client: Optional[Client] = None
supabase_admin: Optional[Client] = None

if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        # Regular client for user operations
        supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print(f"[SUPABASE AUTH] Client initialized: {SUPABASE_URL[:30]}...")
        
        # Admin client for privileged operations (if service role key available)
        if SUPABASE_SERVICE_ROLE_KEY:
            supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            print("[SUPABASE AUTH] Admin client initialized")
    except Exception as e:
        print(f"[SUPABASE AUTH ERROR] Failed to initialize: {e}")
        raise RuntimeError(f"Supabase authentication required but failed to initialize: {e}")
else:
    raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be configured in environment")

# Security
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
    user_id: Optional[str] = None
    scopes: list = []

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class SupabaseUser:
    """Wrapper for Supabase user data"""
    def __init__(self, user_data: Dict[str, Any]):
        self.id = user_data.get("id")
        self.email = user_data.get("email")
        self.user_metadata = user_data.get("user_metadata", {})
        self.full_name = self.user_metadata.get("full_name", "")
        self.is_verified = user_data.get("email_confirmed_at") is not None
        self.is_active = not user_data.get("banned", False)
        self.created_at = user_data.get("created_at")
        self.last_login = user_data.get("last_sign_in_at")
        self.raw_data = user_data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "metadata": self.user_metadata
        }

# User Management Functions
def create_supabase_user(user_data: UserCreate) -> tuple[SupabaseUser, str]:
    """Create a new user in Supabase Auth using Admin API (bypasses rate limits)
    
    Returns:
        tuple: (SupabaseUser, None) - Admin API doesn't return session
    """
    try:
        # Use Admin API to create user directly (bypasses rate limits)
        if not supabase_admin:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Admin client not available for user creation"
            )
        
        # Create user via admin API - this bypasses rate limits
        admin_response = supabase_admin.auth.admin.create_user({
            "email": user_data.email,
            "password": user_data.password,
            "user_metadata": {
                "full_name": user_data.full_name or user_data.email.split("@")[0],
            },
            "email_confirm": True  # Auto-confirm email for simplicity
        })
        
        if not admin_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )
        
        user = SupabaseUser(admin_response.user.model_dump())
        print(f"[SUPABASE AUTH] User created via admin API: {user.email}")
        
        # Create profile in Supabase database
        try:
            profile_data = {
                "id": user.id,
                "email": user.email,
                "risk_tolerance": "medium",
                "capital": 100000,
                "preferred_strategy": "swing",
                "full_name": user.full_name
            }
            supabase_admin.table("profiles").insert(profile_data).execute()
            print(f"[SUPABASE AUTH] Profile created for: {user.email}")
        except Exception as e:
            print(f"[SUPABASE AUTH WARNING] Could not create profile: {e}")
            # Don't fail if profile creation fails - auth succeeded
        
        # Admin API doesn't return a session, so we return None for token
        # User will need to login separately to get tokens
        return user, None
        
    except Exception as e:
        error_msg = str(e)
        if "User already registered" in error_msg or "already exists" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {error_msg}"
        )

def authenticate_supabase_user(email: str, password: str) -> tuple[SupabaseUser, str, str]:
    """Authenticate user with Supabase Auth
    
    Returns:
        tuple: (SupabaseUser, access_token, refresh_token)
    """
    try:
        auth_response = supabase_client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        user = SupabaseUser(auth_response.user.model_dump())
        
        # Update profile last login if possible
        try:
            if supabase_admin:
                supabase_admin.table("profiles").update({
                    "last_login": datetime.utcnow().isoformat()
                }).eq("id", user.id).execute()
        except:
            pass
        
        return (
            user, 
            auth_response.session.access_token,
            auth_response.session.refresh_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Invalid login credentials" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {error_msg}"
        )

def refresh_supabase_token(refresh_token: str) -> Dict[str, str]:
    """Refresh access token using refresh token"""
    try:
        auth_response = supabase_client.auth.refresh_session(refresh_token)
        
        if not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return {
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token,
            "token_type": "bearer",
            "expires_in": 3600  # Supabase tokens typically expire in 1 hour
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {str(e)}"
        )

def logout_supabase_user(access_token: str) -> bool:
    """Logout user from Supabase"""
    try:
        # Set the session to sign out
        supabase_client.auth.sign_out()
        return True
    except Exception as e:
        print(f"[SUPABASE AUTH WARNING] Logout error: {e}")
        return False

def get_user_from_token(token: str) -> Optional[SupabaseUser]:
    """Validate JWT token and get user from Supabase"""
    try:
        # Use Supabase to verify the token
        user_response = supabase_client.auth.get_user(token)
        
        if user_response and user_response.user:
            return SupabaseUser(user_response.user.model_dump())
        return None
    except Exception as e:
        print(f"[SUPABASE AUTH] Token validation failed: {e}")
        return None

# Dependency for protected routes
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> SupabaseUser:
    """Get current authenticated user from Supabase JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    user = get_user_from_token(credentials.credentials)
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return user

async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[SupabaseUser]:
    """Get current user if authenticated, otherwise None"""
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

async def get_current_user_ws(
    websocket: WebSocket
) -> Optional[SupabaseUser]:
    """Get current user from WebSocket connection"""
    # Try to get token from query params
    token = websocket.query_params.get("token")
    if not token:
        return None
    
    return get_user_from_token(token)

# Token generation for login response
def create_token_response(user: SupabaseUser, access_token: str, refresh_token: str) -> Token:
    """Create token response for successful login"""
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600,  # 1 hour
        user=user.to_dict()
    )

# Password reset
def request_password_reset(email: str) -> bool:
    """Request password reset email"""
    try:
        supabase_client.auth.reset_password_email(email)
        return True
    except Exception as e:
        print(f"[SUPABASE AUTH] Password reset error: {e}")
        return False

# User profile management (using Supabase database)
def update_user_profile(user_id: str, **kwargs) -> bool:
    """Update user profile in Supabase database"""
    try:
        if supabase_admin:
            supabase_admin.table("profiles").update(kwargs).eq("id", user_id).execute()
            return True
        return False
    except Exception as e:
        print(f"[SUPABASE AUTH] Profile update error: {e}")
        return False

def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user profile from Supabase database"""
    try:
        if supabase_admin:
            response = supabase_admin.table("profiles").select("*").eq("id", user_id).execute()
            if response.data:
                return response.data[0]
        return None
    except Exception as e:
        print(f"[SUPABASE AUTH] Profile fetch error: {e}")
        return None

# API Key management (stored in Supabase)
def generate_api_key(user_id: str) -> str:
    """Generate API key for user"""
    api_key = f"sa_{secrets.token_urlsafe(32)}"
    
    try:
        if supabase_admin:
            # Store in a separate api_keys table or in profiles
            supabase_admin.table("profiles").update({
                "api_key": api_key,
                "api_key_created_at": datetime.utcnow().isoformat()
            }).eq("id", user_id).execute()
            return api_key
    except Exception as e:
        print(f"[SUPABASE AUTH] API key generation error: {e}")
    
    # Fallback - still return the key even if storage fails
    return api_key

def revoke_api_key(user_id: str) -> bool:
    """Revoke user's API key"""
    try:
        if supabase_admin:
            supabase_admin.table("profiles").update({
                "api_key": None,
                "api_key_created_at": None
            }).eq("id", user_id).execute()
            return True
    except Exception as e:
        print(f"[SUPABASE AUTH] API key revocation error: {e}")
    return False

def validate_api_key(api_key: str) -> Optional[SupabaseUser]:
    """Validate API key and return user"""
    try:
        if supabase_admin and api_key:
            response = supabase_admin.table("profiles").select("*").eq("api_key", api_key).execute()
            if response.data:
                user_id = response.data[0].get("id")
                # Get user from Supabase Auth
                if user_id:
                    # We need to get the user from the auth system
                    # This is a simplified version - in production, you'd cache this
                    auth_response = supabase_admin.auth.admin.get_user_by_id(user_id)
                    if auth_response and auth_response.user:
                        return SupabaseUser(auth_response.user.model_dump())
    except Exception as e:
        print(f"[SUPABASE AUTH] API key validation error: {e}")
    return None
