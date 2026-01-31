"""
NLP Processor Module
Handles text preprocessing, clause segmentation, and entity extraction using spaCy.
"""

import re
from typing import List, Dict, Any, Optional
from dateutil import parser as date_parser


# Try to load spaCy, with fallback if not available
try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        nlp = None
except ImportError:
    nlp = None


def preprocess_text(text: str) -> str:
    """
    Clean and preprocess contract text.
    
    Args:
        text: Raw contract text
        
    Returns:
        Cleaned text
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Normalize line breaks
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Remove special characters but keep legal punctuation
    text = re.sub(r'[^\w\s.,;:()"\'-₹$%@&/\\]', '', text)
    
    return text.strip()


def segment_clauses(text: str) -> List[Dict[str, Any]]:
    """
    Segment contract text into individual clauses.
    
    Args:
        text: Contract text
        
    Returns:
        List of clause dictionaries with id, text, and title
    """
    clauses = []
    
    # Common clause numbering patterns
    patterns = [
        r'(?:^|\n)\s*(\d+\.)\s*([A-Z][A-Z\s]+)\s*\n',  # "1. TITLE"
        r'(?:^|\n)\s*(\d+\.\d+)\s+',  # "1.1"
        r'(?:^|\n)\s*(ARTICLE\s+[IVXLC]+)[:\s]',  # "ARTICLE I:"
        r'(?:^|\n)\s*(SECTION\s+\d+)[:\s]',  # "SECTION 1:"
        r'(?:^|\n)\s*([A-Z]\.)\s+',  # "A."
    ]
    
    # Try to find clause boundaries
    all_matches = []
    for pattern in patterns:
        matches = list(re.finditer(pattern, text, re.MULTILINE))
        for match in matches:
            all_matches.append((match.start(), match.group()))
    
    # Sort by position
    all_matches.sort(key=lambda x: x[0])
    
    if not all_matches:
        # If no clear structure, split by paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        for i, para in enumerate(paragraphs):
            if len(para) > 50:  # Only include substantial paragraphs
                clauses.append({
                    'id': i + 1,
                    'title': f"Paragraph {i + 1}",
                    'text': para,
                    'type': 'unknown'
                })
    else:
        # Extract text between clause markers
        for i, (start, marker) in enumerate(all_matches):
            end = all_matches[i + 1][0] if i + 1 < len(all_matches) else len(text)
            clause_text = text[start:end].strip()
            
            # Try to extract title from the clause
            title_match = re.match(r'^[\d.]+\s*([A-Z][A-Z\s]+)', clause_text)
            title = title_match.group(1).strip() if title_match else f"Clause {i + 1}"
            
            clauses.append({
                'id': i + 1,
                'title': title,
                'text': clause_text,
                'type': identify_clause_type(clause_text)
            })
    
    return clauses


def identify_clause_type(clause_text: str) -> str:
    """
    Identify whether a clause represents an obligation, right, or prohibition.
    
    Args:
        clause_text: Text of a single clause
        
    Returns:
        Clause type: 'obligation', 'right', 'prohibition', or 'neutral'
    """
    text_lower = clause_text.lower()
    
    # Obligation indicators
    obligation_keywords = [
        'shall', 'must', 'will be required', 'agrees to', 'undertakes to',
        'is obligated', 'has the duty', 'is responsible for', 'shall ensure'
    ]
    
    # Right indicators
    right_keywords = [
        'may', 'is entitled to', 'has the right', 'reserves the right',
        'at the option of', 'shall be entitled', 'can', 'is authorized'
    ]
    
    # Prohibition indicators
    prohibition_keywords = [
        'shall not', 'must not', 'may not', 'is prohibited', 'cannot',
        'will not', 'is not permitted', 'is not allowed', 'forbidden'
    ]
    
    # Check for prohibitions first (more specific)
    for keyword in prohibition_keywords:
        if keyword in text_lower:
            return 'prohibition'
    
    # Check for obligations
    for keyword in obligation_keywords:
        if keyword in text_lower:
            return 'obligation'
    
    # Check for rights
    for keyword in right_keywords:
        if keyword in text_lower:
            return 'right'
    
    return 'neutral'


def extract_entities(text: str) -> Dict[str, List[Any]]:
    """
    Extract named entities from contract text.
    
    Args:
        text: Contract text
        
    Returns:
        Dictionary of extracted entities
    """
    entities = {
        'parties': [],
        'dates': [],
        'amounts': [],
        'durations': [],
        'jurisdictions': [],
        'organizations': []
    }
    
    # Use spaCy if available
    if nlp:
        doc = nlp(text[:100000])  # Limit to prevent memory issues
        
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                if ent.text not in entities['parties']:
                    entities['parties'].append(ent.text)
            elif ent.label_ == 'ORG':
                if ent.text not in entities['organizations']:
                    entities['organizations'].append(ent.text)
            elif ent.label_ == 'DATE':
                entities['dates'].append(ent.text)
            elif ent.label_ == 'MONEY':
                entities['amounts'].append(ent.text)
            elif ent.label_ == 'GPE':
                entities['jurisdictions'].append(ent.text)
    
    # Supplement with regex patterns
    
    # Extract Indian currency amounts
    rupee_pattern = r'₹\s*[\d,]+(?:\.\d{2})?|Rs\.?\s*[\d,]+(?:\.\d{2})?|INR\s*[\d,]+(?:\.\d{2})?'
    rupee_matches = re.findall(rupee_pattern, text, re.IGNORECASE)
    entities['amounts'].extend([m for m in rupee_matches if m not in entities['amounts']])
    
    # Extract dollar amounts
    dollar_pattern = r'\$\s*[\d,]+(?:\.\d{2})?|USD\s*[\d,]+(?:\.\d{2})?'
    dollar_matches = re.findall(dollar_pattern, text, re.IGNORECASE)
    entities['amounts'].extend([m for m in dollar_matches if m not in entities['amounts']])
    
    # Extract duration patterns
    duration_pattern = r'\d+\s*(?:years?|months?|days?|weeks?)'
    duration_matches = re.findall(duration_pattern, text, re.IGNORECASE)
    entities['durations'] = list(set(duration_matches))
    
    # Extract common jurisdiction patterns
    jurisdiction_patterns = [
        r'courts?\s+(?:of|in|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'jurisdiction\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'governed\s+by\s+(?:the\s+)?laws?\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
    ]
    for pattern in jurisdiction_patterns:
        matches = re.findall(pattern, text)
        entities['jurisdictions'].extend(matches)
    
    # Remove duplicates
    for key in entities:
        entities[key] = list(set(entities[key]))
    
    return entities


def extract_key_terms(text: str) -> Dict[str, Any]:
    """
    Extract key contractual terms.
    
    Args:
        text: Contract text
        
    Returns:
        Dictionary of key terms
    """
    terms = {
        'effective_date': None,
        'termination_date': None,
        'notice_period': None,
        'governing_law': None,
        'dispute_resolution': None
    }
    
    text_lower = text.lower()
    
    # Effective date
    effective_patterns = [
        r'effective\s+(?:as\s+of\s+)?(\w+\s+\d{1,2},?\s+\d{4})',
        r'dated\s+(?:as\s+of\s+)?(\w+\s+\d{1,2},?\s+\d{4})',
        r'commencing\s+(?:on\s+)?(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    for pattern in effective_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            terms['effective_date'] = match.group(1)
            break
    
    # Notice period
    notice_pattern = r'(\d+)\s*(?:days?|months?)\s*(?:written\s+)?notice'
    notice_match = re.search(notice_pattern, text_lower)
    if notice_match:
        terms['notice_period'] = notice_match.group(0)
    
    # Governing law
    gov_law_pattern = r'governed\s+by\s+(?:the\s+)?laws?\s+of\s+([^.]+)'
    gov_match = re.search(gov_law_pattern, text, re.IGNORECASE)
    if gov_match:
        terms['governing_law'] = gov_match.group(1).strip()
    
    # Dispute resolution
    if 'arbitration' in text_lower:
        terms['dispute_resolution'] = 'Arbitration'
    elif 'mediation' in text_lower:
        terms['dispute_resolution'] = 'Mediation'
    elif 'litigation' in text_lower or 'court' in text_lower:
        terms['dispute_resolution'] = 'Litigation'
    
    return terms


def analyze_text_structure(text: str) -> Dict[str, Any]:
    """
    Analyze the overall structure of the contract.
    
    Args:
        text: Contract text
        
    Returns:
        Structure analysis results
    """
    lines = text.split('\n')
    words = text.split()
    
    return {
        'total_lines': len(lines),
        'total_words': len(words),
        'total_characters': len(text),
        'avg_words_per_line': len(words) / max(len(lines), 1),
        'has_numbered_clauses': bool(re.search(r'^\s*\d+\.', text, re.MULTILINE)),
        'has_sections': bool(re.search(r'SECTION|ARTICLE', text, re.IGNORECASE)),
        'has_definitions': bool(re.search(r'DEFINITIONS?|INTERPRETATIONS?', text, re.IGNORECASE))
    }
