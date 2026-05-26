from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime, date
from typing import Optional, Dict, Any, Literal
from uuid import UUID

# Base config for all models
class CoreModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# 1. ORGANISATIONS
class OrganisationBase(CoreModel):
    name: str

class Organisation(OrganisationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

# 2. USERS
class UserBase(CoreModel):
    auth_id: UUID
    email: EmailStr
    organisation_id: UUID

class User(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

# 3. AGGREGATORS
class AggregatorBase(CoreModel):
    name: str

class Aggregator(AggregatorBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

# 4. BROKER CLIENTS
BrokerClientStatus = Literal['active', 'archived', 'pending documents', 'under offer', 'sold']

class BrokerClientBase(CoreModel):
    organisation_id: UUID
    name: str
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    status: BrokerClientStatus = 'active'
    notes: Optional[str] = None

class BrokerClientCreate(CoreModel):
    name: str
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    status: BrokerClientStatus = 'active'
    notes: Optional[str] = None

class BrokerClient(BrokerClientBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

# 5. STATEMENT UPLOADS
UploadStatus = Literal['pending', 'processing', 'completed', 'failed', 'review_required']

class StatementUploadBase(CoreModel):
    client_id: UUID
    aggregator_id: UUID
    period_month: str = Field(..., pattern=r'^\d{4}-\d{2}$')
    status: UploadStatus = 'pending'
    file_name: str
    file_path: Optional[str] = None
    row_count: int = 0
    flagged_row_count: int = 0
    error_message: Optional[str] = None

class StatementUploadCreate(StatementUploadBase):
    pass

class StatementUpload(StatementUploadBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

class StatementUploadResponse(CoreModel):
    """Returned after upload processing completes"""
    upload_id: UUID
    status: UploadStatus
    row_count: int
    flagged_row_count: int
    error_message: Optional[str] = None

# 6. LOAN ROWS (NORMALISED DATA)
class NormalisedRow(CoreModel):
    """
    Used for parsing output before database insertion.
    Validation rules enforced before database insertion:
    - lender_name must not be empty
    - outstanding_balance >= 0
    - period_month format
    
    NOTE: Using float instead of Decimal here because supabase-py returns numeric types as floats by default.
    If audit-grade exact Decimal precision is ever needed, switch these, but be prepared for type coercion.
    """
    loan_id: Optional[str] = None
    borrower_reference: Optional[str] = None
    lender_name: str = Field(..., min_length=1)
    settlement_date: Optional[date] = None
    loan_amount_original: Optional[float] = None
    outstanding_balance: float = Field(..., ge=0)
    trail_rate_percent: Optional[float] = None
    trail_income_this_period: float
    upfront_commission: float = 0.00
    period_month: str = Field(..., pattern=r'^\d{4}-\d{2}$')
    aggregator_name: str
    raw_row_index: int
    is_flagged: bool = False
    validation_notes: Optional[str] = None

class LoanRowCreate(NormalisedRow):
    """Extends parsed row with foreign keys needed for DB insertion"""
    upload_id: UUID
    client_id: UUID

class LoanRow(LoanRowCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

# 7. AGGREGATOR SCHEMAS
class AggregatorSchemaBase(CoreModel):
    aggregator_id: UUID
    column_mapping: Dict[str, Any]
    is_verified: bool = False

class AggregatorSchemaCreate(AggregatorSchemaBase):
    pass

class AggregatorSchema(AggregatorSchemaBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
