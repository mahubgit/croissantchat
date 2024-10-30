import os
from flask import Flask, render_template, request, jsonify, session
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch
import re
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Configuration du cache des modèles
os.environ['TRANSFORMERS_CACHE'] = Config.MODELS_DIR
os.environ['HF_HOME'] = Config.MODELS_DIR

def get_quantization_config():
    """Configuration pour la quantification 8-bit"""
    return BitsAndBytesConfig(
        load_in_8bit=True,
        bnb_8bit_use_double_quant=True,
        bnb_8bit_quant_type="nf8",
        bnb_8bit_compute_dtype=torch.float16
    )

def save_model_locally():
    """Télécharge et sauvegarde le modèle localement si ce n'est pas déjà fait"""
    local_model_path = os.path.join(Config.MODELS_DIR, 'model_local')
    
    if not os.path.exists(local_model_path):
        print("Premier lancement : Téléchargement et sauvegarde du modèle...")
        tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME, cache_dir=Config.MODELS_DIR)
        
        quantization_config = get_quantization_config()
        model = AutoModelForCausalLM.from_pretrained(
            Config.MODEL_NAME,
            cache_dir=Config.MODELS_DIR,
            quantization_config=quantization_config,
            device_map="auto"  # Gestion automatique de la distribution sur le GPU
        )
        
        tokenizer.save_pretrained(local_model_path)
        model.save_pretrained(local_model_path)
        print(f"Modèle sauvegardé localement dans : {local_model_path}")
    
    return local_model_path

def get_device():
    if Config.DEVICE == 'auto':
        return 'cuda' if torch.cuda.is_available() else 'cpu'
    return Config.DEVICE

# Initialisation du modèle
print("Chargement du modèle...")
local_model_path = save_model_locally()
device = get_device()

try:
    print(f"Chargement du modèle local depuis : {local_model_path}")
    tokenizer = AutoTokenizer.from_pretrained(local_model_path)
    
    quantization_config = get_quantization_config()
    model = AutoModelForCausalLM.from_pretrained(
        local_model_path,
        quantization_config=quantization_config,
        device_map="auto",
        local_files_only=True
    )
    
    print(f"Modèle chargé avec quantification 8-bit")
    
except Exception as e:
    print(f"Erreur lors du chargement du modèle local : {str(e)}")
    raise

def clean_response(response, conversation):
    response = response.replace(conversation, "").strip()
    response = re.sub(r'(Assistant|Humain)\s*:', '', response)
    response = re.sub(r'\s+', ' ', response)
    return response.strip()

def prepare_conversation(message, history):
    """Prépare la conversation en respectant les limites de tokens"""
    conversation = ""
    
    # Calculer combien d'historique on peut inclure
    if history:
        # On commence par le message actuel
        temp_conv = f"Humain : {message}\nAssistant :"
        current_tokens = len(tokenizer.encode(temp_conv))
        
        # On ajoute l'historique en commençant par les messages les plus récents
        for entry in reversed(history):
            entry_text = f"Humain : {entry['user']}\nAssistant : {entry['bot']}\n"
            entry_tokens = len(tokenizer.encode(entry_text))
            
            # Vérifier si l'ajout de cette entrée dépasserait la limite
            if current_tokens + entry_tokens < Config.MAX_INPUT_LENGTH:
                conversation = entry_text + conversation
                current_tokens += entry_tokens
            else:
                break
    
    # Ajouter le message actuel
    conversation += f"Humain : {message}\nAssistant :"
    return conversation

@app.route('/')
def home():
    return render_template('index.html', config=Config)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        message = request.json['message']
        
        # Gestion du contexte
        if Config.MAX_HISTORY_LENGTH > 0:
            if 'history' not in session:
                session['history'] = []
            
            conversation = prepare_conversation(message, session['history'])
        else:
            conversation = f"Humain : {message}\nAssistant :"
        
        inputs = tokenizer(conversation, return_tensors="pt").to(device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=Config.MAX_NEW_TOKENS,  # Utiliser max_new_tokens au lieu de max_length
                min_length=Config.MIN_LENGTH,
                do_sample=True,
                temperature=Config.TEMPERATURE,
                top_p=Config.TOP_P,
                top_k=Config.TOP_K,
                repetition_penalty=Config.REPETITION_PENALTY,
                no_repeat_ngram_size=Config.NO_REPEAT_NGRAM_SIZE,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        cleaned_response = clean_response(response, conversation)
        
        if Config.MAX_HISTORY_LENGTH > 0:
            session['history'].append({
                'user': message,
                'bot': cleaned_response
            })
            if len(session['history']) > Config.MAX_HISTORY_LENGTH:
                session['history'] = session['history'][-Config.MAX_HISTORY_LENGTH:]
        
        return jsonify({'response': cleaned_response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset_conversation():
    if 'history' in session:
        session['history'] = []
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)