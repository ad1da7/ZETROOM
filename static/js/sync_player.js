const roomUuid = JSON.parse(document.getElementById('room-uuid').textContent);

const chatSocket = new WebSocket(
    'ws://' + window.location.host + '/ws/room/' + roomUuid + '/'
);

chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    const chatBox = document.getElementById('chat-box');

    const msg = document.createElement('div');
    msg.style.background = '#2a2a30';
    msg.style.padding = '8px';
    msg.style.borderRadius = '5px';
    msg.style.marginBottom = '8px';
    msg.innerHTML = `<b style="color:#3b82f6;">${data.username}:</b> ${data.message}`;

    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
};

document.getElementById('chat-form').onsubmit = function(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const message = input.value;

    if (message) {
        chatSocket.send(JSON.stringify({
            'message': message,
            'username': 'Гость'
        }));
        input.value = '';
    }
};
