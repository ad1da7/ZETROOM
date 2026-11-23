from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from .models import Room, Participant, Message


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
                'error': 'СОЗДАВАТЬ КОМНАТЫ 18+ МОГУТ ТОЛЬКО ПОЛЬЗОВАТЕЛИ СТАРШЕ 18 ЛЕТ'
            })

        new_room = Room.objects.create(
            name=room_name,
            description=description,
            video_url=video_url,
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
def delete_room(request, room_uuid):
    room = get_object_or_404(Room, uuid=room_uuid)
    if request.user.is_staff or request.user.is_superuser or room.host == request.user:
        room.delete()
    return redirect('index')


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

    return render(request, 'room.html', {
        'room': room,
        'participants': participants,
        'messages': messages
    })