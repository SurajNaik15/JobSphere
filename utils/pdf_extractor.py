# utils/pdf_extractor.py
# Extracts job-related information from government recruitment PDFs

import pdfplumber
import re


def extract_text_from_pdf(pdf_path):
    """Read all text from a PDF file page by page."""
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return full_text


def extract_qualification(text):
    """Try to find qualification/education requirements from the text."""
    patterns = [
        r'(?:qualification|educational qualification|education)[:\s]+([^\n\.]{10,120})',
        r'(?:degree|graduate|bachelor|master|diploma)[^\n]{0,80}',
        r'(?:B\.?Tech|B\.?E|B\.?Sc|M\.?Tech|M\.?Sc|MBA|MCA|B\.?Com|B\.?A)[^\n]{0,60}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()[:200]
    return "Not specified"


def extract_age_limit(text):
    """Find age limit mentioned in the PDF."""
    patterns = [
        r'age limit[:\s]+(\d{2})\s*(?:to|-|–)\s*(\d{2})\s*years?',
        r'minimum age[:\s]+(\d{2}).*?maximum age[:\s]+(\d{2})',
        r'(\d{2})\s*(?:to|-|–)\s*(\d{2})\s*years?\s*(?:of age|age)',
        r'age[:\s]+(\d{2})\s*(?:to|-|–)\s*(\d{2})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if match.lastindex >= 2:
                return f"{match.group(1)} - {match.group(2)} Years"
            return match.group(1).strip()
    return "As per notification"


def extract_salary(text):
    """Find salary or pay scale from the PDF."""
    patterns = [
        r'(?:pay scale|salary|pay band|remuneration|stipend)[:\s]+(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\s*(?:to|-|–)\s*[\d,]+)?)',
        r'(?:Rs\.?|INR|₹)\s*([\d,]+(?:\s*(?:to|-|–)\s*[\d,]+)?)\s*(?:per month|pm|p\.m\.)?',
        r'level[\s-]+(\d+)[^\n]{0,60}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return "Rs. " + match.group(1).strip()
    return "As per 7th Pay Commission"


def extract_last_date(text):
    """Find the application last date from the PDF."""
    patterns = [
        r'last date[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'closing date[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'apply (?:before|by|on or before)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',  # fallback: any date format
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw_date = match.group(1).strip()
            # Try to convert to YYYY-MM-DD for MySQL
            return convert_date(raw_date)
    return None


def convert_date(date_str):
    """Convert various date formats to YYYY-MM-DD."""
    from datetime import datetime
    formats = ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%d/%m/%y', '%d-%m-%y']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def extract_all(pdf_path):
    """Main function: extract all fields from a PDF and return as dict."""
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return None

    result = {
        'raw_text': text[:3000],  # Store first 3000 chars for preview
        'qualification': extract_qualification(text),
        'age_limit': extract_age_limit(text),
        'salary': extract_salary(text),
        'last_date': extract_last_date(text),
    }
    return result
