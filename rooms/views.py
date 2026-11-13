from django.shortcuts import render, redirect, get_object_or_404
from .models import Room, Participant
from django.contrib.auth.models import User


def index(request):
    # открываем главную страницу
    return render(request, 'index.html')


def create_room(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        # создаем комнату в базе
        new_room = Room.objects.create(name=room_name)
        # перекидываем в созданную комнату
        return redirect('room_detail', room_uuid=new_room.uuid)
    return redirect('index')


def join_room(request):
    if request.method == 'POST':
        query = request.POST.get('query')  # берем то что ввел пользователь
        room = None
        try:
            # сначала ищем по коду (uuid)
            room = Room.objects.get(uuid=query)
        except (Room.DoesNotExist, ValueError):
            # если не нашли по коду ищем по названию
            room = Room.objects.filter(name__icontains=query).first()

        if room:
            # если нашли перекидываем в комнату
            return redirect('room_detail', room_uuid=room.uuid)
        else:
            # если не нашли показываем ошибку на главной
            return render(request, 'index.html', {'error': 'комната не найдена'})
    return redirect('index')


def room_detail(request, room_uuid):
    room = get_object_or_404(Room, uuid=room_uuid)

    # добавляем участника если его еще нет
    if request.user.is_authenticated:
        current_user = request.user
    else:
        # создаем гостя если нет авторизации
        current_user, created = User.objects.get_or_create(username="Guest")

    # записываем гостя в комнату
    Participant.objects.get_or_create(room=room, user=current_user)

    # получаем список всех участников
    participants = room.participants.all()

    return render(request, 'room.html', {'room': room, 'participants': participants})