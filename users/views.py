import random
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
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
                'password': form.cleaned_data['password1'],
                'age': form.cleaned_data['age'],
                'code': code
            }
            send_mail(
                'Код подтверждения Zetroom',
                f'Ваш код для завершения регистрации: {code}',
                settings.DEFAULT_FROM_EMAIL,
                [form.cleaned_data['email']],
                fail_silently=False,
            )
            print(f"\n{'='*45}\nКОД ПОДТВЕРЖДЕНИЯ ДЛЯ {form.cleaned_data['email']}: {code}\n{'='*45}\n")
            return redirect('verify_email')
    else:
        form = CustomRegisterForm()
    return render(request, 'register.html', {'form': form})


def verify_email_view(request):
    reg_data = request.session.get('reg_data')
    if not reg_data:
        return redirect('register')

    error = None
    if request.method == 'POST':
        user_code = request.POST.get('code', '').strip()
        if user_code == reg_data['code']:
            user = User.objects.create_user(
                username=reg_data['username'],
                email=reg_data['email'],
                password=reg_data['password']
            )
            user.profile.age = reg_data['age']
            user.profile.is_email_verified = True
            user.profile.save()

            del request.session['reg_data']
            login(request, user)
            return redirect('profile')
        else:
            error = 'НЕВЕРНЫЙ КОД ПОДТВЕРЖДЕНИЯ'

    return render(request, 'verify_email.html', {
        'email': reg_data['email'],
        'error': error
    })


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