"""
Contract Analysis & Risk Assessment Bot
A sophisticated GenAI-powered legal assistant for SMEs to analyze contracts and assess risks.
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import time
import warnings
warnings.filterwarnings('ignore')

# Document parsing
import PyPDF2
import pdfplumber
from docx import Document

# OCR
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image, ImageEnhance, ImageFilter
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠ OCR libraries not available. Install pytesseract and pdf2image for scanned PDF support.")

# NLP
import spacy
from langdetect import detect, LangDetectException

# Embeddings for template matching
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("⚠ Embeddings libraries not available. Template matching will be limited.")

# LLM
import google.generativeai as genai

# UI
import gradio as gr

# PDF generation
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# ============================================================================
# CONFIGURATION
# ============================================================================

GEMINI_API_KEY = "Your API Key"
genai.configure(api_key=GEMINI_API_KEY)

# Directories
AUDIT_LOG_DIR = "audit_logs"
REPORT_DIR = "reports"
os.makedirs(AUDIT_LOG_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# Risk scoring thresholds
RISK_KEYWORDS = {
    "indemnify": 30,
    "hold harmless": 30,
    "unilateral": 40,
    "unilaterally": 40,
    "penalty": 35,
    "liquidated damages": 35,
    "non-compete": 25,
    "non-solicitation": 25,
    "auto-renewal": 20,
    "evergreen": 20,
    "termination without cause": 40,
    "perpetual": 25,
    "irrevocable": 30,
    "exclusive": 20,
    "shall not": 15,
}

# Indian Law Compliance Rules
INDIAN_COMPLIANCE_RULES = {
    "Employment Agreement": {
        "required_clauses": {
            "Provident Fund": "EPF registration and contribution required under EPF Act, 1952",
            "ESI": "Employee State Insurance for establishments with 10+ employees",
            "Gratuity": "Payment of Gratuity Act, 1972 applies after 5 years of service",
            "Notice Period": "Reasonable notice period as per Industrial Employment Act",
            "Leave": "Minimum annual leave provisions under Shops and Establishments Act",
            "Working Hours": "Maximum 48 hours per week as per Factories Act, 1948"
        },
        "max_notice_period_days": 90,
        "jurisdiction": ["India", "Indian courts", "Indian law", "laws of India"]
    },
    "Vendor Contract": {
        "required_clauses": {
            "Payment Terms": "Clear payment schedule required",
            "Deliverables": "Scope of work must be defined",
            "Termination": "Termination conditions required"
        },
        "max_payment_days": 45,  # MSME Payment Act
        "msme_compliance": "If vendor is MSME, payment within 45 days is mandatory (MSMED Act, 2006)"
    },
    "Lease Agreement": {
        "required_clauses": {
            "Rent": "Monthly/annual rent amount",
            "Security Deposit": "Security deposit amount",
            "Maintenance": "Maintenance responsibilities",
            "Duration": "Lease period specification"
        },
        "max_security_deposit_months": 10,
        "registration_threshold_months": 11,
        "registration_note": "Leases exceeding 11 months must be registered under Registration Act, 1908"
    },
    "Service Contract": {
        "required_clauses": {
            "Scope of Services": "Clear definition of services",
            "Payment Terms": "Payment schedule",
            "Termination": "Exit conditions"
        },
        "gst_applicable": True
    }
}

# Standard Clause Templates for Template Matching
STANDARD_CLAUSE_TEMPLATES = {
    "termination_mutual": {
        "text": "Either party may terminate this Agreement by providing 30 days' written notice to the other party.",
        "category": "Termination",
        "risk_level": "Low",
        "description": "Balanced termination clause with mutual rights"
    },
    "termination_cause": {
        "text": "Either party may terminate this Agreement immediately upon written notice if the other party materially breaches any provision.",
        "category": "Termination",
        "risk_level": "Low",
        "description": "Termination for cause with material breach standard"
    },
    "indemnity_mutual": {
        "text": "Each party shall indemnify and hold harmless the other party from losses arising solely from their own negligence or willful misconduct.",
        "category": "Indemnity",
        "risk_level": "Low",
        "description": "Mutual indemnity limited to own wrongdoing"
    },
    "confidentiality_standard": {
        "text": "Confidential information shall be protected for a period of 3 years from the date of disclosure and not used except for the purposes of this Agreement.",
        "category": "Confidentiality",
        "risk_level": "Low",
        "description": "Time-bound confidentiality with clear purpose limitation"
    },
    "ip_work_product": {
        "text": "Intellectual property created specifically for this project shall vest in the Client, while pre-existing IP remains with the original owner.",
        "category": "Intellectual Property",
        "risk_level": "Low",
        "description": "Balanced IP clause protecting both parties"
    },
    "limitation_liability": {
        "text": "Neither party's liability shall exceed the total fees paid under this Agreement in the preceding 12 months, except for gross negligence or willful misconduct.",
        "category": "Liability",
        "risk_level": "Medium",
        "description": "Reasonable liability cap with carve-outs"
    },
    "dispute_resolution": {
        "text": "Disputes shall first be attempted to be resolved through good faith negotiation, failing which through arbitration under the Arbitration and Conciliation Act, 1996.",
        "category": "Dispute Resolution",
        "risk_level": "Low",
        "description": "Standard Indian arbitration clause"
    },
    "force_majeure": {
        "text": "Neither party shall be liable for delays or failures due to circumstances beyond their reasonable control, including natural disasters, war, or government actions.",
        "category": "Force Majeure",
        "risk_level": "Low",
        "description": "Standard force majeure protection"
    },
    "payment_terms": {
        "text": "Payment shall be made within 30 days of invoice receipt via bank transfer to the designated account.",
        "category": "Payment",
        "risk_level": "Low",
        "description": "Clear payment terms (MSME Act compliant)"
    },
    "non_compete_reasonable": {
        "text": "During employment and for 6 months thereafter, Employee shall not engage in directly competitive business within the same geographic market.",
        "category": "Non-Compete",
        "risk_level": "Medium",
        "description": "Reasonable non-compete with time and scope limits"
    }
}

# Legal Entity Extraction Patterns
PARTY_EXTRACTION_PATTERNS = [
    r"(?:between|by and between)\s+([A-Z][A-Za-z\s&.,()]+?)\s+(?:and|,)\s+([A-Z][A-Za-z\s&.,()]+?)(?:\s+hereinafter|\s+\(|,)",
    r"(?:First Party|Party of the First Part)[\s:]+([A-Z][^,\n]+?)(?:\s+hereinafter|\s+\(|,)",
    r"(?:Second Party|Party of the Second Part)[\s:]+([A-Z][^,\n]+?)(?:\s+hereinafter|\s+\(|,)",
    r"(?:Client|Employer|Lessor|Vendor|Licensor)[\s:]+([A-Z][^,\n]+?)(?:\s+hereinafter|\s+\(|,)",
    r"(?:Consultant|Employee|Lessee|Purchaser|Licensee)[\s:]+([A-Z][^,\n]+?)(?:\s+hereinafter|\s+\(|,)"
]


# ============================================================================
# GEMINI API INTEGRATION
# ============================================================================

class GeminiAnalyzer:
    """Handles all Gemini API interactions with retry logic."""
    
    def __init__(self, api_key: str, model_name: str = None):
        self.api_key = api_key
        
        # Discover best available model if not specified
        if model_name is None:
            self.model_name = self._discover_best_model()
            print(f"✓ Auto-discovered model: {self.model_name}")
        else:
            self.model_name = model_name
            print(f"✓ Using specified model: {self.model_name}")
        
        try:
            self.model = genai.GenerativeModel(self.model_name)
            print(f"✓ Gemini model '{self.model_name}' initialized successfully")
        except Exception as e:
            print(f"⚠ Warning: Failed to initialize model '{self.model_name}': {e}")
            # Fallback to basic model
            self.model_name = "gemini-pro"
            self.model = genai.GenerativeModel(self.model_name)
            print(f"✓ Fell back to model: {self.model_name}")
    
    def _discover_best_model(self) -> str:
        """Discover the best available Gemini model from the API."""
        try:
            print("🔍 Discovering available Gemini models...")
            available_models = genai.list_models()
            
            # Filter models that support generateContent
            suitable_models = []
            for model in available_models:
                # Check if model supports generate_content method
                if hasattr(model, 'supported_generation_methods'):
                    if 'generateContent' in model.supported_generation_methods:
                        suitable_models.append(model.name)
                        print(f"  - Found: {model.name}")
            
            if not suitable_models:
                print("⚠ No models found with generateContent support, using default")
                return "gemini-pro"
            
            # Preference order: 2.5 > 2.0 > 1.5 > pro
            # Look for gemini-2.5 family first
            for model_name in suitable_models:
                if "2.5" in model_name or "gemini-2.5" in model_name.lower():
                    print(f"✓ Selected: {model_name} (2.5 family - best)")
                    return model_name
            
            # Look for gemini-2.0 family
            for model_name in suitable_models:
                if ("2.0" in model_name or "gemini-2" in model_name.lower()) and "2.5" not in model_name:
                    print(f"✓ Selected: {model_name} (2.0 family)")
                    return model_name
            
            # Look for gemini-1.5 family
            for model_name in suitable_models:
                if "1.5" in model_name or "gemini-1.5" in model_name.lower():
                    print(f"✓ Selected: {model_name} (1.5 family)")
                    return model_name
            
            # Fallback to first suitable model
            selected = suitable_models[0]
            print(f"✓ Selected: {selected} (first available)")
            return selected
            
        except Exception as e:
            print(f"⚠ Model discovery failed: {e}")
            print("✓ Using default fallback: gemini-pro")
            return "gemini-pro"
    
    def _call_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Call Gemini API with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                error_msg = str(e)
                wait_time = 2 ** attempt
                
                # Enhanced error logging
                print(f"❌ API call failed (attempt {attempt + 1}/{max_retries})")
                print(f"   Model: {self.model_name}")
                print(f"   Error: {error_msg}")
                
                if attempt < max_retries - 1:
                    print(f"   ⏳ Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    # Provide clearer error message
                    if "404" in error_msg or "not found" in error_msg.lower():
                        return f"Error: Model '{self.model_name}' not found. Please restart the application to auto-discover available models."
                    elif "403" in error_msg or "permission" in error_msg.lower():
                        return "Error: API key may be invalid or lacks permissions. Please check your Gemini API key."
                    else:
                        return f"Error: Failed after {max_retries} attempts. {error_msg}"
        return "Error: Maximum retries exceeded"
    
    def classify_contract(self, text: str) -> str:
        """Classify the contract type."""
        prompt = f"""Analyze the following contract and classify it into ONE of these types:
- Employment Agreement
- Vendor Contract
- Lease Agreement
- Partnership Deed
- Service Contract
- NDA (Non-Disclosure Agreement)
- Consulting Agreement
- Licensing Agreement
- Other

Contract text (first 2000 characters):
{text[:2000]}

Return ONLY the contract type, nothing else."""
        
        return self._call_with_retry(prompt).strip()
    
    def analyze_risk(self, clause: str, clause_num: int) -> Dict:
        """Analyze a clause for risks."""
        prompt = f"""Analyze this contract clause for potential risks:

Clause #{clause_num}: {clause}

Provide your analysis in this EXACT JSON format:
{{
    "risk_level": "Low/Medium/High",
    "risk_type": "Financial/Legal/Operational/Reputational",
    "concerns": "Brief description of concerns",
    "recommendation": "Specific actionable recommendation"
}}

Be concise and specific. Return ONLY valid JSON."""
        
        response = self._call_with_retry(prompt)
        
        # Try to parse JSON response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback if no JSON found
                return {
                    "risk_level": "Medium",
                    "risk_type": "Legal",
                    "concerns": response[:200],
                    "recommendation": "Review with legal counsel"
                }
        except json.JSONDecodeError:
            return {
                "risk_level": "Medium",
                "risk_type": "Legal",
                "concerns": "Unable to parse detailed analysis",
                "recommendation": "Manual review recommended"
            }
    
    def explain_clause(self, clause: str, clause_num: int) -> str:
        """Explain a clause in plain language."""
        prompt = f"""Explain this legal clause in simple business English suitable for small business owners:

Clause #{clause_num}: {clause}

Provide a clear explanation covering:
1. What it means in plain language
2. Key obligations or restrictions
3. Potential issues to watch for

Keep it concise (2-3 paragraphs maximum)."""
        
        return self._call_with_retry(prompt)
    
    def suggest_alternatives(self, clause: str) -> str:
        """Suggest alternative wording for unfavorable clauses."""
        prompt = f"""This clause may be unfavorable to one party:

{clause}

Suggest a MORE BALANCED alternative wording that protects both parties fairly.
Keep it concise and practical."""
        
        return self._call_with_retry(prompt)
    
    def generate_summary(self, contract_data: Dict) -> str:
        """Generate executive summary of the contract."""
        prompt = f"""Create a concise executive summary of this contract analysis:

Contract Type: {contract_data.get('type', 'Unknown')}
Number of Clauses: {contract_data.get('num_clauses', 0)}
Overall Risk Score: {contract_data.get('risk_score', 0)}/100
Key Parties: {contract_data.get('parties', 'Not identified')}

Key Findings:
{json.dumps(contract_data.get('key_findings', []), indent=2)}

Provide a 3-paragraph summary covering:
1. Overview of the contract
2. Main risk areas identified
3. Primary recommendations

Keep it professional and actionable."""
        
        return self._call_with_retry(prompt)
    
    def translate_hindi_to_english(self, text: str) -> str:
        """Translate Hindi contract text to English."""
        prompt = f"""Translate this Hindi legal text to English, maintaining legal terminology accuracy:

{text[:3000]}

Provide a clear, accurate English translation."""
        
        return self._call_with_retry(prompt)
    
    def translate_to_hindi(self, text: str) -> str:
        """Translate English text to Hindi for multilingual outputs."""
        prompt = f"""Translate this English text to Hindi, maintaining clarity and accuracy:

{text[:3000]}

Provide a clear, accurate Hindi translation."""
        
        return self._call_with_retry(prompt)



# ============================================================================
# OCR PROCESSOR (Enhancement 1)
# ============================================================================

class OCRProcessor:
    """Handle OCR extraction for scanned PDFs."""
    
    def __init__(self, tesseract_path: str = None):
        if not OCR_AVAILABLE:
            print("⚠ OCR not available. Install pytesseract and pdf2image.")
            return
        
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    @staticmethod
    def is_scanned_pdf(text: str, page_count: int) -> bool:
        """Detect if PDF is likely scanned (low text content)."""
        if page_count == 0:
            return False
        avg_chars = len(text.strip()) / page_count if page_count > 0 else 0
        # If less than 100 characters per page, likely scanned
        return avg_chars < 100
    
    @staticmethod
    def extract_with_ocr(pdf_path: str) -> Tuple[str, Dict]:
        """Extract text from scanned PDF using OCR."""
        if not OCR_AVAILABLE:
            return "OCR libraries not installed", {"error": "OCR unavailable"}
        
        try:
            print("🔍 Using OCR to extract text from scanned PDF...")
            # Convert PDF pages to images
            images = convert_from_path(pdf_path, dpi=300)
            full_text = ""
            
            for i, image in enumerate(images):
                print(f"  Processing page {i+1}/{len(images)}...")
                # Preprocess image for better OCR
                processed = OCRProcessor._preprocess_image(image)
                # Extract text
                text = pytesseract.image_to_string(processed, lang='eng+hin')
                full_text += text + "\n\n"
            
            metadata = {
                "pages": len(images),
                "method": "OCR (Tesseract)",
                "quality": "scanned"
            }
            
            print(f"✓ OCR completed: {len(full_text)} characters extracted")
            return full_text, metadata
        
        except Exception as e:
            error_msg = f"OCR extraction failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg, {"error": str(e)}
    
    @staticmethod
    def _preprocess_image(image: Image) -> Image:
        """Preprocess image for better OCR accuracy."""
        # Convert to grayscale
        image = image.convert('L')
        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        # Sharpen
        image = image.filter(ImageFilter.SHARPEN)
        return image

# ============================================================================
# DOCUMENT PARSER
# ============================================================================================

class DocumentParser:
    """Parse contracts from various file formats."""
    
    @staticmethod
    def parse_pdf(file_path: str) -> Tuple[str, Dict]:
        """Parse PDF file and extract text."""
        text = ""
        metadata = {"pages": 0, "method": "unknown"}
        
        try:
            # Try pdfplumber first (better for complex layouts)
            with pdfplumber.open(file_path) as pdf:
                metadata["pages"] = len(pdf.pages)
                metadata["method"] = "pdfplumber"
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
            
            # Fallback to PyPDF2 if pdfplumber didn't extract much
            if len(text.strip()) < 100:
                text = ""
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    metadata["pages"] = len(pdf_reader.pages)
                    metadata["method"] = "PyPDF2"
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n\n"
            
            # Check if scanned PDF and use OCR if needed (Enhancement 1)
            if OCR_AVAILABLE and OCRProcessor.is_scanned_pdf(text, metadata["pages"]):
                print("⚠ Detected scanned PDF, using OCR...")
                text, ocr_metadata = OCRProcessor.extract_with_ocr(file_path)
                metadata.update(ocr_metadata)
        
        except Exception as e:
            metadata["error"] = str(e)
            text = f"Error parsing PDF: {str(e)}"
        
        return text, metadata
    
    @staticmethod
    def parse_docx(file_path: str) -> Tuple[str, Dict]:
        """Parse DOCX file and extract text."""
        text = ""
        metadata = {"paragraphs": 0}
        
        try:
            doc = Document(file_path)
            metadata["paragraphs"] = len(doc.paragraphs)
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            metadata["error"] = str(e)
            text = f"Error parsing DOCX: {str(e)}"
        
        return text, metadata
    
    @staticmethod
    def parse_txt(file_path: str) -> Tuple[str, Dict]:
        """Parse TXT file."""
        text = ""
        metadata = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            metadata["size_bytes"] = len(text)
        except UnicodeDecodeError:
            # Try different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    text = file.read()
                metadata["encoding"] = "latin-1"
            except Exception as e:
                metadata["error"] = str(e)
                text = f"Error parsing TXT: {str(e)}"
        except Exception as e:
            metadata["error"] = str(e)
            text = f"Error parsing TXT: {str(e)}"
        
        return text, metadata
    
    @staticmethod
    def detect_language(text: str) -> str:
        """Detect the language of the contract."""
        try:
            lang_code = detect(text[:1000])  # Use first 1000 chars
            if lang_code == 'hi':
                return "Hindi"
            elif lang_code == 'en':
                return "English"
            else:
                return f"Other ({lang_code})"
        except LangDetectException:
            return "Unknown"
    
    @staticmethod
    def parse_file(file_path: str) -> Dict:
        """Parse any supported file format."""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            text, metadata = DocumentParser.parse_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            text, metadata = DocumentParser.parse_docx(file_path)
        elif ext == '.txt':
            text, metadata = DocumentParser.parse_txt(file_path)
        else:
            return {
                "text": "",
                "metadata": {"error": f"Unsupported file format: {ext}"},
                "language": "Unknown"
            }
        
        language = DocumentParser.detect_language(text)
        
        return {
            "text": text,
            "metadata": metadata,
            "language": language
        }

# ============================================================================
# NLP PROCESSOR
# ============================================================================

class NLPProcessor:
    """Handle NLP tasks using spaCy."""
    
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Downloading spaCy model...")
            os.system("python -m spacy download en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")
    
    def extract_clauses(self, text: str) -> List[str]:
        """Extract clauses from contract text."""
        clauses = []
        
        # Split by common numbering patterns
        # Patterns: 1. / 1.1 / (a) / Article 1 / Section 1
        patterns = [
            r'\n\s*(\d+\.)\s+',  # 1. 2. 3.
            r'\n\s*(\d+\.\d+)\s+',  # 1.1, 2.3
            r'\n\s*\(([a-z])\)\s+',  # (a) (b) (c)
            r'\n\s*(Article|ARTICLE|Section|SECTION)\s+\d+',
        ]
        
        # Try to split by numbered patterns
        for pattern in patterns:
            matches = list(re.finditer(pattern, text))
            if len(matches) > 3:  # If we found a consistent pattern
                for i, match in enumerate(matches):
                    start = match.end()
                    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                    clause_text = text[start:end].strip()
                    if len(clause_text) > 20:  # Ignore very short clauses
                        clauses.append(clause_text)
                if clauses:
                    return clauses
        
        # Fallback: split by sentences and group into paragraphs
        doc = self.nlp(text[:100000])  # Limit to avoid memory issues
        current_clause = []
        
        for sent in doc.sents:
            current_clause.append(sent.text)
            # Create clause every 3-5 sentences
            if len(current_clause) >= 4:
                clause_text = " ".join(current_clause).strip()
                if len(clause_text) > 50:
                    clauses.append(clause_text)
                current_clause = []
        
        # Add remaining
        if current_clause:
            clause_text = " ".join(current_clause).strip()
            if len(clause_text) > 50:
                clauses.append(clause_text)
        
        return clauses if clauses else [text]  # Return full text if no clauses found
    
    def extract_entities(self, text: str) -> Dict:
        """Extract named entities from contract (Enhanced with legal patterns)."""
        doc = self.nlp(text[:50000])  # Limit for performance
        
        entities = {
            "parties": [],
            "dates": [],
            "amounts": [],
            "locations": [],
            "organizations": []
        }
        
        # Enhancement 5: Use legal-specific regex patterns for party extraction
        for pattern in PARTY_EXTRACTION_PATTERNS:
            matches = re.findall(pattern, text[:5000])  # Check first 5000 chars
            for match in matches:
                if isinstance(match, tuple):
                    entities["parties"].extend([m.strip() for m in match if m])
                else:
                    entities["parties"].append(match.strip())
        
        # Standard spaCy NER
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                entities["parties"].append(ent.text)
            elif ent.label_ == "DATE":
                entities["dates"].append(ent.text)
            elif ent.label_ == "MONEY":
                entities["amounts"].append(ent.text)
            elif ent.label_ == "GPE":  # Geo-political entity
                entities["locations"].append(ent.text)
            elif ent.label_ == "ORG":
                entities["organizations"].append(ent.text)
        
        # Indian currency patterns
        indian_amounts = re.findall(r'(?:Rs\.?|₹)\s*[\d,]+(?:\.\d{2})?', text[:10000])
        entities["amounts"].extend(indian_amounts)
        
        # Deduplicate and clean
        for key in entities:
            # Remove duplicates and empty strings
            entities[key] = [e.strip() for e in list(set(entities[key])) if e.strip()]
            entities[key] = entities[key][:10]  # Keep top 10
        
        return entities
    
    def identify_obligations(self, clause: str) -> Dict:
        """Identify obligations, rights, and prohibitions."""
        doc = self.nlp(clause)
        
        result = {
            "obligations": [],
            "rights": [],
            "prohibitions": []
        }
        
        # Look for modal verbs indicating obligations
        obligation_keywords = ["shall", "must", "required to", "obligated to", "agrees to"]
        right_keywords = ["may", "entitled to", "has the right to", "can"]
        prohibition_keywords = ["shall not", "must not", "prohibited from", "may not"]
        
        for sent in doc.sents:
            sent_text = sent.text.lower()
            
            if any(kw in sent_text for kw in prohibition_keywords):
                result["prohibitions"].append(sent.text)
            elif any(kw in sent_text for kw in obligation_keywords):
                result["obligations"].append(sent.text)
            elif any(kw in sent_text for kw in right_keywords):
                result["rights"].append(sent.text)
        
        return result

# ============================================================================
# RISK ANALYZER
# ============================================================================

class RiskAnalyzer:
    """Analyze contract risks."""
    
    @staticmethod
    def calculate_clause_risk_score(clause: str) -> int:
        """Calculate risk score for a clause based on keywords."""
        score = 0
        clause_lower = clause.lower()
        
        for keyword, points in RISK_KEYWORDS.items():
            if keyword in clause_lower:
                score += points
        
        # Additional risk factors
        if len(clause) > 500 and score > 0:  # Long complex clauses are riskier
            score += 10
        
        # Check for vague language
        vague_terms = ["reasonable", "appropriate", "sufficient", "adequate", "material"]
        vague_count = sum(1 for term in vague_terms if term in clause_lower)
        if vague_count >= 3:
            score += 15
        
        return min(score, 100)  # Cap at 100
    
    @staticmethod
    def get_risk_level(score: int) -> str:
        """Convert score to risk level."""
        if score <= 30:
            return "Low"
        elif score <= 60:
            return "Medium"
        else:
            return "High"
    
    @staticmethod
    def identify_risky_clause_types(clause: str) -> List[str]:
        """Identify types of risky clauses."""
        clause_lower = clause.lower()
        risky_types = []
        
        if "indemnif" in clause_lower or "hold harmless" in clause_lower:
            risky_types.append("Indemnity Clause")
        
        if "penalty" in clause_lower or "liquidated damages" in clause_lower:
            risky_types.append("Penalty Clause")
        
        if "termination" in clause_lower and ("unilateral" in clause_lower or "without cause" in clause_lower):
            risky_types.append("Unilateral Termination")
        
        if "arbitration" in clause_lower or "dispute resolution" in clause_lower:
            risky_types.append("Dispute Resolution")
        
        if "auto-renew" in clause_lower or "evergreen" in clause_lower or "automatic renewal" in clause_lower:
            risky_types.append("Auto-Renewal")
        
        if "non-compete" in clause_lower or "non-solicitation" in clause_lower:
            risky_types.append("Non-Compete/Non-Solicitation")
        
        if "intellectual property" in clause_lower or "ip" in clause_lower or "copyright" in clause_lower:
            risky_types.append("IP Transfer/Ownership")
        
        if "confidential" in clause_lower and "perpetual" in clause_lower:
            risky_types.append("Perpetual Confidentiality")
        
        return risky_types
    
    @staticmethod
    def analyze_contract_risk(clauses: List[Dict]) -> Dict:
        """Calculate overall contract risk."""
        if not clauses:
            return {
                "overall_score": 0,
                "overall_level": "Unknown",
                "clause_distribution": {"Low": 0, "Medium": 0, "High": 0}
            }
        
        scores = [c.get("risk_score", 0) for c in clauses]
        overall_score = sum(scores) // len(scores) if scores else 0
        
        distribution = {"Low": 0, "Medium": 0, "High": 0}
        for clause in clauses:
            level = clause.get("risk_level", "Medium")
            distribution[level] = distribution.get(level, 0) + 1
        
        return {
            "overall_score": overall_score,
            "overall_level": RiskAnalyzer.get_risk_level(overall_score),
            "clause_distribution": distribution,
            "high_risk_count": distribution["High"],
            "medium_risk_count": distribution["Medium"],
            "low_risk_count": distribution["Low"]
        }

# ============================================================================
# INDIAN LAW COMPLIANCE CHECKER (Enhancement 2)
# ============================================================================

class IndianLawComplianceChecker:
    """Check compliance with Indian law requirements."""
    
    @staticmethod
    def check_compliance(contract_type: str, clauses: List[str], text: str) -> Dict:
        """Check contract compliance with Indian law."""
        compliance_report = {
            "compliant": True,
            "missing_clauses": [],
            "violations": [],
            "warnings": [],
            "recommendations": [],
            "score": 100
        }
        
        rules = INDIAN_COMPLIANCE_RULES.get(contract_type, {})
        if not rules:
            compliance_report["warnings"].append(f"No specific compliance rules defined for {contract_type}")
            return compliance_report
        
        # Check required clauses
        required = rules.get("required_clauses", {})
        for clause_name, description in required.items():
            if not IndianLawComplianceChecker._has_clause(clause_name, text):
                compliance_report["missing_clauses"].append({
                    "clause": clause_name,
                    "description": description
                })
                compliance_report["compliant"] = False
                compliance_report["score"] -= 10
        
        # Check jurisdiction
        if "jurisdiction" in rules:
            if not any(j.lower() in text.lower() for j in rules["jurisdiction"]):
                compliance_report["warnings"].append(
                    "Contract does not explicitly specify Indian jurisdiction"
                )
                compliance_report["score"] -= 5
        
        # Contract-specific checks
        if contract_type == "Vendor Contract":
            payment_days = IndianLawComplianceChecker._extract_payment_days(text)
            max_days = rules.get("max_payment_days", 45)
            if payment_days and payment_days > max_days:
                compliance_report["violations"].append(
                    f"Payment terms ({payment_days} days) exceed MSME Act limit ({max_days} days)"
                )
                compliance_report["compliant"] = False
                compliance_report["score"] -= 15
            
            if "msme" in text.lower():
                compliance_report["recommendations"].append(
                    "Vendor is MSME: Ensure payment within 45 days (MSMED Act, 2006)"
                )
        
        elif contract_type == "Lease Agreement":
            # Check registration requirement
            threshold = rules.get("registration_threshold_months", 11)
            if IndianLawComplianceChecker._extract_lease_duration(text) > threshold:
                compliance_report["recommendations"].append(
                    f"Lease exceeds {threshold} months - registration required under Registration Act, 1908"
                )
        
        elif contract_type == "Employment Agreement":
            # Check notice period
            notice_days = IndianLawComplianceChecker._extract_notice_period(text)
            max_notice = rules.get("max_notice_period_days", 90)
            if notice_days and notice_days > max_notice:
                compliance_report["warnings"].append(
                    f"Notice period ({notice_days} days) may be excessive"
                )
        
        compliance_report["score"] = max(0, min(100, compliance_report["score"]))
        return compliance_report
    
    @staticmethod
    def _has_clause(clause_name: str, text: str) -> bool:
        """Check if a clause keyword exists in text."""
        keywords = clause_name.lower().split()
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)
    
    @staticmethod
    def _extract_payment_days(text: str) -> Optional[int]:
        """Extract payment days from text."""
        patterns = [
            r'(\d+)\s*days?\s*(?:of|from)?\s*invoice',
            r'payment.*?within\s*(\d+)\s*days?',
            r'(\d+)\s*days?\s*payment'
        ]
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return int(match.group(1))
        return None
    
    @staticmethod
    def _extract_lease_duration(text: str) -> int:
        """Extract lease duration in months."""
        patterns = [
            r'(\d+)\s*(?:months?|years?)',
            r'period\s*of\s*(\d+)\s*(?:months?|years?)',
            r'term\s*of\s*(\d+)\s*(?:months?|years?)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                duration = int(match.group(1))
                if 'year' in match.group(0):
                    duration *= 12
                return duration
        return 0
    
    @staticmethod
    def _extract_notice_period(text: str) -> Optional[int]:
        """Extract notice period in days."""
        patterns = [
            r'notice.*?(\d+)\s*days?',
            r'(\d+)\s*days?\s*(?:written)?\s*notice',
            r'(\d+)\s*months?\s*notice'
        ]
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                days = int(match.group(1))
                if 'month' in match.group(0):
                    days *= 30
                return days
        return None

# ============================================================================
# TEMPLATE MATCHING ENGINE (Enhancement 5)
# ============================================================================

class TemplateMatchingEngine:
    """Match clauses against standard templates."""
    
    def __init__(self):
        self.templates = STANDARD_CLAUSE_TEMPLATES
        self.embeddings_model = None
        
        # Initialize embeddings model if available
        if EMBEDDINGS_AVAILABLE:
            try:
                print("📊 Loading sentence transformer model for template matching...")
                self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
                # Pre-compute template embeddings
                template_texts = [t["text"] for t in self.templates.values()]
                self.template_embeddings = self.embeddings_model.encode(template_texts)
                print("✓ Template matching model loaded")
            except Exception as e:
                print(f"⚠ Failed to load embeddings model: {e}")
                self.embeddings_model = None
    
    def find_similar_template(self, clause: str) -> Optional[Dict]:
        """Find the most similar standard template for a clause."""
        if not self.embeddings_model:
            # Fallback to keyword matching
            return self._keyword_match(clause)
        
        try:
            # Encode the clause
            clause_embedding = self.embeddings_model.encode([clause])
            
            # Calculate cosine similarity
            similarities = cosine_similarity(clause_embedding, self.template_embeddings)[0]
            
            # Find best match
            best_idx = np.argmax(similarities)
            best_score = similarities[best_idx]
            
            if best_score > 0.5:  # Threshold for similarity
                template_keys = list(self.templates.keys())
                template = self.templates[template_keys[best_idx]]
                
                return {
                    "template_name": template_keys[best_idx],
                    "template_text": template["text"],
                    "category": template["category"],
                    "similarity_score": float(best_score),
                    "risk_level": template["risk_level"],
                    "description": template["description"],
                    "deviation": "Low" if best_score > 0.8 else "Medium" if best_score > 0.6 else "High"
                }
        except Exception as e:
            print(f"Error in template matching: {e}")
        
        return None
    
    def _keyword_match(self, clause: str) -> Optional[Dict]:
        """Fallback keyword-based matching."""
        clause_lower = clause.lower()
        
        # Simple category detection
        if "terminate" in clause_lower or "termination" in clause_lower:
            return {
                "category": "Termination",
                "similarity_score": 0.6,
                "deviation": "Medium",
                "description": "Termination clause detected (keyword-based)"
            }
        elif "indemnif" in clause_lower:
            return {
                "category": "Indemnity",
                "similarity_score": 0.6,
                "deviation": "Medium",
                "description": "Indemnity clause detected (keyword-based)"
            }
        
        return None

# ============================================================================
# REPORT GENERATOR
# ============================================================================

class ReportGenerator:
    """Generate PDF reports of contract analysis."""
    
    @staticmethod
    def generate_pdf_report(analysis_data: Dict, output_path: str):
        """Generate a professional PDF report."""
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Title
        story.append(Paragraph("Contract Analysis Report", title_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Metadata
        metadata_data = [
            ["Contract Type:", analysis_data.get('contract_type', 'Unknown')],
            ["Analysis Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["File Name:", analysis_data.get('file_name', 'Unknown')],
            ["Language:", analysis_data.get('language', 'Unknown')],
        ]
        
        metadata_table = Table(metadata_data, colWidths=[2*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Risk Summary
        story.append(Paragraph("Risk Assessment Summary", heading_style))
        risk_summary = analysis_data.get('risk_summary', {})
        
        risk_color = colors.green
        if risk_summary.get('overall_level') == 'Medium':
            risk_color = colors.orange
        elif risk_summary.get('overall_level') == 'High':
            risk_color = colors.red
        
        risk_data = [
            ["Overall Risk Level:", risk_summary.get('overall_level', 'Unknown')],
            ["Risk Score:", f"{risk_summary.get('overall_score', 0)}/100"],
            ["High Risk Clauses:", str(risk_summary.get('high_risk_count', 0))],
            ["Medium Risk Clauses:", str(risk_summary.get('medium_risk_count', 0))],
            ["Low Risk Clauses:", str(risk_summary.get('low_risk_count', 0))],
        ]
        
        risk_table = Table(risk_data, colWidths=[2.5*inch, 3.5*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('BACKGROUND', (1, 0), (1, 0), risk_color),
            ('TEXTCOLOR', (1, 0), (1, 0), colors.white),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(risk_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Executive Summary
        if analysis_data.get('summary'):
            story.append(Paragraph("Executive Summary", heading_style))
            summary_text = analysis_data.get('summary', 'No summary available.')
            story.append(Paragraph(summary_text, styles['BodyText']))
            story.append(Spacer(1, 0.2 * inch))
        
        # Key Findings
        story.append(Paragraph("Key Findings", heading_style))
        findings = analysis_data.get('key_findings', [])
        for i, finding in enumerate(findings[:10], 1):
            story.append(Paragraph(f"{i}. {finding}", styles['BodyText']))
        story.append(Spacer(1, 0.2 * inch))
        
        # Recommendations
        story.append(Paragraph("Recommendations", heading_style))
        recommendations = analysis_data.get('recommendations', [])
        for i, rec in enumerate(recommendations[:10], 1):
            story.append(Paragraph(f"{i}. {rec}", styles['BodyText']))
        
        story.append(PageBreak())
        
        # Detailed Clause Analysis
        story.append(Paragraph("Detailed Clause Analysis", heading_style))
        clauses = analysis_data.get('analyzed_clauses', [])[:15]  # Limit to 15 clauses
        
        for clause in clauses:
            # Clause header
            clause_title = f"Clause #{clause.get('number', '?')} - Risk: {clause.get('risk_level', 'Unknown')}"
            story.append(Paragraph(clause_title, styles['Heading3']))
            
            # Clause text (truncated)
            clause_text = clause.get('text', '')[:300] + '...' if len(clause.get('text', '')) > 300 else clause.get('text', '')
            story.append(Paragraph(f"<i>{clause_text}</i>", styles['BodyText']))
            story.append(Spacer(1, 0.1 * inch))
            
            # Analysis
            if clause.get('explanation'):
                story.append(Paragraph(f"<b>Explanation:</b> {clause['explanation'][:200]}", styles['BodyText']))
            
            story.append(Spacer(1, 0.2 * inch))
        
        # Disclaimer
        story.append(PageBreak())
        story.append(Paragraph("Important Disclaimer", heading_style))
        disclaimer = """This analysis is provided for informational purposes only and does not constitute legal advice. 
        The risk assessments and recommendations are generated by AI and should not be relied upon as a substitute for 
        consultation with a qualified legal professional. Always consult with an attorney before making legal decisions 
        based on contract terms."""
        story.append(Paragraph(disclaimer, styles['BodyText']))
        
        # Build PDF
        doc.build(story)

# ============================================================================
# AUDIT LOGGER
# ============================================================================

class AuditLogger:
    """Log contract analyses to JSON files."""
    
    @staticmethod
    def log_analysis(analysis_data: Dict):
        """Save analysis to audit log."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(AUDIT_LOG_DIR, f"analysis_{timestamp}.json")
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "file_name": analysis_data.get("file_name", "Unknown"),
            "contract_type": analysis_data.get("contract_type", "Unknown"),
            "language": analysis_data.get("language", "Unknown"),
            "risk_summary": analysis_data.get("risk_summary", {}),
            "num_clauses": len(analysis_data.get("analyzed_clauses", [])),
            "key_findings": analysis_data.get("key_findings", []),
            "recommendations": analysis_data.get("recommendations", [])
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, indent=2, ensure_ascii=False)
        
        return log_file

# ============================================================================
# MAIN ANALYSIS ENGINE
# ============================================================================

class ContractAnalysisEngine:
    """Main engine orchestrating the analysis."""
    
    def __init__(self):
        self.gemini = GeminiAnalyzer(GEMINI_API_KEY)
        self.parser = DocumentParser()
        self.nlp = NLPProcessor()
        self.risk_analyzer = RiskAnalyzer()
        # New enhancement components
        self.compliance_checker = IndianLawComplianceChecker()
        self.template_matcher = TemplateMatchingEngine()

    
    def analyze_contract(self, file_path: str, progress=gr.Progress()) -> Dict:
        """Complete contract analysis pipeline."""
        result = {
            "success": False,
            "error": None,
            "file_name": os.path.basename(file_path),
        }
        
        try:
            # Step 1: Parse document
            progress(0.1, desc="Parsing document...")
            parsed = self.parser.parse_file(file_path)
            
            if not parsed["text"] or len(parsed["text"].strip()) < 50:
                result["error"] = "Could not extract text from document"
                return result
            
            result["language"] = parsed["language"]
            result["metadata"] = parsed["metadata"]
            
            # Step 2: Translate if Hindi
            text = parsed["text"]
            if "Hindi" in parsed["language"]:
                progress(0.15, desc="Translating Hindi to English...")
                text = self.gemini.translate_hindi_to_english(text)
                result["translated"] = True
            
            # Step 3: Classify contract
            progress(0.2, desc="Classifying contract type...")
            contract_type = self.gemini.classify_contract(text)
            result["contract_type"] = contract_type
            
            # Step 4: Extract entities
            progress(0.25, desc="Extracting entities...")
            entities = self.nlp.extract_entities(text)
            result["entities"] = entities
            
            # Step 5: Extract clauses
            progress(0.3, desc="Extracting clauses...")
            clauses = self.nlp.extract_clauses(text)
            result["num_clauses"] = len(clauses)
            
            # Step 6: Analyze each clause
            analyzed_clauses = []
            key_findings = []
            recommendations = []
            
            # Limit to 20 clauses for performance
            clauses_to_analyze = clauses[:20]
            
            for i, clause in enumerate(clauses_to_analyze):
                progress(0.3 + (0.5 * (i / len(clauses_to_analyze))), 
                        desc=f"Analyzing clause {i+1}/{len(clauses_to_analyze)}...")
                
                # Calculate risk score
                risk_score = self.risk_analyzer.calculate_clause_risk_score(clause)
                risk_level = self.risk_analyzer.get_risk_level(risk_score)
                risky_types = self.risk_analyzer.identify_risky_clause_types(clause)
                
                # Get obligations/rights/prohibitions
                obligations_data = self.nlp.identify_obligations(clause)
                
                clause_data = {
                    "number": i + 1,
                    "text": clause,
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "risky_types": risky_types,
                    "obligations": obligations_data
                }
                
                # For high and medium risk clauses, get detailed AI analysis
                if risk_level in ["High", "Medium"]:
                    gemini_analysis = self.gemini.analyze_risk(clause, i + 1)
                    clause_data["ai_analysis"] = gemini_analysis
                    
                    # Get plain language explanation
                    explanation = self.gemini.explain_clause(clause, i + 1)
                    clause_data["explanation"] = explanation
                    
                    # Add to findings
                    if risky_types:
                        finding = f"{', '.join(risky_types)} detected in Clause #{i+1}"
                        key_findings.append(finding)
                    
                    # Add recommendation
                    if gemini_analysis.get("recommendation"):
                        recommendations.append(f"Clause #{i+1}: {gemini_analysis['recommendation']}")
                
                # Enhancement 5: Template matching
                template_match = self.template_matcher.find_similar_template(clause)
                if template_match:
                    clause_data["template_match"] = template_match
                    if template_match.get("deviation") == "High":
                        key_findings.append(f"Clause #{i+1} deviates significantly from standard {template_match.get('category')} template")
                
                analyzed_clauses.append(clause_data)
            
            result["analyzed_clauses"] = analyzed_clauses
            result["key_findings"] = key_findings
            result["recommendations"] = recommendations
            
            # Step 7: Calculate overall risk
            progress(0.85, desc="Calculating overall risk...")
            risk_summary = self.risk_analyzer.analyze_contract_risk(analyzed_clauses)
            result["risk_summary"] = risk_summary
            
            # Enhancement 2: Indian law compliance check
            progress(0.87, desc="Checking Indian law compliance...")
            compliance_report = self.compliance_checker.check_compliance(
                contract_type, clauses, text
            )
            result["compliance_report"] = compliance_report
            
            # Add compliance findings
            for missing in compliance_report.get("missing_clauses", []):
                key_findings.append(f"Missing required clause: {missing['clause']}")
            for violation in compliance_report.get("violations", []):
                key_findings.append(f"Compliance violation: {violation}")
            
            # Step 8: Generate summary
            progress(0.9, desc="Generating executive summary...")
            summary = self.gemini.generate_summary({
                "type": contract_type,
                "num_clauses": len(clauses),
                "risk_score": risk_summary["overall_score"],
                "parties": ", ".join(entities.get("parties", [])[:3]) if entities.get("parties") else "Not identified",
                "key_findings": key_findings[:5]
            })
            result["summary"] = summary
            
            # Step 9: Save audit log
            progress(0.95, desc="Saving audit log...")
            log_file = AuditLogger.log_analysis(result)
            result["log_file"] = log_file
            
            result["success"] = True
            progress(1.0, desc="Analysis complete!")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"Analysis error: {e}")
        
        return result

# ============================================================================
# GRADIO INTERFACE
# ============================================================================

def create_gradio_interface():
    """Create the Gradio UI."""
    
    engine = ContractAnalysisEngine()
    
    def analyze_contract_ui(file):
        """UI wrapper for contract analysis."""
        if file is None:
            return "Please upload a contract file.", "", "", "", "", ""
        
        try:
            # Run analysis
            result = engine.analyze_contract(file.name)
            
            if not result["success"]:
                error_msg = f"❌ Analysis failed: {result.get('error', 'Unknown error')}"
                return error_msg, "", "", "", "", ""
            
            # Format summary tab
            summary_md = f"""# Contract Analysis Summary

## Overview
- **Contract Type:** {result.get('contract_type', 'Unknown')}
- **Language:** {result.get('language', 'Unknown')}
- **Number of Clauses Analyzed:** {result.get('num_clauses', 0)}

## Executive Summary
{result.get('summary', 'No summary available.')}

## Key Parties
{', '.join(result['entities'].get('parties', ['Not identified'])[:5])}

## Key Dates
{', '.join(result['entities'].get('dates', ['Not identified'])[:5])}

## Financial Terms
{', '.join(result['entities'].get('amounts', ['Not identified'])[:5])}
"""
            
            # Format risk tab
            risk_summary = result.get('risk_summary', {})
            risk_level = risk_summary.get('overall_level', 'Unknown')
            risk_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}.get(risk_level, "⚪")
            
            risk_md = f"""# Risk Assessment

## Overall Risk Level: {risk_emoji} {risk_level}

**Risk Score:** {risk_summary.get('overall_score', 0)}/100

## Risk Distribution
- 🔴 **High Risk Clauses:** {risk_summary.get('high_risk_count', 0)}
- 🟡 **Medium Risk Clauses:** {risk_summary.get('medium_risk_count', 0)}
- 🟢 **Low Risk Clauses:** {risk_summary.get('low_risk_count', 0)}

## Key Findings
"""
            for i, finding in enumerate(result.get('key_findings', [])[:10], 1):
                risk_md += f"{i}. {finding}\n"
            
            # Format detailed analysis tab
            detailed_md = "# Detailed Clause Analysis\n\n"
            for clause in result.get('analyzed_clauses', [])[:15]:
                risk_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}.get(clause.get('risk_level', 'Medium'), "⚪")
                
                detailed_md += f"""## Clause #{clause.get('number')} {risk_emoji} {clause.get('risk_level')}

**Clause Text:**  
_{clause.get('text', '')[:400]}{'...' if len(clause.get('text', '')) > 400 else ''}_

**Risk Score:** {clause.get('risk_score', 0)}/100

"""
                if clause.get('risky_types'):
                    detailed_md += f"**Identified Issues:** {', '.join(clause['risky_types'])}\n\n"
                
                if clause.get('explanation'):
                    detailed_md += f"**Plain Language Explanation:**  \n{clause['explanation']}\n\n"
                
                if clause.get('ai_analysis'):
                    ai = clause['ai_analysis']
                    detailed_md += f"**Risk Type:** {ai.get('risk_type', 'N/A')}  \n"
                    detailed_md += f"**Concerns:** {ai.get('concerns', 'N/A')}  \n"
                    detailed_md += f"**Recommendation:** {ai.get('recommendation', 'N/A')}\n\n"
                
                detailed_md += "---\n\n"
            
            # Format recommendations tab
            rec_md = "# Recommendations\n\n"
            for i, rec in enumerate(result.get('recommendations', [])[:15], 1):
                rec_md += f"{i}. {rec}\n\n"
            
            rec_md += """
---

## Next Steps
1. **Review high-risk clauses** with your legal team
2. **Negotiate problematic terms** before signing
3. **Set calendar reminders** for important dates and renewal periods
4. **Keep this report** for future reference

## ⚠️ Important Disclaimer
This analysis is AI-generated and provided for informational purposes only. It does not constitute legal advice. 
Always consult with a qualified attorney before making legal decisions.
"""
            
            # Enhancement 2: Format compliance tab
            compliance_report = result.get('compliance_report', {})
            compliance_md = f"# Indian Law Compliance Report\n\n"
            
            compliance_score = compliance_report.get('score', 100)
            compliant = compliance_report.get('compliant', True)
            
            if compliant:
                compliance_md += f"## ✅ Overall Status: COMPLIANT (Score: {compliance_score}/100)\n\n"
            else:
                compliance_md += f"## ⚠️ Overall Status: NON-COMPLIANT (Score: {compliance_score}/100)\n\n"
            
            # Missing clauses
            missing = compliance_report.get('missing_clauses', [])
            if missing:
                compliance_md += f"### ❌ Missing Required Clauses ({len(missing)})\n\n"
                for item in missing:
                    compliance_md += f"- **{item['clause']}**  \n  {item['description']}\n\n"
            
            # Violations
            violations = compliance_report.get('violations', [])
            if violations:
                compliance_md += f"### 🚨 Legal Violations ({len(violations)})\n\n"
                for v in violations:
                    compliance_md += f"- {v}\n\n"
            
            # Warnings
            warnings = compliance_report.get('warnings', [])
            if warnings:
                compliance_md += f"### ⚠️ Warnings ({len(warnings)})\n\n"
                for w in warnings:
                    compliance_md += f"- {w}\n\n"
            
            # Recommendations
            comp_recs = compliance_report.get('recommendations', [])
            if comp_recs:
                compliance_md += f"### 💡 Compliance Recommendations ({len(comp_recs)})\n\n"
                for r in comp_recs:
                    compliance_md += f"- {r}\n\n"
            
            if not missing and not violations:
                compliance_md += "### ✅ No compliance issues detected\n\n"
                compliance_md += "This contract appears to meet basic Indian law requirements.\n\n"
            
            compliance_md += """
---

### Applicable Laws
- **Employment**: EPF Act 1952, ESI Act 1948, Gratuity Act 1972
- **Vendor**: MSMED Act 2006 (45-day payment rule)
- **Lease**: Registration Act 1908
- **General**: Indian Contract Act 1872, Arbitration Act 1996

⚠️ This is a preliminary compliance check. Consult a legal expert for comprehensive review.
"""
            
            # Generate PDF report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_path = os.path.join(REPORT_DIR, f"report_{timestamp}.pdf")
            ReportGenerator.generate_pdf_report(result, pdf_path)
            
            return summary_md, risk_md, detailed_md, rec_md, compliance_md, pdf_path
            
        except Exception as e:
            error_msg = f"❌ Error during analysis: {str(e)}"
            return error_msg, "", "", "", "", ""
    
    # Create interface
    with gr.Blocks(title="Contract Analysis & Risk Assessment Bot", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 📄 Contract Analysis & Risk Assessment Bot
        
        **Analyze contracts, identify risks, and get actionable recommendations in plain language.**
        
        Upload your contract (PDF, DOCX, or TXT) and get a comprehensive analysis powered by AI.
        """)
        
        with gr.Row():
            file_input = gr.File(
                label="Upload Contract",
                file_types=[".pdf", ".docx", ".doc", ".txt"],
                type="filepath"
            )
        
        analyze_btn = gr.Button("🔍 Analyze Contract", variant="primary", size="lg")
        
        with gr.Tabs() as tabs:
            with gr.Tab("📊 Summary"):
                summary_output = gr.Markdown()
            
            with gr.Tab("⚠️ Risk Assessment"):
                risk_output = gr.Markdown()
            
            with gr.Tab("🔍 Detailed Analysis"):
                detailed_output = gr.Markdown()
            
            with gr.Tab("💡 Recommendations"):
                recommendations_output = gr.Markdown()
            
            with gr.Tab("⚖️ Indian Law Compliance"):
                compliance_output = gr.Markdown()
        
        with gr.Row():
            pdf_output = gr.File(label="📥 Download PDF Report")
        
        gr.Markdown("""
        ---
        ### About This Tool
        This AI-powered assistant helps small and medium business owners understand complex contracts by:
        - Extracting and analyzing contract clauses
        - Identifying potential legal risks
        - Checking Indian law compliance (EPF, ESI, MSME Act, etc.)
        - Providing plain language explanations
        - Suggesting alternative clauses
        - Generating comprehensive reports
        - **NEW:** OCR support for scanned PDFs
        - **NEW:** Template matching for clause evaluation
        
        **Supported Languages:** English and Hindi  
        **Supported Formats:** PDF (including scanned), DOCX, TXT
        
        ⚠️ **Disclaimer:** This tool provides guidance, not legal advice. Consult with a legal professional for binding decisions.
        """)
        
        # Connect button to analysis function
        analyze_btn.click(
            fn=analyze_contract_ui,
            inputs=[file_input],
            outputs=[summary_output, risk_output, detailed_output, recommendations_output, compliance_output, pdf_output]
        )
    
    return demo

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Contract Analysis & Risk Assessment Bot")
    print("=" * 70)
    print("\nInitializing components...")
    print("✓ Gemini API configured")
    print("✓ Document parsers ready")
    print("✓ NLP processor ready")
    print("✓ Risk analyzer ready")
    print("✓ Report generator ready")
    print("\nLaunching Gradio interface...")
    print("=" * 70)
    
    demo = create_gradio_interface()
    demo.launch(
        share=False,
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True
    )
