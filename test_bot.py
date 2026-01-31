"""
Contract Analysis Bot - Test Suite (Enhancement 7)
Tests for all major components and enhancements
"""

import pytest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test data
SAMPLE_CONTRACT_TEXT = """
SERVICE AGREEMENT

This Agreement is made on January 1, 2024 between Acme Corp and Beta Services.

1. Payment Terms
Payment shall be made within 60 days of invoice receipt.

2. Termination
Either party may terminate this agreement unilaterally without cause.

3. Confidentiality
All information shall remain confidential in perpetuity.
"""

class TestIndianLawCompliance:
    """Test Indian law compliance checker."""
    
    def test_payment_days_extraction(self):
        """Test payment days extraction."""
        from main import IndianLawComplianceChecker
        
        days = IndianLawComplianceChecker._extract_payment_days(SAMPLE_CONTRACT_TEXT)
        assert days == 60, f"Expected 60 days, got {days}"
        print("✓ Payment days extraction works")
    
    def test_compliance_check_vendor(self):
        """Test vendor contract compliance."""
        from main import IndianLawComplianceChecker
        
        report = IndianLawComplianceChecker.check_compliance(
            "Vendor Contract",
            [],
            SAMPLE_CONTRACT_TEXT
        )
        
        # Should flag 60-day payment as violation (>45 days)
        assert not report['compliant'], "Should be non-compliant"
        assert len(report['violations']) > 0, "Should have violations"
        print(f"✓ Compliance check found {len(report['violations'])} violations")


class TestOCRProcessor:
    """Test OCR functionality."""
    
    def test_scanned_pdf_detection(self):
        """Test if scanned PDF is detected."""
        from main import OCRProcessor
        
        # Empty text with 5 pages should be detected as scanned
        result = OCRProcessor.is_scanned_pdf("", 5)
        assert result == True, "Should detect as scanned"
        
        # Sufficient text should not be detected as scanned
        result = OCRProcessor.is_scanned_pdf("A" * 1000, 5)
        assert result == False, "Should not detect as scanned"
        print("✓ Scanned PDF detection works")



class TestTemplateMatching:
    """Test template matching."""
    
    def test_template_initialization(self):
        """Test that template matcher initializes."""
        from main import TemplateMatchingEngine
        
        matcher = TemplateMatchingEngine()
        assert matcher.templates is not None
        assert len(matcher.templates) > 0
        print(f"✓ Template matcher loaded {len(matcher.templates)} templates")
    
    def test_keyword_matching(self):
        """Test fallback keyword matching."""
        from main import TemplateMatchingEngine
        
        matcher = TemplateMatchingEngine()
        result = matcher._keyword_match("This clause covers termination procedures.")
        
        assert result is not None
        assert result['category'] == "Termination"
        print("✓ Keyword matching works")


class TestLegalNER:
    """Test enhanced legal NER."""
    
    def test_indian_currency_extraction(self):
        """Test Indian currency pattern extraction."""
        import re
        
        text = "The fee is Rs. 50,000 and additional Rs. 10,000"
        pattern = r'(?:Rs\.?|₹)\s*[\d,]+(?:\.\d{2})?'
        amounts = re.findall(pattern, text)
        
        assert len(amounts) == 2, f"Expected 2 amounts, found {len(amounts)}"
        print(f"✓ Found {len(amounts)} Indian currency amounts")


class TestRiskAnalysis:
    """Test risk analysis."""
    
    def test_risk_scoring(self):
        """Test clause risk scoring."""
        from main import RiskAnalyzer
        
        # High-risk clause
        clause = "You shall indemnify and hold harmless the company from all claims unilaterally."
        score = RiskAnalyzer.calculate_clause_risk_score(clause)
        
        assert score > 50, f"High-risk clause should score >50, got {score}"
        print(f"✓ Risk scoring works (score: {score})")
    
    def test_risk_level(self):
        """Test risk level categorization."""
        from main import RiskAnalyzer
        
        assert RiskAnalyzer.get_risk_level(20) == "Low"
        assert RiskAnalyzer.get_risk_level(50) == "Medium"
        assert RiskAnalyzer.get_risk_level(80) == "High"
        print("✓ Risk level categorization works")


class TestContractTypes:
    """Test contract classification."""
    
    def test_standard_types(self):
        """Test that standard contract types are recognized."""
        expected_types = [
            "Employment Agreement",
            "Vendor Contract",
            "Lease Agreement",
            "Service Contract"
        ]
        
        # These should be in INDIAN_COMPLIANCE_RULES
        from main import INDIAN_COMPLIANCE_RULES
        
        for ctype in expected_types:
            assert ctype in INDIAN_COMPLIANCE_RULES, f"{ctype} not in compliance rules"
        
        print(f"✓ All {len(expected_types)} standard contract types defined")


def run_all_tests():
    """Run all tests manually."""
    print("\n" + "="*60)
    print("CONTRACT ANALYSIS BOT - TEST SUITE")
    print("="*60 + "\n")
    
    test_classes = [
        TestIndianLawCompliance(),
        TestOCRProcessor(),
        TestTemplateMatching(),
        TestLegalNER(),
        TestRiskAnalysis(),
        TestContractTypes()
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n📋 Running {class_name}...")
        print("-" * 60)
        
        # Get all test methods
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_class, method_name)
                method()
                passed_tests += 1
            except AssertionError as e:
                print(f"❌ {method_name} FAILED: {e}")
            except Exception as e:
                print(f"❌ {method_name} ERROR: {e}")
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed_tests}/{total_tests} tests passed")
    print("="*60 + "\n")
    
    if passed_tests == total_tests:
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"⚠️ {total_tests - passed_tests} test(s) failed")
        return 1


if __name__ == "__main__":
    # Can run with pytest or manually
    if len(sys.argv) > 1 and sys.argv[1] == "pytest":
        pytest.main([__file__, "-v"])
    else:
        exit(run_all_tests())
