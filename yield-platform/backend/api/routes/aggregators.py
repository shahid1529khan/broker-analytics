from fastapi import APIRouter, Depends
from typing import Any, Dict, List
from backend.db.supabase_client import get_supabase
from backend.api.deps import get_current_user_with_org

router = APIRouter()

@router.get("/")
def get_aggregators(current_user: Dict[str, Any] = Depends(get_current_user_with_org)):
    supabase = get_supabase()
    res = supabase.table('aggregators').select('*').execute()
    return res.data
