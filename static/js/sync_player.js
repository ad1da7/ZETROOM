document.addEventListener("DOMContentLoaded", () => {
    const roomUuid = JSON.parse(document.getElementById('room-uuid').textContent);
    const currentUsername = JSON.parse(document.getElementById('current-username').textContent);
    const playerContainer = document.getElementById('player-container');
    const rawUrl = playerContainer ? playerContainer.getAttribute('data-video-url').trim() : '';

    let videoElement = null;

    if (playerContainer && rawUrl) {
        let embedUrl = null;

        // 1. YouTube (watch?v=, youtu.be/, embed/, shorts/)
        const ytMatch = rawUrl.match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
        if (ytMatch && ytMatch[1]) {
            embedUrl = `https://youtube.com{ytMatch[1]}?enablejsapi=1`;
        }

        // 2. Rutube
        const rtMatch = rawUrl.match(/rutube\.ru\/video\/([a-zA-Z0-9]+)/);
        if (rtMatch && rtMatch[1]) {
            embedUrl = `https://rutube.ru{rtMatch[1]}`;
        }

        // 3. VK Видео (vk.com и vkvideo.ru)
        const vkMatch = rawUrl.match(/(?:vk\.com|vkvideo\.ru)\/video(-?\d+)_(\d+)/);
        if (vkMatch && vkMatch[1] && vkMatch[2]) {
            embedUrl = `https://vk.com{vkMatch[1]}&id=${vkMatch[2]}&hd=2`;
        }

        if (embedUrl) {
            playerContainer.innerHTML = `<iframe src="${embedUrl}" allow="autoplay; encrypted-media; fullscreen; picture-in-picture" allowfullscreen></iframe>`;
        } else {
            playerContainer.innerHTML = `
                <video id="video-player" controls style="width: 100%; height: 100%;">
                    <source src="${rawUrl}" type="video/mp4">
                    Ваш браузер не поддерживает воспроизведение видео по этой ссылке.
                </video>
            `;
            videoElement = document.getElementById('video-player');
        }
    }

    // Подключение WebSocket для чата и синхронизации
    const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    const chatSocket = new WebSocket(`${wsScheme}://${window.location.host}/ws/room/${roomUuid}/`);
    let isSocketOpen = false;

    chatSocket.onopen = function() { isSocketOpen = true; };
    chatSocket.onclose = function() { isSocketOpen = false; };

    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);

        if (data.message) {
            const chatBox = document.getElementById('chat-box');
            const emptyMsg = document.getElementById('empty-chat-msg');
            if (emptyMsg) emptyMsg.remove();

            if (chatBox) {
                const msg = document.createElement('div');
                msg.className = 'message-item';
                msg.innerHTML = `<span class="message-author">${data.username}:</span> ${data.message}`;
                chatBox.appendChild(msg);
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        }

        if (data.type === 'video_sync' && videoElement) {
            if (Math.abs(videoElement.currentTime - data.time) > 1.5) {
                videoElement.currentTime = data.time;
            }
            if (data.action === 'play' && videoElement.paused) {
                videoElement.play().catch(() => {});
            } else if (data.action === 'pause' && !videoElement.paused) {
                videoElement.pause();
            }
        }
    };

    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');

    if (chatForm && chatInput) {
        chatForm.addEventListener('submit', function(e) {
            const text = chatInput.value.trim();
            if (!text) {
                e.preventDefault();
                return;
            }

            if (isSocketOpen) {
                e.preventDefault();
                chatSocket.send(JSON.stringify({
                    'message': text,
                    'username': currentUsername
                }));
                chatInput.value = '';
            }
        });
    }

    if (videoElement) {
        videoElement.addEventListener('play', () => {
            if (isSocketOpen) chatSocket.send(JSON.stringify({'type': 'video_sync', 'action': 'play', 'time': videoElement.currentTime}));
        });
        videoElement.addEventListener('pause', () => {
            if (isSocketOpen) chatSocket.send(JSON.stringify({'type': 'video_sync', 'action': 'pause', 'time': videoElement.currentTime}));
        });
        videoElement.addEventListener('seeked', () => {
            if (isSocketOpen) chatSocket.send(JSON.stringify({'type': 'video_sync', 'action': 'seek', 'time': videoElement.currentTime}));
        });
    }
});
