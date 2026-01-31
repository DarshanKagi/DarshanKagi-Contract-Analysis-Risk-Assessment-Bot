"""
Contract Analyzer Module
Orchestrates the full contract analysis pipeline.
"""

from typing import Dict, Any, List, Optional
import os

from .document_parser import process_document
from .nlp_processor import (
    preprocess_text, 
    segment_clauses, 
    extract_entities,
    extract_key_terms,
    analyze_text_structure
)
from .deepseek_client import deepseek_client
from .risk_scorer import (
    calculate_clause_risk,
    calculate_contract_risk,
    generate_risk_summary,
    identify_critical_clauses
)
from .audit_logger import log_analysis


def analyze_contract(file_path: str, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
    """
    Perform full analysis of a contract document.
    
    Args:
        file_path: Path to the contract file
        progress_callback: Optional callback function for progress updates (0-100)
        
    Returns:
        Complete analysis results dictionary
    """
    def update_progress(value: int, message: str = ""):
        if progress_callback:
            progress_callback(value, message)
    
    results = {
        'filename': os.path.basename(file_path),
        'status': 'success',
        'error': None
    }
    
    try:
        # Step 1: Parse document (10%)
        update_progress(5, "Parsing document...")
        original_text, normalized_text, language = process_document(file_path)
        
        results['language'] = language
        results['original_text'] = original_text
        results['normalized_text'] = normalized_text
        update_progress(10, "Document parsed successfully")
        
        # Step 2: Preprocess and analyze structure (15%)
        update_progress(12, "Analyzing document structure...")
        clean_text = preprocess_text(normalized_text)
        structure = analyze_text_structure(clean_text)
        results['structure'] = structure
        update_progress(15, "Structure analysis complete")
        
        # Step 3: Classify contract type (20%)
        update_progress(17, "Classifying contract type...")
        contract_type = deepseek_client.classify_contract_type(clean_text)
        results['contract_type'] = contract_type
        update_progress(20, f"Contract type: {contract_type}")
        
        # Step 4: Extract entities (25%)
        update_progress(22, "Extracting entities...")
        entities = extract_entities(clean_text)
        key_terms = extract_key_terms(clean_text)
        results['entities'] = entities
        results['key_terms'] = key_terms
        update_progress(25, "Entity extraction complete")
        
        # Step 5: Segment clauses (30%)
        update_progress(27, "Segmenting clauses...")
        clauses = segment_clauses(clean_text)
        update_progress(30, f"Found {len(clauses)} clauses")
        
        # Step 6: Analyze each clause (30-70%)
        analyzed_clauses = []
        clause_risks = []
        
        for i, clause in enumerate(clauses):
            # Calculate progress within clause analysis phase
            clause_progress = 30 + int((i / max(len(clauses), 1)) * 40)
            update_progress(clause_progress, f"Analyzing clause {i+1}/{len(clauses)}...")
            
            # Get AI risk assessment
            ai_assessment = deepseek_client.assess_clause_risk(
                clause['text'], 
                clause.get('title', '')
            )
            
            # Calculate normalized risk
            risk_info = calculate_clause_risk(ai_assessment)
            
            # Combine all info
            analyzed_clause = {
                'id': clause['id'],
                'title': clause.get('title', f'Clause {clause["id"]}'),
                'text': clause['text'],
                'clause_type': clause.get('type', 'unknown'),
                'risk_level': risk_info['risk_level'],
                'risk_score': risk_info['risk_score'],
                'risk_category': risk_info['risk_category'],
                'explanation': ai_assessment.get('explanation', ''),
                'concerns': ai_assessment.get('concerns', []),
                'suggested_alternative': ai_assessment.get('suggested_alternative', ''),
                'color': risk_info['color'],
                'emoji': risk_info['emoji']
            }
            
            analyzed_clauses.append(analyzed_clause)
            clause_risks.append(risk_info)
        
        results['clauses'] = analyzed_clauses
        update_progress(70, "Clause analysis complete")
        
        # Step 7: Calculate overall risk (75%)
        update_progress(72, "Calculating overall risk...")
        contract_risk = calculate_contract_risk(clause_risks)
        results['overall_risk_score'] = contract_risk['overall_score']
        results['overall_risk_level'] = contract_risk['overall_level']
        results['risk_summary'] = generate_risk_summary(contract_risk, len(clauses))
        results['risk_details'] = contract_risk
        results['critical_clauses'] = identify_critical_clauses(analyzed_clauses)
        update_progress(75, "Risk calculation complete")
        
        # Step 8: Check compliance (80%)
        update_progress(77, "Checking compliance...")
        compliance_issues = deepseek_client.check_compliance(clean_text)
        results['compliance_issues'] = compliance_issues
        update_progress(80, f"Found {len(compliance_issues)} compliance concerns")
        
        # Step 9: Generate summary (90%)
        update_progress(85, "Generating summary...")
        summary = deepseek_client.generate_plain_summary(clean_text, contract_type)
        results['summary'] = summary
        update_progress(90, "Summary generated")
        
        # Step 10: Generate recommendations (95%)
        update_progress(92, "Generating recommendations...")
        recommendations = deepseek_client.get_recommendations(results)
        results['recommendations'] = recommendations
        update_progress(95, "Recommendations ready")
        
        # Step 11: Log analysis (100%)
        update_progress(98, "Finalizing...")
        log_analysis(
            filename=results['filename'],
            contract_type=contract_type,
            risk_score=contract_risk['overall_score'],
            clauses_analyzed=len(clauses),
            language=language
        )
        
        update_progress(100, "Analysis complete!")
        
    except Exception as e:
        results['status'] = 'error'
        results['error'] = str(e)
        update_progress(100, f"Error: {str(e)}")
    
    return results


def quick_analyze(text: str) -> Dict[str, Any]:
    """
    Perform a quick analysis without full clause breakdown.
    Useful for previews or large documents.
    
    Args:
        text: Contract text
        
    Returns:
        Quick analysis results
    """
    try:
        # Basic preprocessing
        clean_text = preprocess_text(text)
        
        # Get contract type
        contract_type = deepseek_client.classify_contract_type(clean_text)
        
        # Extract entities
        entities = extract_entities(clean_text)
        
        # Get summary
        summary = deepseek_client.generate_plain_summary(clean_text, contract_type)
        
        return {
            'status': 'success',
            'contract_type': contract_type,
            'entities': entities,
            'summary': summary
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def get_analysis_for_display(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format analysis results for UI display.
    
    Args:
        results: Raw analysis results
        
    Returns:
        Formatted results for UI
    """
    if results.get('status') == 'error':
        return {
            'error': results.get('error', 'Unknown error'),
            'display_ready': False
        }
    
    # Format parties list
    parties = results.get('entities', {}).get('parties', [])
    orgs = results.get('entities', {}).get('organizations', [])
    all_parties = list(set(parties + orgs))
    
    # Format clauses for accordion display
    clause_display = []
    for clause in results.get('clauses', []):
        clause_display.append({
            'header': f"{clause['emoji']} {clause['title']} [{clause['risk_level']} Risk]",
            'content': {
                'original': clause['text'][:500] + '...' if len(clause['text']) > 500 else clause['text'],
                'explanation': clause['explanation'],
                'concerns': clause['concerns'],
                'alternative': clause['suggested_alternative']
            },
            'risk_level': clause['risk_level'],
            'color': clause['color']
        })
    
    # Format compliance issues
    compliance_display = []
    for issue in results.get('compliance_issues', []):
        compliance_display.append({
            'issue': issue.get('issue', ''),
            'severity': issue.get('severity', 'Medium'),
            'law': issue.get('relevant_law', ''),
            'recommendation': issue.get('recommendation', '')
        })
    
    return {
        'display_ready': True,
        'contract_type': results.get('contract_type', 'Unknown'),
        'language': 'Hindi' if results.get('language') == 'hi' else 'English',
        'overall_risk': {
            'score': results.get('overall_risk_score', 0),
            'level': results.get('overall_risk_level', 'Unknown'),
            'summary': results.get('risk_summary', '')
        },
        'parties': all_parties,
        'key_dates': results.get('entities', {}).get('dates', []),
        'amounts': results.get('entities', {}).get('amounts', []),
        'summary': results.get('summary', ''),
        'clauses': clause_display,
        'critical_clauses': results.get('critical_clauses', []),
        'compliance_issues': compliance_display,
        'recommendations': results.get('recommendations', []),
        'key_terms': results.get('key_terms', {})
    }
