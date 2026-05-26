import logging

logger = logging.getLogger(__name__)

import os
import json
import anthropic
import dateutil.parser
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ValidationError

from backend.services.schema_registry import get_schema, save_schema
from backend.db.models import NormalisedRow

class NormalisationResult(BaseModel):
    success: bool
    rows: List[NormalisedRow] = []
    errors: List[str] = []

COMMON_HEADER_ALIASES = {
    "loan id": "loan_id",
    "loan number": "loan_id",
    "account number": "loan_id",
    "borrower reference": "borrower_reference",
    "borrower": "borrower_reference",
    "client": "borrower_reference",
    "customer": "borrower_reference",
    "lender": "lender_name",
    "lender name": "lender_name",
    "bank": "lender_name",
    "financier": "lender_name",
    "credit provider": "lender_name",
    "settlement date": "settlement_date",
    "drawdown date": "settlement_date",
    "draw down date": "settlement_date",
    "funded date": "settlement_date",
    "commencement date": "settlement_date",
    "original loan amount": "loan_amount_original",
    "loan amount": "loan_amount_original",
    "settlement amount": "loan_amount_original",
    "current balance": "outstanding_balance",
    "loan balance": "outstanding_balance",
    "outstanding balance": "outstanding_balance",
    "remaining balance": "outstanding_balance",
    "trail rate": "trail_rate_percent",
    "trail rate %": "trail_rate_percent",
    "trail commission": "trail_income_this_period",
    "trail income": "trail_income_this_period",
    "ongoing commission": "trail_income_this_period",
    "monthly trail": "trail_income_this_period",
    "net trail": "trail_income_this_period",
    "upfront commission": "upfront_commission",
    "upfront": "upfront_commission",
}

def build_local_mapping(raw_headers: List[str]) -> Dict[str, str]:
    mapping = {}
    for header in raw_headers:
        normalised = str(header).strip().lower()
        mapping[header] = COMMON_HEADER_ALIASES.get(normalised, "UNMAPPED")
    return mapping

def has_required_mapping(mapping: Dict[str, str]) -> bool:
    targets = set(mapping.values())
    return "lender_name" in targets and "outstanding_balance" in targets and "trail_income_this_period" in targets

def clean_currency(val: Any) -> tuple[float, bool]:
    """Normalises all currency values to a float, stripping symbols and commas. Returns (value, had_error)."""
    if val is None:
        return 0.0, False
    if isinstance(val, (int, float)):
        return float(val), False
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ('-', 'na', 'n/a', 'null', 'none'):
        return 0.0, False
    
    # Strip non-numeric artifacts
    val_str = val_str.replace('$', '').replace(',', '').replace(' ', '')
    
    # Handle accounting format for negative numbers: (123.45)
    if val_str.startswith('(') and val_str.endswith(')'):
        val_str = '-' + val_str[1:-1]
        
    try:
        return float(val_str), False
    except ValueError:
        return 0.0, True

def clean_date(val: Any) -> Optional[str]:
    """Normalises date strings to YYYY-MM-DD."""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime('%Y-%m-%d')
        
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ('-', 'na', 'n/a', 'null', 'none'):
        return None
        
    try:
        # Dayfirst=True handles Australian standard formats (DD-MM-YYYY)
        parsed = dateutil.parser.parse(val_str, fuzzy=True, dayfirst=True)
        return parsed.strftime('%Y-%m-%d')
    except Exception:
        return None

def fetch_claude_mapping(raw_headers: List[str], sample_row: Dict[str, Any], aggregator_name: str) -> Dict[str, str]:
    """Calls Claude to intelligently map raw statement headers to the schema."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    system_prompt = """
    You are an expert Australian mortgage data analyst. 
    You have extracted raw tabular data from a mortgage aggregator commission statement. 
    Your job is to map the raw columns onto a unified schema. Return ONLY a valid JSON object.
    No explanation, no markdown wrapping, no extra keys.
    """
    
    user_prompt = f"""
    Aggregator Name: {aggregator_name}
    
    Target schema fields:
    - loan_id
    - borrower_reference
    - lender_name
    - settlement_date
    - loan_amount_original
    - outstanding_balance
    - trail_rate_percent
    - trail_income_this_period
    - upfront_commission

    Rules:
    1. Map "Trail Commission", "Ongoing Commission", "Residual", "Trail Income", "Monthly Trail", "Net Trail" → trail_income_this_period
    2. Map "Loan Balance", "Outstanding", "Current Balance", "Remaining Balance" → outstanding_balance
    3. Map "Settlement Date", "Draw Down Date", "Funded Date", "Commencement Date" → settlement_date
    4. Map "Lender", "Bank", "Financier", "Credit Provider", "Institution" → lender_name
    5. Output JSON where keys are the EXACT raw column names provided, mapping to the target schema fields.
    6. If a column cannot be mapped, map it the value "UNMAPPED".

    Raw Columns detected: {json.dumps(raw_headers)}
    Sample Row data: {json.dumps(sample_row)}
    """

    try:
        # claude-sonnet-4-5: fast, accurate for structured extraction tasks
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            temperature=0.0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        # Parse the JSON response
        text = response.content[0].text.strip()
        
        # Handle if Claude wrapped in markdown despite instructions
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        text = text.strip()
            
        mapping = json.loads(text)
        return mapping
        
    except Exception as e:
        logger.error(f"Claude mapping failed: {e}")
        return {}

def process_raw_data(raw_rows: List[Dict[str, Any]], aggregator_id: str, aggregator_name: str, period_month: str) -> NormalisationResult:
    """
    Main normalisation engine. Checks schema registry, conditionally uses Claude for mapping, 
    cleans values, and yields Pydantic validated rows.
    """
    result = NormalisationResult(success=True, rows=[], errors=[])
    
    if not raw_rows:
        result.success = False
        result.errors.append("No rows provided for normalisation.")
        return result
        
    # Standardise headers from first row
    first_row = raw_rows[0]
    raw_headers = list(first_row.keys())
    
    # 1. Check schema registry
    mapping_schema = get_schema(aggregator_id)
    schema_was_in_registry = True
    
    if not mapping_schema:
        mapping_schema = build_local_mapping(raw_headers)

    if not has_required_mapping(mapping_schema):
        # 2. Invoke Claude to detect mapping if unseen aggregator layout
        schema_was_in_registry = False
        mapping_schema = fetch_claude_mapping(raw_headers, first_row, aggregator_name)
        
        if not mapping_schema:
            result.success = False
            result.errors.append("Failed to ascertain column mapping via schema registry or Claude.")
            return result
            
        # Store for future
        save_schema(aggregator_id, mapping_schema)
        
    # 3. Apply logic per row locally to bypass API limits and speed up ingest
    valid_rows = []
    for i, row in enumerate(raw_rows):
        mapped_data = {
            "period_month": period_month,
            "aggregator_name": aggregator_name,
            "raw_row_index": i,
            "is_flagged": False,
            "lender_name": "", # Default required fallback
            "outstanding_balance": 0.0,
            "trail_income_this_period": 0.0,
        }
        
        unmapped_cols = {}
        
        # Determine validation flagging
        validation_notes = []
        
        for raw_col, val in row.items():
            target_col = mapping_schema.get(raw_col, "UNMAPPED")
            
            if target_col == "UNMAPPED":
                unmapped_cols[raw_col] = val
                continue
                
            # Clean and assign properties
            if target_col in ["loan_amount_original", "outstanding_balance", "trail_rate_percent", "trail_income_this_period", "upfront_commission"]:
                val_float, had_error = clean_currency(val)
                mapped_data[target_col] = val_float
                if had_error:
                    validation_notes.append(f"Invalid currency format in column '{raw_col}'")
                    mapped_data["is_flagged"] = True
            elif target_col == "settlement_date":
                mapped_data[target_col] = clean_date(val)
            else:
                mapped_data[target_col] = str(val).strip() if val is not None else None

        if not mapped_data.get("lender_name"):
            validation_notes.append("Lender name missing.")
            mapped_data["lender_name"] = "UNKNOWN LENDER" 
            mapped_data["is_flagged"] = True
            
        if mapped_data.get("outstanding_balance", -1) < 0:
            validation_notes.append("Negative outstanding balance detected.")
            mapped_data["outstanding_balance"] = 0.0
            mapped_data["is_flagged"] = True
            
        if unmapped_cols:
            # Store unmapped columns in validation_notes to preserve data without schema changes
            validation_notes.append(f"Unmapped data: {json.dumps(unmapped_cols)}")
            
        mapped_data["validation_notes"] = " | ".join(validation_notes) if validation_notes else None

        # Cast to strictly validated Pydantic model
        try:
            validated_row = NormalisedRow(**mapped_data)
            valid_rows.append(validated_row)
        except ValidationError as ve:
            result.errors.append(f"Row {i} fell outside structural rules entirely: {ve}")
            
    result.rows = valid_rows
    
    if len(valid_rows) == 0 and len(raw_rows) > 0:
         result.success = False
         result.errors.append("All rows failed critical structuring constraints.")
         
    return result
