from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Room, Participant, Message


def index(request):
    query = request.GET.get('q', '').strip()
    rooms = Room.objects.all().order_by('-created_at')

    if query:
        rooms = rooms.filter(name__icontains=query)

    return render(request, 'index.html', {
        'rooms': rooms,
        'query': query
    })


def all_rooms(request):
    return redirect('index')


@login_required
def create_room(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name', '').strip()
        description = request.POST.get('description', '').strip()
        video_url = request.POST.get('video_url', '').strip()

        if not room_name:
            rooms = Room.objects.all().order_by('-created_at')
            return render(request, 'index.html', {
                'rooms': rooms,
                'error': 'ВВЕДИТЕ НАЗВАНИЕ КОМНАТЫ'
            })

        new_room = Room.objects.create(
            name=room_name,
            description=description,
            video_url=video_url,
            host=request.user
        )
        Participant.objects.create(room=new_room, user=request.user)
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
            try:
                room = Room.objects.get(uuid=query)
            except (Room.DoesNotExist, ValidationError, ValueError):
                room = Room.objects.filter(name__icontains=query).first()

        if room:
            return redirect('room_detail', room_uuid=room.uuid)
        else:
            rooms = Room.objects.all().order_by('-created_at')
            return render(request, 'index.html', {
                'rooms': rooms,
                'error': 'КОМНАТА НЕ НАЙДЕНА'
            })
    return redirect('index')


@login_required
def room_detail(request, room_uuid):
    room = get_object_or_404(Room, uuid=room_uuid)
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
