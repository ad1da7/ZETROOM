const roomUuid = JSON.parse(document.getElementById('room-uuid').textContent);
const chatSocket = new WebSocket('ws://' + window.location.host + '/ws/room/' + roomUuid + '/');
const video = document.getElementById('video-player');

chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);

    // Чат
    if (data.message) {
        const chatBox = document.getElementById('chat-box');
        if (chatBox) {
            const msg = document.createElement('div');
            msg.className = 'message-item';
            msg.innerHTML = `<span class="message-author">${data.username}:</span> ${data.message}`;
            chatBox.appendChild(msg);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    }

    // Синхронизация видео
    if (data.type === 'video_sync' && video) {
        if (data.action === 'play') { video.currentTime = data.time; video.play(); }
        else if (data.action === 'pause') { video.currentTime = data.time; video.pause(); }
        else if (data.action === 'seek') { video.currentTime = data.time; }
    }
};

document.getElementById('chat-form').onsubmit = function(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    if (input.value) {
        chatSocket.send(JSON.stringify({'message': input.value, 'username': 'Гость'}));
        input.value = '';
    }
};

if (video) {
    video.addEventListener('play', () => chatSocket.send(JSON.stringify({'type': 'video_sync', 'action': 'play', 'time': video.currentTime})));
    video.addEventListener('pause', () => chatSocket.send(JSON.stringify({'type': 'video_sync', 'action': 'pause', 'time': video.currentTime})));
    video.addEventListener('seeked', () => chatSocket.send(JSON.stringify({'type': 'video_sync', 'action': 'seek', 'time': video.currentTime})));
}
