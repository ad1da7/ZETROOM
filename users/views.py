import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import IntegrityError, transaction
from django.utils import timezone
from .forms import CustomRegisterForm, ProfileUpdateForm
from .models import Profile, FriendRequest


def register_view(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            code = str(random.randint(100000, 999999))
            request.session['reg_data'] = {
                'username': form.cleaned_data['username'],
                'email': form.cleaned_data['email'],
                'age': form.cleaned_data['age'],
                'password': form.cleaned_data['password1'],
                'code': code,
            }
            request.session.set_expiry(900)

            try:
                send_mail(
                    subject='Код подтверждения | ZetRoom',
                    message=f'Ваш код для завершения регистрации в ZetRoom: {code}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[form.cleaned_data['email']],
                    fail_silently=False,
                )
            except Exception as error:
                print(f"!!! ОШИБКА ОТПРАВКИ ПОЧТЫ: {error}")
                request.session.pop('reg_data', None)
                messages.error(request, 'Не удалось отправить письмо с кодом. Проверьте настройки почты.')
                return render(request, 'register.html', {'form': form})

            return redirect('verify_email')
    else:
        form = CustomRegisterForm()

    return render(request, 'register.html', {'form': form})


def verify_email_view(request):
    reg_data = request.session.get('reg_data')
    if not reg_data:
        return redirect('register')

    if request.method == 'POST':
        user_code = request.POST.get('code', '').strip()
        if user_code == reg_data.get('code'):
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=reg_data['username'],
                        email=reg_data['email'],
                        password=reg_data['password']
                    )
                    profile, _ = Profile.objects.get_or_create(user=user)
                    profile.age = reg_data['age']
                    profile.is_email_verified = True
                    profile.save()
            except IntegrityError:
                messages.error(request, 'Пользователь с таким никнеймом или почтой уже существует. Начните регистрацию заново.')
                request.session.pop('reg_data', None)
                return redirect('register')

            request.session.pop('reg_data', None)
            login(request, user)
            return redirect('profile')
        messages.error(request, 'Неверный код подтверждения')

    return render(request, 'verify_email.html', {'email': reg_data['email']})


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            new_username = form.cleaned_data.get('username')
            if new_username and new_username != request.user.username:
                request.user.username = new_username
                request.user.save(update_fields=['username'])
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile)

    return render(request, 'profile.html', {
        'form': form,
        'profile': profile
    })


def public_profile_view(request, username):
    target_user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=target_user)

    is_friend = False
    outgoing_request = None
    incoming_request = None

    if request.user.is_authenticated and request.user != target_user:
        current_profile, _ = Profile.objects.get_or_create(user=request.user)
        is_friend = current_profile.friends.filter(id=target_user.id).exists()

        if not is_friend:
            outgoing_request = FriendRequest.objects.filter(
                sender=request.user,
                recipient=target_user,
                status=FriendRequest.PENDING
            ).first()
            incoming_request = FriendRequest.objects.filter(
                sender=target_user,
                recipient=request.user,
                status=FriendRequest.PENDING
            ).first()

        if request.method == 'POST':
            action = request.POST.get('action')

            if action == 'send_request' and not is_friend and not outgoing_request:
                if incoming_request:
                    incoming_request.status = FriendRequest.ACCEPTED
                    incoming_request.save(update_fields=['status'])
                    current_profile.friends.add(target_user)
                    profile.friends.add(request.user)
                else:
                    req, created = FriendRequest.objects.get_or_create(
                        sender=request.user,
                        recipient=target_user,
                        defaults={'status': FriendRequest.PENDING}
                    )
                    if not created and req.status != FriendRequest.PENDING:
                        req.status = FriendRequest.PENDING
                        req.created_at = timezone.now()
                        req.save(update_fields=['status', 'created_at'])

            elif action == 'cancel_request' and outgoing_request:
                outgoing_request.delete()

            elif action == 'accept_request' and incoming_request:
                incoming_request.status = FriendRequest.ACCEPTED
                incoming_request.save(update_fields=['status'])
                current_profile.friends.add(target_user)
                profile.friends.add(request.user)

            elif action == 'decline_request' and incoming_request:
                incoming_request.status = FriendRequest.DECLINED
                incoming_request.save(update_fields=['status'])

            elif action == 'remove_friend' and is_friend:
                current_profile.friends.remove(target_user)
                profile.friends.remove(request.user)

            return redirect('public_profile', username=username)

    return render(request, 'public_profile.html', {
        'target_user': target_user,
        'profile': profile,
        'is_friend': is_friend,
        'outgoing_request': outgoing_request,
        'incoming_request': incoming_request,
        'friends_count': profile.friends.count(),
    })
@login_required
@require_POST
def toggle_friend_view(request, username):
    target_user = get_object_or_404(User, username=username)
    if request.user == target_user:
        return JsonResponse({'status': 'error', 'message': 'Нельзя добавить себя в друзья'}, status=400)

    current_profile, _ = Profile.objects.get_or_create(user=request.user)
    target_profile, _ = Profile.objects.get_or_create(user=target_user)

    if current_profile.friends.filter(id=target_user.id).exists():
        current_profile.friends.remove(target_user)
        target_profile.friends.remove(request.user)
        return JsonResponse({'status': 'ok', 'action': 'removed'})

    outgoing = FriendRequest.objects.filter(
        sender=request.user, recipient=target_user, status=FriendRequest.PENDING
    ).first()
    if outgoing:
        outgoing.delete()
        return JsonResponse({'status': 'ok', 'action': 'cancelled'})

    incoming = FriendRequest.objects.filter(
        sender=target_user, recipient=request.user, status=FriendRequest.PENDING
    ).first()
    if incoming:
        incoming.status = FriendRequest.ACCEPTED
        incoming.save(update_fields=['status'])
        current_profile.friends.add(target_user)
        target_profile.friends.add(request.user)
        return JsonResponse({'status': 'ok', 'action': 'accepted'})

    req, created = FriendRequest.objects.get_or_create(
        sender=request.user,
        recipient=target_user,
        defaults={'status': FriendRequest.PENDING}
    )
    if not created and req.status != FriendRequest.PENDING:
        req.status = FriendRequest.PENDING
        req.created_at = timezone.now()
        req.save(update_fields=['status', 'created_at'])

    return JsonResponse({'status': 'ok', 'action': 'requested'})


@login_required
def friends_api_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    friends = profile.friends.select_related('profile').all().order_by('username')

    data = []
    for friend in friends:
        friend_profile = getattr(friend, 'profile', None)
        avatar_url = friend_profile.avatar.url if friend_profile and friend_profile.avatar else ''
        data.append({
            'username': friend.username,
            'avatar_url': avatar_url,
        })

    return JsonResponse(data, safe=False)


@login_required
@require_POST
def friend_request_by_tag_view(request):
    tag = request.POST.get('tag', '').strip()
    if tag and not tag.startswith('@'):
        tag = '@' + tag
    if not tag or len(tag) > 30:
        return JsonResponse({'status': 'error', 'message': 'Введите корректный юзер-тег.'}, status=400)

    target_profile = Profile.objects.select_related('user').filter(tag__iexact=tag).first()
    if not target_profile:
        return JsonResponse({'status': 'error', 'message': 'Пользователь с таким тегом не найден.'}, status=404)
    target = target_profile.user
    if target.pk == request.user.pk:
        return JsonResponse({'status': 'error', 'message': 'Нельзя добавить самого себя.'}, status=400)

    my_profile, _ = Profile.objects.get_or_create(user=request.user)
    if my_profile.friends.filter(pk=target.pk).exists():
        return JsonResponse({'status': 'error', 'message': 'Вы уже друзья.'}, status=409)

    reverse_pending = FriendRequest.objects.filter(
        sender=target, recipient=request.user, status=FriendRequest.PENDING
    ).first()
    if reverse_pending:
        reverse_pending.status = FriendRequest.ACCEPTED
        reverse_pending.save(update_fields=['status'])
        my_profile.friends.add(target)
        target_profile.friends.add(request.user)
        return JsonResponse({'status': 'ok', 'message': 'Заявка принята. Теперь вы друзья.'})

    req, created = FriendRequest.objects.get_or_create(
        sender=request.user, recipient=target,
        defaults={'status': FriendRequest.PENDING}
    )
    if not created and req.status != FriendRequest.PENDING:
        req.status = FriendRequest.PENDING
        req.created_at = timezone.now()
        req.save(update_fields=['status', 'created_at'])
        return JsonResponse({'status': 'ok', 'message': f'Заявка отправлена пользователю {target.username}.'})
    if not created and req.status == FriendRequest.PENDING:
        return JsonResponse({'status': 'ok', 'message': 'Заявка уже отправлена.'})
    return JsonResponse({'status': 'ok', 'message': f'Заявка отправлена пользователю {target.username}.'})


@login_required
def friend_requests_api_view(request):
    incoming = FriendRequest.objects.select_related('sender', 'sender__profile').filter(
        recipient=request.user,
        status=FriendRequest.PENDING
    ).order_by('-created_at')

    data = []
    for req in incoming:
        sender_profile = getattr(req.sender, 'profile', None)
        avatar_url = sender_profile.avatar.url if sender_profile and sender_profile.avatar else ''
        data.append({
            'id': req.id,
            'username': req.sender.username,
            'tag': sender_profile.tag if sender_profile else '',
            'avatar_url': avatar_url,
        })

    return JsonResponse(data, safe=False)


@login_required
@require_POST
def friend_request_response_view(request, request_id):
    friend_req = get_object_or_404(
        FriendRequest,
        id=request_id,
        recipient=request.user,
        status=FriendRequest.PENDING
    )
    decision = request.POST.get('decision') or request.POST.get('action')

    if decision == 'accept':
        friend_req.status = FriendRequest.ACCEPTED
        friend_req.save(update_fields=['status'])
        my_profile, _ = Profile.objects.get_or_create(user=request.user)
        sender_profile, _ = Profile.objects.get_or_create(user=friend_req.sender)
        my_profile.friends.add(friend_req.sender)
        sender_profile.friends.add(request.user)
        return JsonResponse({'status': 'ok', 'action': 'accepted'})

    if decision == 'decline':
        friend_req.status = FriendRequest.DECLINED
        friend_req.save(update_fields=['status'])
        return JsonResponse({'status': 'ok', 'action': 'declined'})

    return JsonResponse({'status': 'error', 'message': 'Некорректное действие.'}, status=400)
