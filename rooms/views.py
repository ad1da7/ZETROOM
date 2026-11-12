from django.shortcuts import render, redirect, get_object_or_404
from .models import Room, Participant
from django.contrib.auth.models import User


def index(request):
    return render(request, 'index.html')


def create_room(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        # Создаем комнату
        new_room = Room.objects.create(name=room_name)
        return redirect('room_detail', room_uuid=new_room.uuid)
    return redirect('index')


def room_detail(request, room_uuid):
    room = get_object_or_404(Room, uuid=room_uuid)

    # ЛОГИКА ВХОДА: Добавляем участника     если его еще нет
    # Так как у нас нет страницы регистрации , мы создадим анонимного   гостя
    if request.user.is_authenticated:
        current_user = request.user
    else:
        # Создаем гостя (или берем первого попавшегося)
        current_user, created = User.objects.get_or_create(username="Guest")

    # добавляем в комнату (get_or_create чтобы не дублировать)
    Participant.objects.get_or_create(room=room, user=current_user)

    #получаем список всех участников этой комнаты
    participants = room.participants.all()

    return render(request, 'room.html', {'room': room, 'participants': participants})