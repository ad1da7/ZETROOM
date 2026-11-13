from django.shortcuts import render, redirect, get_object_or_404
from .models import Room, Participant
from django.contrib.auth.models import User

"""эта функция на срабатывания когда пользователь заходит на главную страницу сайта"""
def index(request):
    return render(request, 'index.html')
"""это функция  на создание новой комнаты и  когда пользователь заполнил форму и нажал кнопку «Создать»"""
def create_room(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        """создаем комнату"""
        new_room = Room.objects.create(name=room_name)
        return redirect('room_detail', room_uuid=new_room.uuid)

    return redirect('index')
# новая функция поиска и входа в комнату
def join_room(request):
    if request.method == 'POST':
        query = request.POST.get('query')  # берем то что ввел пользователь
        room = None
        try:
            # сначала пытаемся найти по коду uuid
            room = Room.objects.get(uuid=query)
        except (Room.DoesNotExist, ValueError):
            # если по коду не нашли или ввели не код а че то др то ищем по названию
            room = Room.objects.filter(name__icontains=query).first()
        if room:
            #если нашли перекидываем в комнату
            return redirect('room_detail', room_uuid=room.uuid)
        else:
            #если не нашли то показываем ошибку на главной
            return render(request, 'index.html', {'error': 'комната не найдена. проверьте название или код.'})


    return redirect('index')

def room_detail(request, room_uuid):
    room = get_object_or_404(Room, uuid=room_uuid)
    """логика входа: добавляем участника если его еще нет
     так как  пока у меня  нет страницы регистрации, мы создадим анонимного гостя"""
    if request.user.is_authenticated:
        current_user = request.user
    else:
        #создаем гостя (или берем первого попавшегося)
        current_user, created = User.objects.get_or_create(username="Guest")
    # добавляем в комнату (get_or_create чтобы не дублировать)
    Participant.objects.get_or_create(room=room, user=current_user)
    #получаем список всех участников этой комнаты
    participants = room.participants.all()
    return render(request, 'room.html', {'room': room, 'participants': participants})