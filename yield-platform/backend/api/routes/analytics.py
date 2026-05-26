from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any, Dict, List, Optional
from uuid import UUID
from backend.api.deps import get_current_user_with_org, verify_client_access
from backend.services.analytics_engine import AnalyticsEngine

router = APIRouter()

@router.get("/{client_id}/dashboard-summary")
def get_dashboard_summary(
    client_id: UUID, 
    periods: Optional[List[str]] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user_with_org)
):
    """Retrieve all analytics metrics for the dashboard."""
    str_client_id = verify_client_access(str(client_id), current_user)
    
    engine = AnalyticsEngine(str_client_id, periods)
    return engine.get_all_analytics()

@router.get("/{client_id}/loan-age")
def get_loan_age(
    client_id: UUID, 
    periods: Optional[List[str]] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user_with_org)
):
    str_client_id = verify_client_access(str(client_id), current_user)
    engine = AnalyticsEngine(str_client_id, periods)
    if not engine.rows:
        return {"error": "No data"}
    return engine.get_loan_age_analysis()

@router.get("/{client_id}/average-loan-size")
def get_average_loan_size(
    client_id: UUID, 
    periods: Optional[List[str]] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user_with_org)
):
    str_client_id = verify_client_access(str(client_id), current_user)
    engine = AnalyticsEngine(str_client_id, periods)
    if not engine.rows:
        return {"error": "No data"}
    return engine.get_average_loan_size()

@router.get("/{client_id}/trail-income")
def get_trail_income(
    client_id: UUID, 
    periods: Optional[List[str]] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user_with_org)
):
    str_client_id = verify_client_access(str(client_id), current_user)
    engine = AnalyticsEngine(str_client_id, periods)
    if not engine.rows:
        return {"error": "No data"}
    return engine.get_trail_income_analysis()

@router.get("/{client_id}/run-off")
def get_run_off(
    client_id: UUID, 
    periods: Optional[List[str]] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user_with_org)
):
    str_client_id = verify_client_access(str(client_id), current_user)
    engine = AnalyticsEngine(str_client_id, periods)
    if not engine.rows:
        return {"error": "No data"}
    return engine.get_run_off_analysis()

@router.get("/{client_id}/concentration")
def get_concentration(
    client_id: UUID, 
    periods: Optional[List[str]] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user_with_org)
):
    str_client_id = verify_client_access(str(client_id), current_user)
    engine = AnalyticsEngine(str_client_id, periods)
    if not engine.rows:
        return {"error": "No data"}
    return engine.get_lender_concentration()
