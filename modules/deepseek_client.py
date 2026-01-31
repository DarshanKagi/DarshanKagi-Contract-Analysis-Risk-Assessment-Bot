"""
DeepSeek API Client Module
Handles all interactions with DeepSeek API for legal reasoning tasks.
"""

import json
import requests
from typing import Dict, List, Any, Optional
import time

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, DEEPSEEK_MODEL


class DeepSeekClient:
    """Client for interacting with DeepSeek API."""
    
    def __init__(self, api_key: str = DEEPSEEK_API_KEY, base_url: str = DEEPSEEK_API_BASE):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, messages: List[Dict], max_tokens: int = 2000, temperature: float = 0.3) -> str:
        """Make a request to DeepSeek API."""
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=self.headers, json=payload, timeout=60)
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise Exception(f"DeepSeek API error: {str(e)}")
    
    def classify_contract_type(self, text: str) -> str:
        """
        Classify the type of contract.
        
        Args:
            text: Contract text (first 3000 chars for efficiency)
            
        Returns:
            Contract type classification
        """
        sample = text[:3000]
        
        messages = [
            {
                "role": "system",
                "content": """You are a legal document classifier. Classify contracts into one of these categories:
                - Employment Agreement
                - Vendor Contract
                - Lease Agreement
                - Partnership Deed
                - Service Contract
                - Non-Disclosure Agreement (NDA)
                - Consulting Agreement
                - License Agreement
                - Sales Contract
                - Other
                
                Respond with ONLY the category name, nothing else."""
            },
            {
                "role": "user",
                "content": f"Classify this contract:\n\n{sample}"
            }
        ]
        
        return self._make_request(messages, max_tokens=50).strip()
    
    def assess_clause_risk(self, clause_text: str, clause_title: str = "") -> Dict[str, Any]:
        """
        Assess the risk level of a specific clause.
        
        Args:
            clause_text: Text of the clause
            clause_title: Optional title of the clause
            
        Returns:
            Risk assessment dictionary
        """
        messages = [
            {
                "role": "system",
                "content": """You are a legal risk analyst specializing in contract review for Indian SMEs.
                
Analyze the given clause and provide:
1. risk_level: "Low", "Medium", or "High"
2. risk_score: A number from 0-100
3. risk_category: One of [penalty_clause, indemnity_clause, unilateral_termination, arbitration_terms, auto_renewal, lock_in_period, non_compete, ip_transfer, confidentiality, payment_terms, liability, general]
4. explanation: Plain language explanation of what this clause means for the business
5. concerns: List of specific concerns or red flags
6. suggested_alternative: A fairer alternative clause text (if risk is Medium or High)

Respond in JSON format ONLY."""
            },
            {
                "role": "user",
                "content": f"Clause Title: {clause_title}\n\nClause Text:\n{clause_text}\n\nAnalyze this clause for risks."
            }
        ]
        
        response = self._make_request(messages, max_tokens=1000)
        
        try:
            # Try to parse JSON from response
            # Handle markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response.strip())
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "risk_level": "Medium",
                "risk_score": 50,
                "risk_category": "general",
                "explanation": response,
                "concerns": [],
                "suggested_alternative": ""
            }
    
    def generate_plain_summary(self, text: str, contract_type: str) -> str:
        """
        Generate a plain language summary of the contract.
        
        Args:
            text: Full contract text
            contract_type: Type of contract
            
        Returns:
            Plain language summary
        """
        # Limit text for API
        sample = text[:8000]
        
        messages = [
            {
                "role": "system",
                "content": """You are a legal advisor helping Indian small business owners understand contracts.
                
Write a clear, plain-language summary that:
1. Explains what this contract is about in simple terms
2. Identifies the main parties involved
3. Highlights key obligations for each party
4. Notes important dates, amounts, and deadlines
5. Points out anything unusual or potentially concerning
6. Uses simple business English that a non-lawyer can understand

Keep the summary concise but comprehensive (300-500 words)."""
            },
            {
                "role": "user",
                "content": f"Contract Type: {contract_type}\n\n{sample}\n\nProvide a plain language summary."
            }
        ]
        
        return self._make_request(messages, max_tokens=800)
    
    def check_compliance(self, text: str) -> List[Dict[str, Any]]:
        """
        Check for potential compliance issues with Indian laws.
        
        Args:
            text: Contract text
            
        Returns:
            List of compliance concerns
        """
        sample = text[:6000]
        
        messages = [
            {
                "role": "system",
                "content": """You are an Indian legal compliance expert. Review contracts for potential issues with:
1. Indian Contract Act, 1872
2. Companies Act, 2013
3. Labour laws (if employment related)
4. Consumer Protection Act
5. Information Technology Act
6. General contract enforceability

Identify potential compliance issues and respond in JSON format:
[
    {
        "issue": "Brief description of the issue",
        "severity": "Low/Medium/High",
        "relevant_law": "Name of relevant law/act",
        "recommendation": "What should be done"
    }
]

If no issues found, return an empty array: []"""
            },
            {
                "role": "user",
                "content": f"Review this contract for compliance issues:\n\n{sample}"
            }
        ]
        
        response = self._make_request(messages, max_tokens=1000)
        
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response.strip())
        except json.JSONDecodeError:
            return []
    
    def suggest_alternative_clause(self, clause_text: str, issue_description: str) -> str:
        """
        Suggest an alternative clause that is more balanced.
        
        Args:
            clause_text: Original clause text
            issue_description: Description of the issue with the clause
            
        Returns:
            Suggested alternative clause
        """
        messages = [
            {
                "role": "system",
                "content": """You are a contract drafting expert helping SMEs negotiate fairer terms.
                
Given a problematic clause, suggest a more balanced alternative that:
1. Protects the interests of both parties
2. Is legally sound under Indian law
3. Is written in clear, professional language
4. Addresses the specific concerns mentioned

Provide ONLY the alternative clause text, ready to use."""
            },
            {
                "role": "user",
                "content": f"Original Clause:\n{clause_text}\n\nIssue:\n{issue_description}\n\nSuggest a fairer alternative."
            }
        ]
        
        return self._make_request(messages, max_tokens=500)
    
    def get_recommendations(self, analysis_results: Dict) -> List[str]:
        """
        Generate actionable recommendations based on contract analysis.
        
        Args:
            analysis_results: Full analysis results dictionary
            
        Returns:
            List of recommendations
        """
        # Create a summary for the API
        summary = f"""
Contract Type: {analysis_results.get('contract_type', 'Unknown')}
Overall Risk Score: {analysis_results.get('overall_risk_score', 0)}/100
High Risk Clauses: {len([c for c in analysis_results.get('clauses', []) if c.get('risk_level') == 'High'])}
Medium Risk Clauses: {len([c for c in analysis_results.get('clauses', []) if c.get('risk_level') == 'Medium'])}
Compliance Issues: {len(analysis_results.get('compliance_issues', []))}
"""
        
        messages = [
            {
                "role": "system",
                "content": """You are a business advisor helping Indian SMEs with contract negotiations.
                
Based on the contract analysis summary, provide 5-7 actionable recommendations:
1. Which clauses need immediate attention
2. What to negotiate before signing
3. Any protective measures to take
4. Red flags that might require legal consultation

Format as a numbered list of clear, actionable items."""
            },
            {
                "role": "user",
                "content": f"Analysis Summary:\n{summary}\n\nProvide recommendations."
            }
        ]
        
        response = self._make_request(messages, max_tokens=600)
        
        # Parse into list
        recommendations = []
        for line in response.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove number prefix
                clean = line.lstrip('0123456789.-) ').strip()
                if clean:
                    recommendations.append(clean)
        
        return recommendations if recommendations else [response]


# Create a singleton instance
deepseek_client = DeepSeekClient()
