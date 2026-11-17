from django.shortcuts import render, redirect, get_object_or_404
from .models import Room, Participant, Message
from django.contrib.auth.models import User

def index(request):
    # открываем главную страницу
    return render(request, 'index.html')

def create_room(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name')

        # получаем текущего пользователя (или создаем гостя)
        if request.user.is_authenticated:
            current_user = request.user
        else:
            current_user, created = User.objects.get_or_create(username="Guest")

        # создаем комнату и назначаем хозяином
        new_room = Room.objects.create(name=room_name, host=current_user)

        # сразу добавляем создателя в участники
        Participant.objects.create(room=new_room, user=current_user)

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

def join_room(request):
    if request.method == 'POST':
        query = request.POST.get('query')
        room = None
        try:
            room = Room.objects.get(uuid=query)
        except (Room.DoesNotExist, ValueError):
            room = Room.objects.filter(name__icontains=query).first()

        if room:
            return redirect('room_detail', room_uuid=room.uuid)
        else:
            return render(request, 'index.html', {'error': 'комната не найдена'})
    return redirect('index')


def room_detail(request, room_uuid):
    room = get_object_or_404(Room, uuid=room_uuid)

    if request.user.is_authenticated:
        current_user = request.user
    else:
        current_user, created = User.objects.get_or_create(username="Guest")

    Participant.objects.get_or_create(room=room, user=current_user)

    if request.method == 'POST':
        text = request.POST.get('message_text')
        if text:
            Message.objects.create(room=room, user=current_user.username, text=text)
            return redirect('room_detail', room_uuid=room.uuid)

    participants = room.participants.all()
    messages = room.messages.all().order_by('created_at')

    return render(request, 'room.html', {
        'room': room,
        'participants': participants,
        'messages': messages
    })