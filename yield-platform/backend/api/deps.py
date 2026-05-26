from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any
from backend.db.supabase_client import get_supabase

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Any:
    token = credentials.credentials
    supabase = get_supabase()
    try:
        # Verify the token using the Supabase client
        # In supabase-py, get_user() expects the token either globally set or we can pass it
        user_resp = supabase.auth.get_user(token)
        if not user_resp or not user_resp.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_resp.user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user_with_org(current_user: Any = Depends(get_current_user)) -> Dict[str, Any]:
    supabase = get_supabase()
    user_res = supabase.table('users').select('organisation_id').eq('auth_id', current_user.id).execute()
    if not user_res.data:
        raise HTTPException(status_code=403, detail="User not associated with an organisation")
    return {
        "id": current_user.id,
        "email": getattr(current_user, "email", ""),
        "organisation_id": user_res.data[0]['organisation_id']
    }

def verify_client_access(client_id: str, user_with_org: Dict[str, Any]) -> str:
    supabase = get_supabase()
    org_id = user_with_org["organisation_id"]
    client_res = supabase.table('broker_clients').select('id').eq('id', client_id).eq('organisation_id', org_id).execute()
    if not client_res.data:
        raise HTTPException(status_code=404, detail="Client not found or access denied")
    return client_id
