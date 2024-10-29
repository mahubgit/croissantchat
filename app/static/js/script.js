function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    
    if (message) {
        displayMessage('user', message);
        input.value = '';
        input.disabled = true;
        
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                displayMessage('bot', 'Erreur: ' + data.error);
            } else {
                displayMessage('bot', data.response);
            }
        })
        .catch(error => {
            displayMessage('bot', 'Erreur de connexion');
            console.error('Erreur:', error);
        })
        .finally(() => {
            input.disabled = false;
            input.focus();
        });
    }
}

function displayMessage(sender, message) {
    const chatMessages = document.getElementById('chat-messages');
    const messageElement = document.createElement('div');
    messageElement.className = `message ${sender}`;
    messageElement.textContent = message;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}