import re
import json
import time
import urllib.request
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.views.decorators.http import require_POST
from .models import Room, Participant, Message

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


def extract_direct_stream(video_url):
    if not video_url:
        return ''
    lower_url = video_url.lower()
    if any(host in lower_url for host in ('vk.com', 'vkvideo.ru', 'rutube.ru')):
        return ''
    if lower_url.endswith(('.mp4', '.webm', '.ogg')) or '.m3u8' in lower_url:
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
            if info and info.get('url'):
                return info['url']
    except Exception:
        pass
    return ''


def fetch_video_thumbnail(video_url):
    if not video_url:
        return ''
    try:
        if 'youtube.com' in video_url or 'youtu.be' in video_url:
            match = re.search(r'(?:v=|youtu\.be/|shorts/|embed/)([a-zA-Z0-9_-]{11})', video_url)
            if match:
                return f"https://img.youtube.com/vi/{match.group(1)}/hqdefault.jpg"
        request = urllib.request.Request(video_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=5) as response:
            html = response.read(500000).decode('utf-8', errors='ignore')
            match = re.search(
                r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                html, re.IGNORECASE
            )
            if not match:
                match = re.search(
                    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:image["\']',
                    html, re.IGNORECASE
                )
            if match:
                return match.group(1).replace('&amp;', '&')
    except Exception:
        pass
    return ''


def _profile_age(user):
    try:
        return user.profile.age
    except Exception:
        return None


def _can_enter_room(user, room):
    if room.is_18_plus:
        age = _profile_age(user)
        return age is not None and age >= 18
    return True


def index(request):
    query = request.GET.get('q', '').strip()
    age_filter = request.GET.get('age', 'all')
    content_filter = request.GET.get('content', 'all')

    rooms = Room.objects.filter(is_private=False).select_related('host').order_by('-created_at')
    for room in rooms:
        room.cleanup_stale_participants()
        room.save(update_fields=['voice_state', 'webrtc_signals'])

    if query:
        rooms = rooms.filter(name__icontains=query)
    if age_filter == '18':
        rooms = rooms.filter(is_18_plus=True)
    if content_filter != 'all':
        valid_types = {item[0] for item in Room.CONTENT_CHOICES}
        if content_filter in valid_types:
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
    for room in rooms:
        room.cleanup_stale_participants()
        room.save(update_fields=['voice_state', 'webrtc_signals'])
        data[str(room.uuid)] = {
            'count': room.participants.count(),
            'max': room.max_participants
        }
    return JsonResponse({'rooms': data})


def all_rooms(request):
    return redirect('index')


@login_required
@require_POST
def create_room(request):
    name = request.POST.get('room_name', '').strip()
    if not name:
        return redirect('index')

    try:
        max_participants = int(request.POST.get('max_participants', 10) or 10)
    except (TypeError, ValueError):
        max_participants = 10

    content_type = request.POST.get('content_type', 'movie')
    valid_types = {item[0] for item in Room.CONTENT_CHOICES}
    if content_type not in valid_types:
        content_type = 'movie'

    is_18_plus = request.POST.get('is_18_plus') == 'on'
    if is_18_plus:
        age = _profile_age(request.user)
        if age is None or age < 18:
            return redirect('index')

    room = Room.objects.create(
        name=name[:100],
        host=request.user,
        description=request.POST.get('description', '').strip(),
        video_url=request.POST.get('video_url', '').strip(),
        max_participants=max(1, min(max_participants, 100)),
        is_18_plus=is_18_plus,
        is_private=request.POST.get('is_private') == 'on',
        content_type=content_type,
    )
    room.thumbnail_url = fetch_video_thumbnail(room.video_url)
    room.save(update_fields=['thumbnail_url'])
    Participant.objects.get_or_create(room=room, user=request.user)
    return redirect('room_detail', room_uuid=room.uuid)


@login_required
@require_POST
def join_room(request):
    query = request.POST.get('query', '').strip()
    if not query:
        return redirect('index')

    room = Room.objects.filter(access_code__iexact=query).first()
    if room is None:
        room = Room.objects.filter(uuid=query).first()
    if room is None:
        room = Room.objects.filter(name__icontains=query, is_private=False).first()

    if room:
        return redirect('room_detail', room_uuid=room.uuid)
    return redirect('index')


@login_required
def room_detail(request, room_uuid):
    room = get_object_or_404(Room, uuid=room_uuid)
    if room.banned_users.filter(id=request.user.id).exists():
        return redirect('index')
    if not _can_enter_room(request.user, room):
        return redirect('index')

    room.cleanup_stale_participants()
    room.save(update_fields=['voice_state', 'webrtc_signals'])

    with transaction.atomic():
        room = Room.objects.select_for_update().get(uuid=room_uuid)
        existing = Participant.objects.filter(room=room, user=request.user).first()
        if not existing and room.participants.count() >= room.max_participants:
            return redirect('index')
        Participant.objects.update_or_create(
            room=room, user=request.user,
            defaults={'last_seen': timezone.now()}
        )

    direct_stream_url = extract_direct_stream(room.video_url)
    return render(request, 'room.html', {
        'room': room,
        'is_host': room.host_id == request.user.id,
        'direct_stream_url': direct_stream_url,
        'participants': room.participants.select_related('user', 'user__profile').all(),
        'messages': room.messages.all().order_by('-created_at')[:100][::-1],
    })


@login_required
@require_POST
def delete_room(request, room_uuid):
    room = get_object_or_404(Room, uuid=room_uuid)
    if room.host_id == request.user.id or request.user.is_staff or request.user.is_superuser:
        room.delete()
    return redirect('index')


@login_required
@require_POST
def kick_user(request, room_uuid, user_id):
    room = get_object_or_404(Room, uuid=room_uuid)
    if room.host_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
        return redirect('room_detail', room_uuid=room.uuid)

    target = get_object_or_404(User, id=user_id)
    if target.id != room.host_id:
        room.banned_users.add(target)
        Participant.objects.filter(room=room, user=target).delete()
        voice_state = dict(room.voice_state or {})
        voice_state.pop(str(target.id), None)
        room.voice_state = voice_state
        room.save(update_fields=['voice_state'])
    return redirect('room_detail', room_uuid=room.uuid)


@login_required
@require_POST
def leave_room(request, room_uuid):
    room = Room.objects.filter(uuid=room_uuid).first()
    if room:
        if room.host_id == request.user.id:
            room.delete()
        else:
            Participant.objects.filter(room=room, user=request.user).delete()
            voice_state = dict(room.voice_state or {})
            voice_state.pop(str(request.user.id), None)
            room.voice_state = voice_state
            room.save(update_fields=['voice_state'])
    return redirect('index')


@login_required
def room_sync_api(request, room_uuid):
    if request.method not in ('GET', 'POST'):
        return JsonResponse({'status': 'method_not_allowed'}, status=405)

    with transaction.atomic():
        room = Room.objects.select_for_update().filter(uuid=room_uuid).first()
        if not room:
            return JsonResponse({'status': 'closed', 'redirect': '/'}, status=404)
        if room.banned_users.filter(id=request.user.id).exists() or not _can_enter_room(request.user, room):
            return JsonResponse({'status': 'banned', 'redirect': '/'}, status=403)

        now_ts = time.time()
        uid = str(request.user.id)
        is_host = room.host_id == request.user.id

        room.cleanup_stale_participants()
        participant, created = Participant.objects.get_or_create(
            room=room, user=request.user,
            defaults={'last_seen': timezone.now()}
        )
        participant.last_seen = timezone.now()
        participant.save(update_fields=['last_seen'])

        if request.method == 'POST':
            try:
                payload = json.loads(request.body.decode('utf-8') or '{}')
                if not isinstance(payload, dict):
                    raise ValueError
            except (ValueError, UnicodeDecodeError):
                return JsonResponse({'status': 'invalid_json'}, status=400)
        else:
            payload = {}

        if is_host and isinstance(payload.get('video'), dict):
            video = payload['video']
            try:
                room.current_time = max(0.0, min(float(video.get('current_time', room.current_time)), 86400.0))
            except (TypeError, ValueError):
                pass
            room.is_playing = bool(video.get('is_playing', room.is_playing))

        chat_text = payload.get('chat_message', '')
        if isinstance(chat_text, str):
            chat_text = chat_text.strip()[:1000]
            if chat_text:
                Message.objects.create(room=room, user=request.user.username, text=chat_text)

        voice_action = payload.get('voice_action')
        voice_state = {
            key: value for key, value in (room.voice_state or {}).items()
            if now_ts - float(value.get('updated_at', 0)) < 12
        }
        if voice_action == 'join':
            voice_state[uid] = {
                'username': request.user.username,
                'muted': bool(payload.get('muted', False)),
                'updated_at': now_ts
            }
        elif voice_action == 'leave':
            voice_state.pop(uid, None)
        elif uid in voice_state:
            voice_state[uid]['updated_at'] = now_ts
            if 'muted' in payload:
                voice_state[uid]['muted'] = bool(payload['muted'])
        room.voice_state = voice_state

        signals = [
            signal for signal in (room.webrtc_signals or [])
            if now_ts - float(signal.get('ts', 0)) < 15
        ]
        incoming_signals = payload.get('signals') or []
        if isinstance(incoming_signals, list):
            for signal in incoming_signals[:30]:
                if not isinstance(signal, dict):
                    continue
                target_id = str(signal.get('to', ''))
                signal_type = signal.get('type')
                data = signal.get('data')
                if (target_id.isdigit() and target_id != uid
                        and signal_type in ('offer', 'answer', 'candidate')
                        and isinstance(data, dict)):
                    signals.append({
                        'from': uid, 'to': target_id,
                        'type': signal_type, 'data': data, 'ts': now_ts
                    })

        my_signals = [signal for signal in signals if signal.get('to') == uid]
        room.webrtc_signals = [signal for signal in signals if signal.get('to') != uid]

        room.save(update_fields=[
            'is_playing', 'current_time', 'voice_state', 'webrtc_signals'
        ])

        try:
            last_id = max(0, int(request.GET.get('last_msg_id') or payload.get('last_msg_id') or 0))
        except (TypeError, ValueError):
            last_id = 0

        messages = [
            {'id': message.id, 'user': message.user, 'text': message.text}
            for message in room.messages.filter(id__gt=last_id).order_by('id')[:50]
        ]
        participants = []
        for item in room.participants.select_related('user', 'user__profile').all():
            if not item.user_id:
                continue
            profile = getattr(item.user, 'profile', None)
            avatar_url = profile.avatar.url if profile and profile.avatar else ''
            participants.append({
                'id': item.user_id,
                'username': item.user.username,
                'is_host': item.user_id == room.host_id,
                'avatar_url': avatar_url
            })

        return JsonResponse({
            'status': 'ok',
            'video': {
                'is_playing': room.is_playing,
                'current_time': room.current_time
            },
            'viewers_count': len(participants),
            'participants': participants,
            'voice_state': voice_state,
            'signals': my_signals,
            'messages': messages,
            'last_msg_id': messages[-1]['id'] if messages else last_id
        })


@login_required
@require_POST
def livekit_token(request, room_uuid):
    """Выдаёт краткоживущий токен только участнику текущей комнаты."""
    room = get_object_or_404(Room, uuid=room_uuid)
    if room.banned_users.filter(pk=request.user.pk).exists():
        return JsonResponse({'error': 'Доступ к комнате запрещён.'}, status=403)
    if not _can_enter_room(request.user, room):
        return JsonResponse({'error': 'Для этой комнаты доступ ограничен.'}, status=403)
    if not Participant.objects.filter(room=room, user=request.user).exists():
        return JsonResponse({'error': 'Сначала войдите в комнату.'}, status=403)

    livekit_url = getattr(settings, 'LIVEKIT_URL', '')
    api_key = getattr(settings, 'LIVEKIT_API_KEY', '')
    api_secret = getattr(settings, 'LIVEKIT_API_SECRET', '')
    if not all((livekit_url, api_key, api_secret)):
        return JsonResponse({'error': 'Голосовой чат не настроен администратором.'}, status=503)
    try:
        from datetime import timedelta
        from livekit import api
        livekit_room = f'zetroom-{room.uuid}'
        token = (api.AccessToken(api_key, api_secret)
            .with_identity(str(request.user.pk))
            .with_name(request.user.username)
            .with_ttl(timedelta(hours=2))
            .with_grants(api.VideoGrants(room_join=True, room=livekit_room,
                can_publish=True, can_subscribe=True, can_publish_data=False))
            .to_jwt())
    except ImportError:
        return JsonResponse({'error': 'На сервере не установлен пакет livekit-api.'}, status=503)
    except Exception:
        return JsonResponse({'error': 'Не удалось подготовить подключение к голосовому чату.'}, status=500)
    return JsonResponse({'url': livekit_url, 'token': token, 'room_name': livekit_room})
