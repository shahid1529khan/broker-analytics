import logging

logger = logging.getLogger(__name__)

import pdfplumber
import io
import base64
import json
import anthropic
from typing import List, Dict, Any, Union

def _detect_text(pdf_obj: pdfplumber.pdf.PDF) -> bool:
    """Heuristic to detect if PDF contains text (native) or is purely scanned."""
    text_count = 0
    # Check up to first 3 pages
    for page in pdf_obj.pages[:3]:
        text = page.extract_text()
        if text:
            text_count += len(text.strip())
            
    # If there are more than a reasonable amount of text characters, consider it text-based
    return text_count > 100

def _pdf_to_images(file_path_or_bytes: Union[str, bytes]) -> List[str]:
    """Converts a PDF to a list of base64 encoded PNG strings."""
    images_base64 = []
    
    if isinstance(file_path_or_bytes, bytes):
        pdf = pdfplumber.open(io.BytesIO(file_path_or_bytes))
    else:
        pdf = pdfplumber.open(file_path_or_bytes)
        
    with pdf:
        for page in pdf.pages:
            try:
                im = page.to_image(resolution=150)
                pil_image = im.original
                buffered = io.BytesIO()
                pil_image.save(buffered, format="PNG")
                img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                images_base64.append(img_b64)
            except Exception as e:
                # If image extraction fails on a specific page, log/skip
                logger.warning(f"Failed to convert page {page.page_number} to image: {e}")
                
    return images_base64

def _extract_scanned_pdf(file_path_or_bytes: Union[str, bytes]) -> List[Dict[str, Any]]:
    """Uses Claude API with Vision to extract tables from scanned PDFs."""
    images = _pdf_to_images(file_path_or_bytes)
    
    client = anthropic.Anthropic()
    extracted_data = []
    
    for img_b64 in images:
        prompt_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_b64
                }
            },
            {
                "type": "text",
                "text": "This is a scanned mortgage aggregator commission statement. Please extract all tabular data into a strictly structured JSON array of objects. Preserve original column headers exactly as they appear. Output ONLY the JSON array (starting with '[' and ending with ']'), no surrounding markdown, no explanation."
            }
        ]
        
        try:
            # We use sonnet-4-6 (claude-3-5-sonnet-20241022 or latest) as per instructions
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4000,
                temperature=0,
                messages=[{"role": "user", "content": prompt_content}]
            )
            
            text = response.content[0].text
            
            # Simple heuristic to extract JSON array since LLMs sometimes prefix/suffix
            start_idx = text.find('[')
            end_idx = text.rfind(']') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = text[start_idx:end_idx]
                chunk = json.loads(json_str)
                if isinstance(chunk, list):
                    extracted_data.extend(chunk)
                    
        except Exception as e:
            # Continue processing remaining pages on per-page failure
            logger.warning(f"Failed to extract table from scanned page image via Claude: {e}")
            
    return extracted_data

def _extract_text_pdf(pdf_obj: pdfplumber.pdf.PDF) -> List[Dict[str, Any]]:
    """Extracts tables from a native text PDF using pdfplumber."""
    extracted_data = []
    
    for page in pdf_obj.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table or len(table) < 2:
                continue
                
            # Find header row dynamically
            header_idx = 0
            best_score = -1
            keywords = {'trail', 'amount', 'date', 'loan', 'balance', 'name', 'borrower', 'lender', 'commission', 'settlement'}
            
            for i, row in enumerate(table[:20]):
                # Score based on how many keywords appear, and how many columns have content
                score = sum(2 for cell in row if cell and str(cell).lower().strip() in keywords)
                score += sum(1 for cell in row if cell and str(cell).strip())
                if score > best_score:
                    best_score = score
                    header_idx = i
                    
            headers = []
            for c_idx, h in enumerate(table[header_idx]):
                if h and str(h).strip():
                    # Clean up newlines that pdfplumber might add in wrapped headers
                    headers.append(str(h).replace('\n', ' ').strip())
                else:
                    headers.append(f"Column_{c_idx}")
                    
            # Parse data rows
            for row in table[header_idx + 1:]:
                if not row:
                    continue
                # Skip empty rows visually
                if all(cell is None or str(cell).strip() == "" for cell in row):
                    continue
                    
                row_dict = {}
                for col_idx, cell in enumerate(row):
                    if col_idx < len(headers):
                        val = str(cell).replace('\n', ' ').strip() if cell else None
                        row_dict[headers[col_idx]] = val
                        
                extracted_data.append(row_dict)
                
    return extracted_data

def parse_pdf(file_path_or_bytes: Union[str, bytes]) -> List[Dict[str, Any]]:
    """
    Main entry point for parsing PDF statements.
    Returns a list of dicts representing parsed rows.
    """
    is_text_pdf = False
    
    if isinstance(file_path_or_bytes, bytes):
        pdf = pdfplumber.open(io.BytesIO(file_path_or_bytes))
    else:
        pdf = pdfplumber.open(file_path_or_bytes)
        
    with pdf:
        is_text_pdf = _detect_text(pdf)
        if is_text_pdf:
            return _extract_text_pdf(pdf)

    # Scanned PDF fallback
    return _extract_scanned_pdf(file_path_or_bytes)
