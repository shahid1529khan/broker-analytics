import logging

logger = logging.getLogger(__name__)

from typing import Dict, Any, Optional
from backend.db.supabase_client import get_supabase

def get_schema(aggregator_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a saved column mapping schema for a given aggregator."""
    try:
        supabase = get_supabase()
        response = supabase.table('aggregator_schemas').select('column_mapping').eq('aggregator_id', aggregator_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get('column_mapping')
    except Exception as e:
        logger.error(f"Error fetching schema from registry: {e}")
    return None

def save_schema(aggregator_id: str, mapping: Dict[str, Any]) -> bool:
    """Saves or updates a given column mapping schema to the registry."""
    try:
        supabase = get_supabase()
        data = {
            "aggregator_id": str(aggregator_id),
            "column_mapping": mapping,
            "is_verified": False
        }
        # Upsert based on the unique aggregator_id
        supabase.table('aggregator_schemas').upsert(data, on_conflict='aggregator_id').execute()
        return True
    except Exception as e:
        logger.error(f"Error saving schema to registry: {e}")
        return False
