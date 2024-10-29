import os
from flask import Flask, render_template, request, jsonify, session
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import re
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Configuration du cache des modèles
os.environ['TRANSFORMERS_CACHE'] = Config.MODELS_DIR
os.environ['HF_HOME'] = Config.MODELS_DIR

def save_model_locally():
    """Télécharge et sauvegarde le modèle localement si ce n'est pas déjà fait"""
    local_model_path = os.path.join(Config.MODELS_DIR, 'model_local')
    
    if not os.path.exists(local_model_path):
        print("Premier lancement : Téléchargement et sauvegarde du modèle...")
        tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_NAME, cache_dir=Config.MODELS_DIR)
        model = AutoModelForCausalLM.from_pretrained(
            Config.MODEL_NAME,
            torch_dtype=torch.float16 if Config.USE_FLOAT16 and torch.cuda.is_available() else torch.float32,
            cache_dir=Config.MODELS_DIR
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
    model = AutoModelForCausalLM.from_pretrained(
        local_model_path,
        torch_dtype=torch.float16 if Config.USE_FLOAT16 and torch.cuda.is_available() else torch.float32,
        local_files_only=True
    )
    
    model = model.to(device)
    print(f"Modèle chargé sur {device.upper()}")
    
except Exception as e:
    print(f"Erreur lors du chargement du modèle local : {str(e)}")
    raise

def clean_response(response, conversation):
    response = response.replace(conversation, "").strip()
    response = re.sub(r'(Assistant|Humain)\s*:', '', response)
    response = re.sub(r'\s+', ' ', response)
    return response.strip()

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
            
            conversation = ""
            for entry in session['history'][-Config.MAX_HISTORY_LENGTH:]:
                conversation += f"Humain : {entry['user']}\nAssistant : {entry['bot']}\n"
            conversation += f"Humain : {message}\nAssistant :"
        else:
            conversation = f"Humain : {message}\nAssistant :"
        
        inputs = tokenizer(conversation, return_tensors="pt").to(device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=Config.MAX_LENGTH,
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