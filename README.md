# Contract Analysis & Risk Assessment Bot

A sophisticated GenAI-powered legal assistant that helps small and medium business owners understand complex contracts, identify potential legal risks, and receive actionable advice in plain language.

## Features

### 🆕 Latest Enhancements (Version 2.0)

1. **OCR Support (✓)**: Automatically detects and processes scanned PDFs using Tesseract OCR
2. **Indian Law Compliance (✓)**: Checks contracts against EPF Act, ESI Act, MSME Act, and Registration Act
3. **Multilingual Hindi Output (✓)**: Generate summaries and explanations in Hindi
4. **Enhanced Legal NER (✓)**: Improved party and entity extraction with legal-specific patterns
5. **Template Matching (✓)**: Compare clauses against standard templates using semantic similarity
6. **Contract Templates (✓)**: Built-in library of SME-friendly contract templates
7. **Testing Framework (✓)**: Comprehensive test suite for validation

### Core Features

- **Contract Analysis**: Parse and analyze contracts from PDF (including scanned), DOCX, and TXT formats
- **Risk Assessment**: Identify and score risks at clause and contract levels
- **NLP Tasks**: Extract entities, classify clauses, detect obligations/rights/prohibitions
- **Multilingual Support**: Handle English and Hindi contracts with bilingual output
- **Indian Law Compliance**: Automatic checking of statutory requirements
- **Template Matching**: Semantic comparison with standard clause templates  
- **Report Generation**: Create professional PDF reports with findings and recommendations
- **Interactive UI**: User-friendly Gradio interface for non-technical users

## Key Capabilities

### Core Legal NLP Tasks
- Contract type classification
- Clause and sub-clause extraction
- Enhanced Named Entity Recognition (parties, dates, amounts, jurisdictions)
- Legal entity extraction with contract-specific patterns
- Obligation vs. Right vs. Prohibition identification
- Risk and compliance detection
- Ambiguity detection and flagging

### Risk Assessment
- Clause-level risk scores (Low/Medium/High)
- Contract-level composite risk score
- Template deviation analysis
- Identification of specific risky clauses:
  - Penalty clauses
  - Indemnity clauses
  - Unilateral termination rights
  - Arbitration & jurisdiction terms
  - Auto-renewal & lock-in periods
  - Non-compete & IP transfer clauses

### Indian Law Compliance Checking
- **Employment Agreements**: EPF, ESI, Gratuity, Notice Period, Leave requirements
- **Vendor Contracts**: MSME 45-day payment rule enforcement
- **Lease Agreements**: Registration requirements for leases > 11 months
- **Service Contracts**: GST and statutory compliance checks
- Automatic detection of missing mandatory clauses
- Violation flagging and remediation recommendations


### User-Facing Outputs
- Simplified contract summary
- Clause-by-clause plain-language explanation
- Unfavorable clause highlighting
- Suggested renegotiation alternatives
- Professional PDF reports
- JSON audit logs

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup Instructions

1. **Navigate to project directory**:
   ```bash
   cd contract-analysis-bot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Download spaCy language model**:
   ```bash
   python -m spacy download en_core_web_sm
   ```

## Usage

### Running the Application

```bash
python main.py
```

The application will launch a Gradio web interface at `http://127.0.0.1:7860`

### Using the Interface

1. **Upload Contract**: Click "Upload Contract" and select your PDF, DOCX, or TXT file
2. **Analyze**: Click "🔍 Analyze Contract" button
3. **Review Results**: Navigate through the tabs:
   - **Summary**: Overview, key parties, dates, and financial terms
   - **Risk Assessment**: Overall risk level and distribution
   - **Detailed Analysis**: Clause-by-clause breakdown with explanations
   - **Recommendations**: Actionable advice for each risky clause
4. **Export**: Download the PDF report for legal consultation

### Sample Contracts

The `sample_contracts/` directory contains example contracts for testing:
- `employment_agreement.txt` - Employment contract with various risk clauses
- `vendor_contract.txt` - Vendor service agreement with one-sided terms
- `lease_agreement.txt` - Commercial lease with multiple high-risk clauses
- `service_contract.txt` - Service contract with moderate risk levels

## Technical Architecture

### Components

1. **GeminiAnalyzer**: Handles all Gemini API interactions with retry logic
2. **DocumentParser**: Parses PDF, DOCX, and TXT files
3. **NLPProcessor**: Extracts clauses and entities using spaCy
4. **RiskAnalyzer**: Calculates risk scores and identifies risky clause types
5. **ReportGenerator**: Creates professional PDF reports
6. **AuditLogger**: Maintains JSON logs of all analyses
7. **ContractAnalysisEngine**: Orchestrates the complete analysis pipeline

### Risk Scoring Algorithm

**Clause-Level Scoring**:
- Keywords are weighted based on risk severity
- Vague language and complexity add additional risk
- Scores range from 0-100

**Risk Levels**:
- Low: 0-30
- Medium: 31-60
- High: 61+

**Contract-Level Score**:
- Average of all clause scores
- Weighted by clause importance

## API Configuration

The application uses the Gemini API for natural language understanding and legal reasoning. The API key is already configured in `main.py`:

```python
GEMINI_API_KEY = "Your API Key"
```

## Output Files

### Audit Logs
- Location: `audit_logs/`
- Format: JSON
- Contains: Timestamp, contract metadata, risk summary, key findings, recommendations

### PDF Reports
- Location: `reports/`
- Format: Professional PDF with tables and color-coded risk indicators
- Sections: Metadata, risk summary, executive summary, key findings, recommendations, detailed clause analysis

## Multilingual Support

The bot supports both English and Hindi contracts:

1. **Language Detection**: Automatically detects contract language
2. **Translation**: Hindi contracts are translated to English for processing
3. **Output**: All summaries and explanations are provided in simple English

## Limitations & Disclaimers

⚠️ **Important**: This tool provides guidance, not legal advice. Always consult with a qualified legal professional before making legal decisions based on contract terms.

### Current Limitations
- Analysis limited to first 20 clauses for performance
- OCR for scanned PDFs requires external processing
- No integration with Indian legal databases
- AI analysis may occasionally misinterpret legal language

## Performance Metrics

- **Analysis Time**: 30-120 seconds per contract
- **API Cost**: ~₹0.01-0.05 per contract
- **Storage**: ~10KB per audit log, 100-500KB per PDF report

## Troubleshooting

### Common Issues

**Issue**: "Could not extract text from document"
- **Solution**: Ensure the PDF is text-based, not scanned. Use OCR tools if needed.

**Issue**: SpaCy model not found
- **Solution**: Run `python -m spacy download en_core_web_sm`

**Issue**: Gemini API errors
- **Solution**: Check internet connection. The tool includes automatic retry logic.

**Issue**: Port 7860 already in use
- **Solution**: Modify the `server_port` parameter in `main.py`

## Future Enhancements

- OCR integration for scanned PDFs
- Comparison mode for multiple contract versions
- Template library with SME-friendly contracts
- Batch processing for multiple contracts
- Email notifications for contract renewals
- Mobile application

## License

This project is for educational and informational purposes only.

## Support

For issues or questions, please refer to the implementation plan and code documentation.

---

**Developed using**: Gemini API, Gradio, spaCy, ReportLab  
**Version**: 1.0.0  
**Last Updated**: January 2026
