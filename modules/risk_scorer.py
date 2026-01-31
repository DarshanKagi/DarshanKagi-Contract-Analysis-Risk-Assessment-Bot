"""
Risk Scorer Module
Calculates risk scores at clause and contract levels.
"""

from typing import Dict, List, Any
from config import RISK_WEIGHTS, RISK_THRESHOLDS


def get_risk_label(score: int) -> str:
    """
    Convert a numeric risk score to a label.
    
    Args:
        score: Risk score (0-100)
        
    Returns:
        Risk label: "Low", "Medium", or "High"
    """
    if score <= RISK_THRESHOLDS['low'][1]:
        return "Low"
    elif score <= RISK_THRESHOLDS['medium'][1]:
        return "Medium"
    else:
        return "High"


def get_risk_color(level: str) -> str:
    """
    Get display color for risk level.
    
    Args:
        level: Risk level string
        
    Returns:
        Color code
    """
    colors = {
        "Low": "#22c55e",      # Green
        "Medium": "#f59e0b",   # Orange
        "High": "#ef4444"      # Red
    }
    return colors.get(level, "#6b7280")


def get_risk_emoji(level: str) -> str:
    """
    Get emoji for risk level.
    
    Args:
        level: Risk level string
        
    Returns:
        Emoji string
    """
    emojis = {
        "Low": "🟢",
        "Medium": "🟡",
        "High": "🔴"
    }
    return emojis.get(level, "⚪")


def calculate_clause_risk(clause_assessment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process and normalize clause risk assessment.
    
    Args:
        clause_assessment: Raw assessment from AI
        
    Returns:
        Normalized risk assessment
    """
    # Extract or default values
    risk_score = clause_assessment.get('risk_score', 50)
    risk_level = clause_assessment.get('risk_level', 'Medium')
    risk_category = clause_assessment.get('risk_category', 'general')
    
    # Ensure score is in valid range
    risk_score = max(0, min(100, int(risk_score)))
    
    # Ensure level matches score
    if risk_score <= 30:
        risk_level = "Low"
    elif risk_score <= 60:
        risk_level = "Medium"
    else:
        risk_level = "High"
    
    # Apply category weight modifier
    category_weight = RISK_WEIGHTS.get(risk_category, 0.1)
    weighted_score = int(risk_score * (1 + (category_weight - 0.1)))
    weighted_score = max(0, min(100, weighted_score))
    
    return {
        'risk_score': risk_score,
        'weighted_score': weighted_score,
        'risk_level': risk_level,
        'risk_category': risk_category,
        'category_weight': category_weight,
        'color': get_risk_color(risk_level),
        'emoji': get_risk_emoji(risk_level)
    }


def calculate_contract_risk(clause_risks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate overall contract risk from clause-level risks.
    
    Args:
        clause_risks: List of clause risk assessments
        
    Returns:
        Contract-level risk assessment
    """
    if not clause_risks:
        return {
            'overall_score': 0,
            'overall_level': "Low",
            'high_risk_count': 0,
            'medium_risk_count': 0,
            'low_risk_count': 0,
            'risk_distribution': {},
            'top_concerns': []
        }
    
    # Count by level
    high_count = sum(1 for c in clause_risks if c.get('risk_level') == 'High')
    medium_count = sum(1 for c in clause_risks if c.get('risk_level') == 'Medium')
    low_count = sum(1 for c in clause_risks if c.get('risk_level') == 'Low')
    
    # Calculate weighted average
    total_weighted = sum(c.get('weighted_score', 50) for c in clause_risks)
    avg_score = total_weighted / len(clause_risks)
    
    # Add penalty for high-risk clauses
    high_risk_penalty = high_count * 5
    avg_score = min(100, avg_score + high_risk_penalty)
    
    # Determine overall level
    overall_level = get_risk_label(int(avg_score))
    
    # Get distribution by category
    category_distribution = {}
    for c in clause_risks:
        cat = c.get('risk_category', 'general')
        if cat not in category_distribution:
            category_distribution[cat] = {'count': 0, 'total_score': 0}
        category_distribution[cat]['count'] += 1
        category_distribution[cat]['total_score'] += c.get('risk_score', 50)
    
    # Find top concerns (highest scoring categories)
    top_concerns = []
    for cat, data in category_distribution.items():
        avg = data['total_score'] / data['count']
        if avg >= 50:
            top_concerns.append({
                'category': cat,
                'average_score': round(avg, 1),
                'count': data['count']
            })
    
    top_concerns.sort(key=lambda x: x['average_score'], reverse=True)
    
    return {
        'overall_score': round(avg_score, 1),
        'overall_level': overall_level,
        'high_risk_count': high_count,
        'medium_risk_count': medium_count,
        'low_risk_count': low_count,
        'risk_distribution': category_distribution,
        'top_concerns': top_concerns[:5],
        'color': get_risk_color(overall_level),
        'emoji': get_risk_emoji(overall_level)
    }


def generate_risk_summary(contract_risk: Dict[str, Any], clause_count: int) -> str:
    """
    Generate a human-readable risk summary.
    
    Args:
        contract_risk: Contract-level risk assessment
        clause_count: Total number of clauses analyzed
        
    Returns:
        Risk summary text
    """
    level = contract_risk['overall_level']
    score = contract_risk['overall_score']
    high = contract_risk['high_risk_count']
    medium = contract_risk['medium_risk_count']
    
    summary = f"**Overall Risk: {level}** (Score: {score}/100)\n\n"
    
    if level == "High":
        summary += "⚠️ **This contract contains significant risks that require careful review.**\n\n"
    elif level == "Medium":
        summary += "⚡ **This contract has some areas of concern that should be addressed.**\n\n"
    else:
        summary += "✅ **This contract appears relatively low-risk, but review is still recommended.**\n\n"
    
    summary += f"Analyzed {clause_count} clauses:\n"
    summary += f"- 🔴 {high} High Risk\n"
    summary += f"- 🟡 {medium} Medium Risk\n"
    summary += f"- 🟢 {contract_risk['low_risk_count']} Low Risk\n"
    
    if contract_risk['top_concerns']:
        summary += "\n**Top Concerns:**\n"
        for concern in contract_risk['top_concerns'][:3]:
            cat_name = concern['category'].replace('_', ' ').title()
            summary += f"- {cat_name}: {concern['average_score']}/100 avg score\n"
    
    return summary


def identify_critical_clauses(clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Identify the most critical clauses that need attention.
    
    Args:
        clauses: List of analyzed clauses
        
    Returns:
        Sorted list of critical clauses
    """
    critical = []
    
    for clause in clauses:
        if clause.get('risk_level') in ['High', 'Medium']:
            critical.append({
                'id': clause.get('id'),
                'title': clause.get('title', 'Unknown'),
                'risk_level': clause.get('risk_level'),
                'risk_score': clause.get('risk_score', 0),
                'risk_category': clause.get('risk_category', 'general'),
                'concerns': clause.get('concerns', []),
                'has_alternative': bool(clause.get('suggested_alternative'))
            })
    
    # Sort by risk score descending
    critical.sort(key=lambda x: x['risk_score'], reverse=True)
    
    return critical
