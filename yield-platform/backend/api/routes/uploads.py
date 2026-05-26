import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from typing import Any, Dict, List
from uuid import UUID
from backend.db.supabase_client import get_supabase
from backend.api.deps import get_current_user_with_org, verify_client_access
from backend.db.models import StatementUploadResponse, StatementUpload
from backend.services.pdf_parser import parse_pdf
from backend.services.excel_parser import parse_excel
from backend.services.claude_normaliser import process_raw_data
import os
import uuid

router = APIRouter()

def process_upload_task(upload_id: str, client_id: str, aggregator_id: str, agg_name: str, period_month: str, file_name: str, file_bytes: bytes):
    supabase = get_supabase()
    
    try:
        raw_rows = []
        lower_name = file_name.lower()
        if lower_name.endswith('.pdf'):
            raw_rows = parse_pdf(file_bytes)
        elif lower_name.endswith('.xlsx') or lower_name.endswith('.xls'):
            raw_rows = parse_excel(file_bytes, file_name)
        else:
            raise ValueError("Unsupported file format. Must be PDF, XLSX, or XLS.")
            
        norm_result = process_raw_data(raw_rows, aggregator_id, agg_name, period_month)
        
        if not norm_result.success:
            error_msg = "; ".join(norm_result.errors)
            supabase.table('statement_uploads').update({
                "status": "failed",
                "error_message": error_msg[:255]
            }).eq('id', upload_id).execute()
            return
            
        db_rows = []
        flagged_count = 0
        for row in norm_result.rows:
            row_dict = row.model_dump(mode="json")
            row_dict["upload_id"] = upload_id
            row_dict["client_id"] = client_id
            db_rows.append(row_dict)
            if row_dict.get("is_flagged"):
                flagged_count += 1
                
        if db_rows:
            chunk_size = 500
            for i in range(0, len(db_rows), chunk_size):
                chunk = db_rows[i:i + chunk_size]
                supabase.table('loan_rows').insert(chunk).execute()
                
        final_status = "review_required" if flagged_count > 0 else "completed"
        
        supabase.table('statement_uploads').update({
            "status": final_status,
            "row_count": len(db_rows),
            "flagged_row_count": flagged_count
        }).eq('id', upload_id).execute()
        
    except Exception as e:
        supabase.table('statement_uploads').update({
            "status": "failed",
            "error_message": f"Processing error: {str(e)}"
        }).eq('id', upload_id).execute()

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def upload_statement(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    client_id: UUID = Form(...),
    aggregator_id: UUID = Form(...),
    period_month: str = Form(...),
    current_user: Dict[str, Any] = Depends(get_current_user_with_org)
):
    supabase = get_supabase()
    
    # 1. Verify user's organisation matches client's organisation
    verify_client_access(str(client_id), current_user)
        
    # Get aggregator name
    agg_res = supabase.table('aggregators').select('name').eq('id', str(aggregator_id)).execute()
    if not agg_res.data:
        raise HTTPException(status_code=404, detail="Aggregator not found")
    agg_name = agg_res.data[0]['name']

    # Read file bytes
    file_bytes = await file.read()
    file_name = file.filename or 'upload.ext'
    
    file_path = f"statements/{client_id}/{uuid.uuid4()}_{file_name}"
    
    try:
        supabase.storage.from_('statements').upload(
            path=file_path,
            file=file_bytes,
            file_options={"content-type": file.content_type}
        )
    except Exception as e:
        logger.warning(f"Storage upload skipped; keeping logical file path only: {e}")
    
    # Create statement_upload record
    upload_data = {
        "client_id": str(client_id),
        "aggregator_id": str(aggregator_id),
        "period_month": period_month,
        "status": "pending",
        "file_name": file_name,
        "file_path": file_path,
        "row_count": 0,
        "flagged_row_count": 0
    }
    
    upload_res = supabase.table('statement_uploads').insert(upload_data).execute()
    if not upload_res.data:
        raise HTTPException(status_code=500, detail="Failed to create upload record")
        
    upload_id = upload_res.data[0]['id']
    
    background_tasks.add_task(process_upload_task, upload_id, str(client_id), str(aggregator_id), agg_name, period_month, file_name, file_bytes)
    
    return {"upload_id": upload_id, "status": "pending"}

@router.get("/{upload_id}", response_model=StatementUploadResponse)
def get_upload_status(upload_id: UUID, current_user: Dict[str, Any] = Depends(get_current_user_with_org)):
    supabase = get_supabase()
    res = supabase.table('statement_uploads').select('*').eq('id', str(upload_id)).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Upload not found")
        
    record = res.data[0]
    verify_client_access(record['client_id'], current_user)
    
    return StatementUploadResponse(
        upload_id=record['id'],
        status=record['status'],
        row_count=record.get('row_count', 0),
        flagged_row_count=record.get('flagged_row_count', 0),
        error_message=record.get('error_message')
    )

@router.get("/", response_model=List[StatementUpload])
def list_uploads(client_id: UUID, current_user: Dict[str, Any] = Depends(get_current_user_with_org)):
    verify_client_access(str(client_id), current_user)
    supabase = get_supabase()
    res = supabase.table('statement_uploads').select('*').eq('client_id', str(client_id)).order('created_at', desc=True).execute()
    return res.data
