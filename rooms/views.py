import re
import json
import time
import urllib.request
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from .models import Room, Participant, Message

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


def extract_direct_stream(video_url):
    if not video_url or not yt_dlp:
        return ''
    if video_url.endswith('.mp4') or video_url.endswith('.m3u8'):
        return video_url

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best[ext=mp4]/best',
        'noplaylist': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if info and 'url' in info:
                return info['url']
    except Exception as e:
        print(f"[STREAM EXTRACT ERROR] {e}")
    return ''


def fetch_video_thumbnail(video_url):
    if not video_url:
        return ''
    try:
        if 'youtube.com' in video_url or 'youtu.be' in video_url:
            yt_match = re.search(r'(?:v=|youtu\.be/|shorts/|embed/)([a-zA-Z0-9_-]{11})', video_url)
            if yt_match:
                yt_id = yt_match.group(1)
                return "https://youtube.com" + f"/vi/{yt_id}/hqdefault.jpg"

        req = urllib.request.Request(
            video_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'ru-RU,ru;q=0.9'
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            og_match = re.search(r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if not og_match:
                og_match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:image["\']', html, re.IGNORECASE)
            if og_match:
                return og_match.group(1).replace('&amp;', '&')
    except Exception:
        pass
    return ''


def index(request):
    query = request.GET.get('q', '').strip()
    age_filter = request.GET.get('age', 'all')

    rooms = Room.objects.filter(is_private=False).order_by('-created_at')

    if query:
        rooms = rooms.filter(name__icontains=query)

    if age_filter == '18':
        rooms = rooms.filter(is_18_plus=True)

    return render(request, 'index.html', {
        'rooms': rooms,
        'query': query,
        'age_filter': age_filter
    })


def all_rooms(request):
    return redirect('index')
@login_required
def create_room(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name', '').strip()
        description = request.POST.get('description', '').strip()
        video_url = request.POST.get('video_url', '').strip()
        is_18_plus = request.POST.get('is_18_plus') == 'on'
        is_private = request.POST.get('is_private') == 'on'

        try:
            max_participants = int(request.POST.get('max_participants', 10))
            if max_participants < 1:
                max_participants = 1
        except ValueError:
            max_participants = 10

        if not room_name:
            rooms = Room.objects.filter(is_private=False).order_by('-created_at')
            return render(request, 'index.html', {
                'rooms': rooms,
                'error': 'ВВЕДИТЕ НАЗВАНИЕ КОМНАТЫ'
            })

        user_age = getattr(request.user.profile, 'age', None)
        if is_18_plus and (not user_age or user_age < 18):
            rooms = Room.objects.filter(is_private=False).order_by('-created_at')
            return render(request, 'index.html', {
                'rooms': rooms,
                'error': 'СОЗДАТЬ КОМНАТЫ 18+ МОГУТ ТОЛЬКО ПОЛЬЗОВАТЕЛИ СТАРШЕ 18 ЛЕТ'
            })

        thumbnail_url = fetch_video_thumbnail(video_url)

        new_room = Room.objects.create(
            name=room_name,
            description=description,
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            host=request.user,
            is_18_plus=is_18_plus,
            is_private=is_private,
            max_participants=max_participants
        )
        Participant.objects.create(room=new_room, user=request.user)

        unlocked = request.session.get('unlocked_rooms', [])
        unlocked.append(str(new_room.uuid))
        request.session['unlocked_rooms'] = unlocked

        return redirect('room_detail', room_uuid=new_room.uuid)
    return redirect('index')


@login_required
def leave_room(request, room_uuid):
    room = get_object_or_404(Room, uuid=room_uuid)
    if room.host == request.user:
        room.delete()
    else:
        Participant.objects.filter(room=room, user=request.user).delete()
    return redirect('index')


@login_required
def delete_room(request, room_uuid):
    room = get_object_or_404(Room, uuid=room_uuid)
    if request.user.is_staff or request.user.is_superuser or room.host == request.user:
        room.delete()
    return redirect('index')


@login_required
def kick_user(request, room_uuid, user_id):
    room = get_object_or_404(Room, uuid=room_uuid)
    if room.host == request.user and user_id != request.user.id:
        target_user = get_object_or_404(User, id=user_id)
        room.banned_users.add(target_user)
        Participant.objects.filter(room=room, user=target_user).delete()
    return redirect('room_detail', room_uuid=room.uuid)
@login_required
def join_room(request):
    if request.method == 'POST':
        query = request.POST.get('query', '').strip()
        room = None

        if query:
            room = Room.objects.filter(access_code__iexact=query).first()
            if not room:
                try:
                    room = Room.objects.get(uuid=query)
                except (Room.DoesNotExist, ValidationError, ValueError):
                    room = Room.objects.filter(name__icontains=query, is_private=False).first()

        if room:
            if room.is_private and room.access_code.upper() == query.upper():
                unlocked = request.session.get('unlocked_rooms', [])
                if str(room.uuid) not in unlocked:
                    unlocked.append(str(room.uuid))
                    request.session['unlocked_rooms'] = unlocked
            return redirect('room_detail', room_uuid=room.uuid)
        else:
            rooms = Room.objects.filter(is_private=False).order_by('-created_at')
            return render(request, 'index.html', {
                'rooms': rooms,
                'error': 'КОМНАТА НЕ НАЙДЕНА ИЛИ НЕВЕРНЫЙ КОД'
            })
    return redirect('index')


@login_required
def room_detail(request, room_uuid):
    room = get_object_or_404(Room, uuid=room_uuid)
    rooms_list = Room.objects.filter(is_private=False).order_by('-created_at')

    if room.banned_users.filter(id=request.user.id).exists():
        return render(request, 'index.html', {
            'rooms': rooms_list,
            'error': 'ВЫ БЫЛИ ИСКЛЮЧЕНЫ ИЗ ЭТОЙ КОМНАТЫ СОЗДАТЕЛЕМ. ПОВТОРНЫЙ ВХОД ЗАПРЕЩЕН.'
        })

    unlocked = request.session.get('unlocked_rooms', [])
    if room.is_private and room.host != request.user and str(room.uuid) not in unlocked:
        return render(request, 'index.html', {
            'rooms': rooms_list,
            'error': 'ЭТА КОМНАТА ЧАСТНАЯ. ВОЙДИТЕ ПО СПЕЦИАЛЬНОМУ КОДУ ЧЕРЕЗ КНОПКУ «ПРИСОЕДИНИТЬСЯ».'
        })

    user_age = getattr(request.user.profile, 'age', None)
    if room.is_18_plus and (not user_age or user_age < 18):
        return render(request, 'index.html', {
            'rooms': rooms_list,
            'error': 'ДОСТУП ЗАПРЕЩЕН: ЭТА КОМНАТА ТОЛЬКО ДЛЯ ПОЛЬЗОВАТЕЛЕЙ 18+'
        })

    is_already_in = Participant.objects.filter(room=room, user=request.user).exists()
    if not is_already_in and room.participants.count() >= room.max_participants:
        return render(request, 'index.html', {
            'rooms': rooms_list,
            'error': f'КОМНАТА ПЕРЕПОЛНЕНА (МАКСИМУМ {room.max_participants} ЧЕЛ.)'
        })

    Participant.objects.get_or_create(room=room, user=request.user)

    if request.method == 'POST':
        text = request.POST.get('message_text', '').strip()
        if text:
            Message.objects.create(room=room, user=request.user.username, text=text)
            return redirect('room_detail', room_uuid=room.uuid)

    participants = room.participants.all()
    messages = room.messages.all().order_by('created_at')
    direct_stream_url = extract_direct_stream(room.video_url)

    return render(request, 'room.html', {
        'room': room,
        'participants': participants,
        'messages': messages,
        'direct_stream_url': direct_stream_url
    })


@login_required
def room_sync_api(request, room_uuid):
    room = Room.objects.filter(uuid=room_uuid).first()
    if not room:
        return JsonResponse({'room_deleted': True})

    if room.banned_users.filter(id=request.user.id).exists():
        return JsonResponse({'kicked': True})

    now = time.time()
    voice_users = dict(room.voice_state or {})
    signals = list(room.webrtc_signals or [])

    cleaned_voice = {k: v for k, v in voice_users.items() if now - v.get('ts', 0) < 12}
    cleaned_signals = [s for s in signals if now - s.get('ts', 0) < 15]
    changed = (len(cleaned_voice) != len(voice_users)) or (len(cleaned_signals) != len(signals))

    active_peer = request.GET.get('voice_peer', '').strip()
    if active_peer:
        cleaned_voice[active_peer] = {'username': request.user.username, 'ts': now}
        changed = True

    if request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            body = {}

        action_type = body.get('type')

        if action_type == 'chat':
            text = body.get('message', '').strip()
            if text:
                Message.objects.create(room=room, user=request.user.username, text=text)

        elif action_type == 'video_state' and room.host == request.user:
            room.is_playing = bool(body.get('is_playing', False))
            room.current_time = float(body.get('time', 0))
            changed = True

        elif action_type == 'voice_leave':
            peer_id = body.get('peerId')
            if peer_id in cleaned_voice:
                del cleaned_voice[peer_id]
                changed = True

        elif action_type == 'webrtc_signal':
            cleaned_signals.append({'ts': now, 'data': body.get('signal')})
            changed = True

        if changed:
            room.voice_state = cleaned_voice
            room.webrtc_signals = cleaned_signals
            room.save(update_fields=['is_playing', 'current_time', 'voice_state', 'webrtc_signals'])

        return JsonResponse({'ok': True})

    if changed:
        room.voice_state = cleaned_voice
        room.webrtc_signals = cleaned_signals
        room.save(update_fields=['voice_state', 'webrtc_signals'])

    last_msg_id = int(request.GET.get('last_msg_id', 0))
    new_msgs = list(room.messages.filter(id__gt=last_msg_id).order_by('id').values('id', 'user', 'text'))

    since_ts = float(request.GET.get('since_ts', 0))
    new_signals = [s['data'] for s in cleaned_signals if s['ts'] > since_ts]

    participants_data = [
        {'id': p.user.id, 'username': p.user.username, 'is_host': p.user_id == room.host_id}
        for p in room.participants.select_related('user').all()
    ]

    return JsonResponse({
        'kicked': False,
        'room_deleted': False,
        'server_ts': now,
        'messages': new_msgs,
        'video': {'is_playing': room.is_playing, 'time': room.current_time},
        'voice_users': cleaned_voice,
        'signals': new_signals,
        'participants': participants_data,
        'max_participants': room.max_participants,
    })
