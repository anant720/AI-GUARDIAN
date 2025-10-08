# Guardian Configuration Settings

# Flask Configuration
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = False # Set to False for production

# Detection Configuration
RISK_THRESHOLDS = {
    'SUSPICIOUS': 5,
    'DANGEROUS': 10
}

# Model Configuration
MODEL_CONFIG = {
    'VECTORIZER_PATH': 'src/Guardian/model/vectorizer.joblib',
    'MODEL_PATH': 'src/Guardian/model/model.joblib',
    'DATASET_PATH': 'src/Guardian/model/dataset.csv'
}

# Logging Configuration
LOG_CONFIG = {
    'LOG_FILE': 'guardian_log.csv',
    'LOG_LEVEL': 'INFO',
    'LOG_FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
}

# API Configuration
API_CONFIG = {
    'MAX_MESSAGE_LENGTH': 10000,
    'RATE_LIMIT': '100 per hour',
    'CORS_ORIGINS': ['*']
}

