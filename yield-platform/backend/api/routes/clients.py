from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Any, Dict
from uuid import UUID
from backend.db.supabase_client import get_supabase
from backend.db.models import BrokerClient, BrokerClientCreate
from backend.api.deps import get_current_user_with_org

router = APIRouter()

@router.get("/", response_model=List[BrokerClient])
def get_clients(current_user: Dict[str, Any] = Depends(get_current_user_with_org)):
    """Get all broker clients for the current user's organisation."""
    supabase = get_supabase()
    org_id = current_user["organisation_id"]
    
    clients_res = supabase.table('broker_clients').select('*').eq('organisation_id', org_id).execute()
    return clients_res.data

@router.get("/{client_id}", response_model=BrokerClient)
def get_client(client_id: UUID, current_user: Dict[str, Any] = Depends(get_current_user_with_org)):
    """Get a specific broker client."""
    supabase = get_supabase()
    org_id = current_user["organisation_id"]
    
    client_res = supabase.table('broker_clients').select('*').eq('id', str(client_id)).eq('organisation_id', org_id).execute()
    
    if not client_res.data:
        raise HTTPException(status_code=404, detail="Client not found")
        
    return client_res.data[0]

@router.post("/", response_model=BrokerClient, status_code=status.HTTP_201_CREATED)
def create_client(client_in: BrokerClientCreate, current_user: Dict[str, Any] = Depends(get_current_user_with_org)):
    """Create a new broker client."""
    supabase = get_supabase()
    org_id = current_user["organisation_id"]

    data = client_in.model_dump(mode="json")
    data["organisation_id"] = org_id
    
    try:
        res = supabase.table('broker_clients').insert(data).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create client")
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{client_id}", response_model=BrokerClient)
def update_client(client_id: UUID, client_in: BrokerClientCreate, current_user: Dict[str, Any] = Depends(get_current_user_with_org)):
    """Update a broker client."""
    supabase = get_supabase()
    org_id = current_user["organisation_id"]
    
    # Verify existing
    client_res = supabase.table('broker_clients').select('id').eq('id', str(client_id)).eq('organisation_id', org_id).execute()
    if not client_res.data:
        raise HTTPException(status_code=404, detail="Client not found")
        
    data = client_in.model_dump(mode="json")
        
    try:
        res = supabase.table('broker_clients').update(data).eq('id', str(client_id)).execute()
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
