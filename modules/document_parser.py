"""
Document Parser Module
Handles extraction of text from PDF, DOCX, and TXT files with language detection.
"""

import os
from typing import Tuple
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator


def parse_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        from pypdf2 import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    
    text_content = []
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_content.append(page_text)
        return "\n".join(text_content)
    except Exception as e:
        raise Exception(f"Error parsing PDF: {str(e)}")


def parse_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    from docx import Document
    
    try:
        doc = Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(paragraphs)
    except Exception as e:
        raise Exception(f"Error parsing DOCX: {str(e)}")


def parse_txt(file_path: str) -> str:
    """Extract text from a TXT file."""
    encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    
    raise Exception("Could not decode text file with any supported encoding")


def parse_document(file_path: str) -> str:
    """
    Parse a document based on its file extension.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Extracted text content
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        return parse_pdf(file_path)
    elif ext in ['.docx', '.doc']:
        return parse_docx(file_path)
    elif ext == '.txt':
        return parse_txt(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def detect_language(text: str) -> str:
    """
    Detect the language of the given text.
    
    Args:
        text: Input text
        
    Returns:
        Language code ('en' for English, 'hi' for Hindi, etc.)
    """
    try:
        # Use a sample of text for detection (first 1000 chars)
        sample = text[:1000] if len(text) > 1000 else text
        lang = detect(sample)
        return lang
    except LangDetectException:
        return 'en'  # Default to English


def translate_to_english(text: str, source_lang: str = 'hi') -> str:
    """
    Translate text to English using Google Translator.
    
    Args:
        text: Text to translate
        source_lang: Source language code
        
    Returns:
        Translated text in English
    """
    if source_lang == 'en':
        return text
    
    try:
        translator = GoogleTranslator(source=source_lang, target='en')
        
        # Handle long texts by chunking (Google has a 5000 char limit)
        max_chunk_size = 4500
        if len(text) <= max_chunk_size:
            return translator.translate(text)
        
        # Split into chunks at sentence boundaries
        chunks = []
        current_chunk = ""
        sentences = text.replace('\n', ' \n ').split('. ')
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Translate each chunk
        translated_chunks = []
        for chunk in chunks:
            if chunk.strip():
                translated_chunks.append(translator.translate(chunk))
        
        return " ".join(translated_chunks)
    
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return text  # Return original if translation fails


def process_document(file_path: str) -> Tuple[str, str, str]:
    """
    Process a document: parse, detect language, and normalize to English.
    
    Args:
        file_path: Path to the document
        
    Returns:
        Tuple of (original_text, normalized_english_text, detected_language)
    """
    # Parse the document
    original_text = parse_document(file_path)
    
    # Detect language
    detected_lang = detect_language(original_text)
    
    # Normalize to English if needed
    if detected_lang != 'en':
        normalized_text = translate_to_english(original_text, detected_lang)
    else:
        normalized_text = original_text
    
    return original_text, normalized_text, detected_lang
