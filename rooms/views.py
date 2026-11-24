import re
import json
import time
import urllib.request
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from .models import Room, Participant, Message

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


def extract_direct_stream(video_url):
    if not video_url:
        return ''
    lower_url = video_url.lower()
    if 'vk.com' in lower_url or 'vkvideo.ru' in lower_url or 'rutube.ru' in lower_url:
        return ''
    if lower_url.endswith('.mp4') or '.m3u8' in lower_url:
        return video_url
    if not yt_dlp:
        return ''

    ydl_opts = {
        'quiet': True, 'no_warnings': True, 'format': 'best[ext=mp4]/best',
        'noplaylist': True, 'socket_timeout': 8,
        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if info and 'url' in info:
                return info['url']
    except Exception:
        pass
    return ''


def fetch_video_thumbnail(video_url):
    if not video_url:
        return ''
    try:
        if 'youtube.com' in video_url or 'youtu.be' in video_url:
            yt_match = re.search(r'(?:v=|youtu\.be/|shorts/|embed/)([a-zA-Z0-9_-]{11})', video_url)
            if yt_match:
                return f"https://youtube.com{yt_match.group(1)}/hqdefault.jpg"
        req = urllib.request.Request(video_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            og_match = re.search(r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                                 html, re.IGNORECASE)
            if not og_match:
                og_match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:image["\']',
                                     html, re.IGNORECASE)
            if og_match:
                return og_match.group(1).replace('&amp;', '&')
    except Exception:
        pass
    return ''


def index(request):
    query = request.GET.get('q', '').strip()
    age_filter = request.GET.get('age', 'all')
    content_filter = request.GET.get('content', 'all')

    rooms = Room.objects.filter(is_private=False).order_by('-created_at')
    for r in rooms:
        r.cleanup_stale_participants()

    if query:
        rooms = rooms.filter(name__icontains=query)
    if age_filter == '18':
        rooms = rooms.filter(is_18_plus=True)
    if content_filter != 'all':
        rooms = rooms.filter(content_type=content_filter)

    return render(request, 'index.html', {
        'rooms': rooms,
        'query': query,
        'age_filter': age_filter,
        'content_filter': content_filter,
    })


def rooms_counts_api(request):
    rooms = Room.objects.filter(is_private=False)
    data = {}
    for r in rooms:
        r.cleanup_stale_participants()
        data[str(r.uuid)] = {'count': r.participants.count(), 'max': r.max_participants}
    return JsonResponse({'rooms': data})


def all_rooms(request): return redirect('index')


@login_required
def create_room(request):
    if request.method == 'POST':
        name = request.POST.get('room_name', '').strip()
        description = request.POST.get('description', '').strip()
        video_url = request.POST.get('video_url', '').strip()
        max_participants = int(request.POST.get('max_participants', 10) or 10)
        is_18_plus = request.POST.get('is_18_plus') == 'on'
        is_private = request.POST.get('is_private') == 'on'

        content_type = request.POST.get('content_type', 'movie')

        if not name: return redirect('index')

        room = Room.objects.create(
            name=name, host=request.user, description=description,
            video_url=video_url, thumbnail_url=fetch_video_thumbnail(video_url),
            max_participants=max(1, min(max_participants, 100)),
            is_18_plus=is_18_plus, is_private=is_private,
            content_type=content_type,
        )
        Participant.objects.get_or_create(room=room, user=request.user)
        return redirect('room_detail', room_uuid=room.uuid)
    return redirect('index')


@login_required
def join_room(request):
    if request.method == 'POST':
        q = request.POST.get('query', '').strip()
        if not q: return redirect('index')
        room = Room.objects.filter(access_code__iexact=q).first()
        if not room:
            try:
                room = Room.objects.filter(uuid=q).first()
            except Exception:
                room = None
        if not room:
            room = Room.objects.filter(name__icontains=q, is_private=False).first()
        if room: return redirect('room_detail', room_uuid=room.uuid)
    return redirect('index')


@login_required
def room_detail(request, room_uuid):
    room = get_object_or_404(Room, uuid=room_uuid)
    if room.banned_users.filter(id=request.user.id).exists(): return redirect('index')
    room.cleanup_stale_participants()
    if room.participants.count() >= room.max_participants and not room.participants.filter(user=request.user).exists():
        return redirect('index')

    Participant.objects.update_or_create(room=room, user=request.user, defaults={'last_seen': timezone.now()})
    direct_stream_url = extract_direct_stream(room.video_url)

    return render(request, 'room.html', {
        'room': room,
        'is_host': room.host_id == request.user.id,
        'direct_stream_url': direct_stream_url,
        'participants': room.participants.select_related('user').all(),
        'messages': room.messages.all().order_by('created_at')[:100],
    })


@login_required
def delete_room(request, room_uuid):
    room = get_object_or_404(Room, uuid=room_uuid)
    if room.host == request.user or request.user.is_staff or request.user.is_superuser:
        room.delete()
    return redirect('index')


@login_required
def kick_user(request, room_uuid, user_id):
    room = get_object_or_404(Room, uuid=room_uuid)
    if room.host == request.user or request.user.is_staff or request.user.is_superuser:
        target = get_object_or_404(User, id=user_id)
        if target != room.host:
            room.banned_users.add(target)
            Participant.objects.filter(room=room, user=target).delete()
            vs = dict(room.voice_state or {})
            vs.pop(str(target.id), None)
            room.voice_state = vs
            room.save(update_fields=['voice_state'])
    return redirect('room_detail', room_uuid=room.uuid)


@csrf_exempt
@login_required
def leave_room(request, room_uuid):
    room = Room.objects.filter(uuid=room_uuid).first()
    if room:
        if room.host_id == request.user.id:
            room.delete()
        else:
            Participant.objects.filter(room=room, user=request.user).delete()
            vs = dict(room.voice_state or {})
            if str(request.user.id) in vs:
                vs.pop(str(request.user.id), None)
                room.voice_state = vs
                room.save(update_fields=['voice_state'])
    if request.method == 'POST':
        return JsonResponse({'status': 'left'})
    return redirect('index')


@csrf_exempt
@login_required
def room_sync_api(request, room_uuid):
    with transaction.atomic():
        room = Room.objects.select_for_update().filter(uuid=room_uuid).first()
        if not room:
            return JsonResponse({'status': 'closed', 'redirect': '/'})
        if room.banned_users.filter(id=request.user.id).exists():
            return JsonResponse({'status': 'banned', 'redirect': '/'})

        now_ts = time.time()
        uid_str = str(request.user.id)
        is_host = (room.host_id == request.user.id)

        Participant.objects.update_or_create(room=room, user=request.user, defaults={'last_seen': timezone.now()})
        room.cleanup_stale_participants()

        payload = {}
        if request.method == 'POST':
            try:
                payload = json.loads(request.body.decode('utf-8'))
            except Exception:
                payload = {}

        if is_host and 'video' in payload:
            v = payload['video']
            room.is_playing = bool(v.get('is_playing', room.is_playing))
            room.current_time = float(v.get('current_time', room.current_time))

        chat_text = (payload.get('chat_message') or '').strip()
        if chat_text:
            Message.objects.create(room=room, user=request.user.username, text=chat_text[:1000])

        vs = {k: v for k, v in (room.voice_state or {}).items() if now_ts - v.get('updated_at', 0) < 12}
        v_act = payload.get('voice_action')
        if v_act == 'join':
            vs[uid_str] = {'username': request.user.username, 'muted': bool(payload.get('muted', False)),
                           'updated_at': now_ts}
        elif v_act == 'leave':
            vs.pop(uid_str, None)
        elif uid_str in vs:
            vs[uid_str]['updated_at'] = now_ts
            if 'muted' in payload:
                vs[uid_str]['muted'] = bool(payload['muted'])
        room.voice_state = vs

        sigs = [s for s in (room.webrtc_signals or []) if now_ts - s.get('ts', 0) < 15]
        for s in (payload.get('signals') or []):
            sigs.append(
                {'from': uid_str, 'to': str(s.get('to')), 'type': s.get('type'), 'data': s.get('data'), 'ts': now_ts})
        my_sigs = [s for s in sigs if s.get('to') == uid_str]
        room.webrtc_signals = [s for s in sigs if s.get('to') != uid_str]
        room.save()

        last_id = int(request.GET.get('last_msg_id') or payload.get('last_msg_id') or 0)
        msgs = [{'id': m.id, 'user': m.user, 'text': m.text} for m in room.messages.filter(id__gt=last_id)[:50]]

        new_last_id = msgs[-1]['id'] if msgs else last_id

        parts = [{'id': p.user_id, 'username': p.user.username, 'is_host': p.user_id == room.host_id} for p in
                 room.participants.select_related('user').all() if p.user]

        return JsonResponse({
            'status': 'ok',
            'video': {'is_playing': room.is_playing, 'current_time': room.current_time},
            'viewers_count': len(parts),
            'participants': parts,
            'voice_state': vs,
            'signals': my_sigs,
            'messages': msgs,
            'last_msg_id': new_last_id,
        })