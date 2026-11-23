import random
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from .forms import CustomRegisterForm, ProfileUpdateForm
from .models import Profile


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

            try:
                send_mail(
                    subject='Код подтверждения | ZetRoom',
                    message=f'Ваш код для завершения регистрации в ZetRoom: {code}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[form.cleaned_data['email']],
                    fail_silently=False,
                )
            except Exception as e:
                # Если произошла ошибка при отправке, выводим её в консоль сервера
                print(f"!!! ОШИБКА ОТПРАВКИ ПОЧТЫ: {e}")
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

        if user_code == reg_data['code']:
            user = User.objects.create_user(
                username=reg_data['username'],
                email=reg_data['email'],
                password=reg_data['password']
            )
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.age = reg_data['age']
            profile.save()

            del request.session['reg_data']
            login(request, user)
            return redirect('profile')
        else:
            messages.error(request, 'Неверный код подтверждения')

    return render(request, 'verify_email.html', {'email': reg_data['email']})


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile)

    return render(request, 'profile.html', {
        'form': form,
        'profile': profile
    })