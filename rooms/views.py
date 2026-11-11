from django.shortcuts import render, redirect, get_object_or_404
from .models import Room

def index(request):
    return render(request, 'index.html')

def create_room(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        new_room = Room.objects.create(name=room_name)
        return redirect('room_detail', room_uuid=new_room.uuid)
    return redirect('index')

def room_detail(request, room_uuid):
    room = get_object_or_404(Room, uuid=room_uuid)
    return render(request, 'room.html', {'room': room})