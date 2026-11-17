const video = document.getElementById('video-player');
const btnPlay = document.getElementById('btn-play');
const btnPause = document.getElementById('btn-pause');

if (video) {
    btnPlay.onclick = () => {
        video.play();
        chatSocket.send(JSON.stringify({'type': 'video_sync', 'action': 'play', 'time': video.currentTime}));
    };
    
    btnPause.onclick = () => {
        video.pause();
        chatSocket.send(JSON.stringify({'type': 'video_sync', 'action': 'pause', 'time': video.currentTime}));
    };

    if (data.type === 'video_sync') {
        if (data.action === 'play') { video.currentTime = data.time; video.play(); }
        if (data.action === 'pause') { video.currentTime = data.time; video.pause(); }
    }
}
