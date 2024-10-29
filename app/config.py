import os

class Config:
    # Paramètres de base
    SECRET_KEY = os.environ.get('SECRET_KEY', 'votre_clé_secrète_par_défaut')
    
    # Paramètres du modèle
    MODEL_NAME = os.environ.get('MODEL_NAME', 'croissantllm/CroissantLLMChat-v0.1')
    MAX_HISTORY_LENGTH = int(os.environ.get('MAX_HISTORY_LENGTH', '5'))  # 0 pour désactiver le contexte
    
    # Paramètres de génération
    MAX_LENGTH = int(os.environ.get('MAX_LENGTH', '512'))
    MIN_LENGTH = int(os.environ.get('MIN_LENGTH', '20'))
    TEMPERATURE = float(os.environ.get('TEMPERATURE', '0.7'))
    TOP_P = float(os.environ.get('TOP_P', '0.9'))
    TOP_K = int(os.environ.get('TOP_K', '50'))
    REPETITION_PENALTY = float(os.environ.get('REPETITION_PENALTY', '1.2'))
    NO_REPEAT_NGRAM_SIZE = int(os.environ.get('NO_REPEAT_NGRAM_SIZE', '3'))
    
    # Paramètres de performance
    USE_FLOAT16 = os.environ.get('USE_FLOAT16', 'true').lower() == 'true'
    DEVICE = os.environ.get('DEVICE', 'auto')  # 'auto', 'cpu', ou 'cuda'
    
    # Paramètres du cache
    MODELS_DIR = os.environ.get('MODELS_DIR', '/chatbot/app/models')