"""
Authentication and Authorization Module - Supabase Edition
JWT-based authentication using Supabase Auth exclusively
"""

from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

# Import the new Supabase auth module
from app.supabase_auth import (
    SupabaseUser, Token, TokenData, UserCreate, UserLogin, UserResponse,
    PasswordReset, PasswordChange,
    create_supabase_user, authenticate_supabase_user, refresh_supabase_token,
    logout_supabase_user, get_user_from_token, create_token_response,
    request_password_reset, update_user_profile, get_user_profile,
    generate_api_key, revoke_api_key, validate_api_key,
    get_current_user as get_current_supabase_user,
    get_current_user_optional as get_current_supabase_user_optional,
    get_current_user_ws as get_current_supabase_user_ws,
    supabase_client, supabase_admin
)

# Re-export for backward compatibility
__all__ = [
    'Token', 'UserCreate', 'UserLogin', 'UserResponse', 'PasswordReset', 'PasswordChange',
    'create_user', 'authenticate_user', 'login_user', 'refresh_access_token',
    'logout_user', 'get_current_user', 'get_current_user_optional', 'get_current_user_ws',
    'get_current_active_user', 'get_admin_user', 'generate_user_api_key', 'revoke_user_api_key',
    'get_user_from_api_key', 'log_audit_event'
]

# Security
security = HTTPBearer(auto_error=False)

# Convert SupabaseUser to the format expected by existing code
def convert_to_user_response(user: SupabaseUser) -> Dict[str, Any]:
    """Convert SupabaseUser to UserResponse format"""
    return {
        "id": user.id,
        "email": user.email,
        "username": user.email,  # Use email as username
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "is_admin": user.user_metadata.get("is_admin", False),
        "created_at": user.created_at,
        "last_login": user.last_login,
        "supabase_synced": True
    }

# User CRUD Operations
def create_user(user_data: UserCreate) -> tuple[Dict[str, Any], bool]:
    """Create a new user in Supabase Auth
    
    Returns:
        tuple: (User dict, True - always synced with Supabase)
    """
    user, _ = create_supabase_user(user_data)
    return convert_to_user_response(user), True

def authenticate_user(username: str, password: str) -> Optional[SupabaseUser]:
    """Authenticate user with Supabase Auth"""
    try:
        user, _, _ = authenticate_supabase_user(username, password)
        return user
    except HTTPException:
        return None

# API Key management
def generate_user_api_key(user_id: str) -> str:
    """Generate API key for user"""
    return generate_api_key(user_id)

def revoke_user_api_key(user_id: str) -> bool:
    """Revoke user's API key"""
    return revoke_api_key(user_id)

async def get_user_from_api_key(api_key: str) -> Optional[SupabaseUser]:
    """Get user from API key"""
    return validate_api_key(api_key)

# Authentication Dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> SupabaseUser:
    """Get current authenticated user from Supabase JWT token"""
    return await get_current_supabase_user(credentials)

async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[SupabaseUser]:
    """Get current user if authenticated, otherwise None"""
    return await get_current_supabase_user_optional(credentials)

async def get_current_active_user(
    current_user: SupabaseUser = Depends(get_current_user)
) -> SupabaseUser:
    """Ensure user is active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user

async def get_admin_user(
    current_user: SupabaseUser = Depends(get_current_user)
) -> SupabaseUser:
    """Ensure user is admin"""
    is_admin = current_user.user_metadata.get("is_admin", False)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_current_user_ws(
    websocket: WebSocket
) -> Optional[SupabaseUser]:
    """Get current user from WebSocket connection"""
    return await get_current_supabase_user_ws(websocket)

# Audit Logging - Now uses Supabase
def log_audit_event(
    action: str,
    resource_type: str,
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict] = None,
    request: Optional[Request] = None,
    success: bool = True,
    error_message: Optional[str] = None
):
    """Log an audit event to Supabase"""
    try:
        if supabase_admin:
            audit_data = {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details,
                "ip_address": request.client.host if request else None,
                "user_agent": request.headers.get("user-agent") if request else None,
                "success": success,
                "error_message": error_message,
                "timestamp": datetime.utcnow().isoformat()
            }
            supabase_admin.table("audit_logs").insert(audit_data).execute()
    except Exception as e:
        print(f"[AUDIT LOG ERROR] {e}")

# Login/Token Functions
def login_user(
    username: str, 
    password: str, 
    request: Optional[Request] = None
) -> Token:
    """Authenticate user and generate tokens using Supabase"""
    try:
        user, access_token, refresh_token = authenticate_supabase_user(username, password)
        
        # Log successful login
        log_audit_event(
            action="LOGIN_SUCCESS",
            resource_type="user",
            user_id=user.id,
            resource_id=user.id,
            request=request,
            success=True
        )
        
        return create_token_response(user, access_token, refresh_token)
        
    except HTTPException as e:
        # Log failed login
        log_audit_event(
            action="LOGIN_FAILED",
            resource_type="user",
            details={"username": username, "error": e.detail},
            request=request,
            success=False,
            error_message=e.detail
        )
        raise

def refresh_access_token(refresh_token: str) -> Dict[str, str]:
    """Generate new access token from refresh token"""
    return refresh_supabase_token(refresh_token)

def logout_user(user_id: str, access_token: str, request: Optional[Request] = None):
    """Log user logout"""
    logout_supabase_user(access_token)
    
    log_audit_event(
        action="LOGOUT",
        resource_type="user",
        user_id=user_id,
        resource_id=user_id,
        request=request,
        success=True
    )
