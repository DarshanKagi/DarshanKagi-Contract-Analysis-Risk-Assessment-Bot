# Configuration for Contract Analysis Bot

# DeepSeek API Configuration
DEEPSEEK_API_KEY = "sk-77513614b75f4cd98dee89bfde8c8c63"
DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

# Risk Scoring Weights
RISK_WEIGHTS = {
    "penalty_clause": 0.15,
    "indemnity_clause": 0.15,
    "unilateral_termination": 0.12,
    "arbitration_terms": 0.10,
    "auto_renewal": 0.10,
    "lock_in_period": 0.10,
    "non_compete": 0.10,
    "ip_transfer": 0.10,
    "confidentiality": 0.08
}

# Risk Level Thresholds
RISK_THRESHOLDS = {
    "low": (0, 30),
    "medium": (31, 60),
    "high": (61, 100)
}

# Supported File Types
SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".doc", ".txt"]

# Paths
LOGS_DIR = "logs"
EXPORTS_DIR = "exports"
TEMPLATES_DIR = "templates"
