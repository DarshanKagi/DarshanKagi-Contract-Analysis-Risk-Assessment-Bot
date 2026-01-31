"""
Audit Logger Module
Maintains JSON-based audit trails for contract analyses.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from config import LOGS_DIR


def ensure_logs_dir():
    """Ensure the logs directory exists."""
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)


def get_log_file_path() -> str:
    """Get the path to the audit log file."""
    ensure_logs_dir()
    return os.path.join(LOGS_DIR, "audit_logs.json")


def load_logs() -> List[Dict[str, Any]]:
    """Load existing audit logs."""
    log_file = get_log_file_path()
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_logs(logs: List[Dict[str, Any]]):
    """Save audit logs to file."""
    log_file = get_log_file_path()
    
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)


def log_analysis(
    filename: str,
    contract_type: str,
    risk_score: float,
    clauses_analyzed: int,
    language: str,
    user_actions: Optional[List[str]] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Log a contract analysis event.
    
    Args:
        filename: Name of the analyzed file
        contract_type: Type of contract detected
        risk_score: Overall risk score
        clauses_analyzed: Number of clauses analyzed
        language: Detected language
        user_actions: Optional list of user actions taken
        notes: Optional notes
        
    Returns:
        The created log entry
    """
    logs = load_logs()
    
    entry = {
        'id': len(logs) + 1,
        'timestamp': datetime.now().isoformat(),
        'filename': filename,
        'contract_type': contract_type,
        'risk_score': risk_score,
        'risk_level': 'High' if risk_score > 60 else ('Medium' if risk_score > 30 else 'Low'),
        'clauses_analyzed': clauses_analyzed,
        'language': language,
        'user_actions': user_actions or [],
        'notes': notes or '',
        'exported': False
    }
    
    logs.append(entry)
    save_logs(logs)
    
    return entry


def log_export(analysis_id: int, export_path: str):
    """
    Log that an analysis was exported.
    
    Args:
        analysis_id: ID of the analysis
        export_path: Path where the export was saved
    """
    logs = load_logs()
    
    for log in logs:
        if log.get('id') == analysis_id:
            log['exported'] = True
            log['export_path'] = export_path
            log['export_timestamp'] = datetime.now().isoformat()
            break
    
    save_logs(logs)


def log_user_action(analysis_id: int, action: str):
    """
    Add a user action to an existing log entry.
    
    Args:
        analysis_id: ID of the analysis
        action: Description of the action
    """
    logs = load_logs()
    
    for log in logs:
        if log.get('id') == analysis_id:
            if 'user_actions' not in log:
                log['user_actions'] = []
            log['user_actions'].append({
                'action': action,
                'timestamp': datetime.now().isoformat()
            })
            break
    
    save_logs(logs)


def get_audit_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get recent audit history.
    
    Args:
        limit: Maximum number of entries to return
        
    Returns:
        List of recent audit entries (newest first)
    """
    logs = load_logs()
    return sorted(logs, key=lambda x: x['timestamp'], reverse=True)[:limit]


def get_statistics() -> Dict[str, Any]:
    """
    Get statistics from audit logs.
    
    Returns:
        Dictionary of statistics
    """
    logs = load_logs()
    
    if not logs:
        return {
            'total_analyses': 0,
            'avg_risk_score': 0,
            'by_contract_type': {},
            'by_risk_level': {'High': 0, 'Medium': 0, 'Low': 0},
            'by_language': {}
        }
    
    # Calculate statistics
    total = len(logs)
    avg_risk = sum(l.get('risk_score', 0) for l in logs) / total
    
    by_type = {}
    by_level = {'High': 0, 'Medium': 0, 'Low': 0}
    by_language = {}
    
    for log in logs:
        # By contract type
        ct = log.get('contract_type', 'Unknown')
        by_type[ct] = by_type.get(ct, 0) + 1
        
        # By risk level
        rl = log.get('risk_level', 'Medium')
        by_level[rl] = by_level.get(rl, 0) + 1
        
        # By language
        lang = log.get('language', 'en')
        by_language[lang] = by_language.get(lang, 0) + 1
    
    return {
        'total_analyses': total,
        'avg_risk_score': round(avg_risk, 1),
        'by_contract_type': by_type,
        'by_risk_level': by_level,
        'by_language': by_language
    }


def format_audit_for_display() -> str:
    """
    Format audit logs for display in the UI.
    
    Returns:
        Formatted string for display
    """
    logs = get_audit_history(20)
    
    if not logs:
        return "No analysis history yet."
    
    output = "## Recent Analysis History\n\n"
    output += "| # | Date | File | Type | Risk | Clauses |\n"
    output += "|---|------|------|------|------|--------|\n"
    
    for log in logs:
        timestamp = log.get('timestamp', '')[:10]
        filename = log.get('filename', 'Unknown')[:20]
        contract_type = log.get('contract_type', 'Unknown')[:15]
        risk_level = log.get('risk_level', 'Unknown')
        clauses = log.get('clauses_analyzed', 0)
        
        emoji = '🔴' if risk_level == 'High' else ('🟡' if risk_level == 'Medium' else '🟢')
        
        output += f"| {log.get('id', '')} | {timestamp} | {filename} | {contract_type} | {emoji} {risk_level} | {clauses} |\n"
    
    stats = get_statistics()
    output += f"\n**Total Analyses:** {stats['total_analyses']} | "
    output += f"**Avg Risk Score:** {stats['avg_risk_score']}/100"
    
    return output
