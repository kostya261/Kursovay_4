from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta

import traceback
from django.views.generic import CreateView
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
import uuid
from .models import CustomUser
from .forms import (
    CustomUserCreationForm,
    LoginForm,
    PasswordResetForm,
    PasswordResetConfirmForm
)


class RegisterView(CreateView):
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')

    def form_valid(self, form):
        response = super().form_valid(form)

        # Отправка email для подтверждения
        user = self.object
        confirmation_code = get_random_string(64)
        user.confirmation_code = confirmation_code
        user.save()

        messages.success(
            self.request,
            _('Регистрация успешна! Проверьте email для подтверждения.')
        )
        return response


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            # Используем authenticate, который вернет пользователя с backend
            user = authenticate(request, username=email, password=password)

            if user is not None:
                if user.is_blocked:
                    messages.error(request, 'Ваш аккаунт заблокирован')
                else:
                    login(request, user)
                    messages.success(request, 'Вход выполнен успешно')
                    return redirect('mailer:home')
            else:
                messages.error(request, 'Неверный email или пароль')
    else:
        form = LoginForm()

    return render(request, 'users/login.html', {'form': form})


@login_required
def user_logout(request):
    logout(request)
    messages.success(request, _('Выход выполнен успешно'))
    return redirect('mailer:home')


def password_reset(request):
    """Отправка email для сброса пароля"""
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            try:
                user = CustomUser.objects.get(email=email)

                # Генерируем уникальный токен
                reset_token = str(uuid.uuid4())
                user.reset_token = reset_token
                user.reset_token_created_at = timezone.now()
                user.save()

                # Формируем полный URL
                reset_url = request.build_absolute_uri(
                    f'/users/password-reset-confirm/{reset_token}/'
                )

                # HTML версия письма
                html_message = render_to_string(
                    'users/emails/password_reset_email.html',
                    {
                        'user': user,
                        'reset_url': reset_url,
                    }
                )

                # Текстовая версия
                plain_message = render_to_string(
                    'users/emails/password_reset_email.txt',
                    {
                        'user': user,
                        'reset_url': reset_url,
                    }
                )

                # Отправляем email
                try:
                    send_mail(
                        subject='Сброс пароля - Сервис рассылок',
                        message=plain_message,
                        html_message=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )

                    messages.success(
                        request,
                        'Инструкции по сбросу пароля отправлены на ваш email.'
                    )



                except Exception as e:
                    # Если ошибка отправки, показываем ссылку для отладки
                    if settings.DEBUG:
                        messages.warning(
                            request,
                            f'Ошибка отправки email: {e}<br>'
                            f'Для теста используйте эту ссылку:<br>'
                            f'<a href="{reset_url}">{reset_url}</a>'
                        )
                    else:
                        messages.error(
                            request,
                            'Произошла ошибка при отправке письма. Попробуйте позже.'
                        )
                    print(f"Ошибка отправки email: {e}")

            except CustomUser.DoesNotExist:
                messages.success(
                    request,
                    'Если пользователь с таким email существует, инструкции будут отправлены.'
                )

            return redirect('users:password_reset')

    else:
        form = PasswordResetForm()

    return render(request, 'users/password_reset.html', {'form': form})


def password_reset_confirm(request, token):
    """Подтверждение сброса пароля"""

    user = None

    try:
        user = CustomUser.objects.get(reset_token=token)
        print(f"✅ Пользователь найден: {user.email}")

        # Проверяем срок действия токена (24 часа)
        if user.reset_token_created_at:
            token_age = timezone.now() - user.reset_token_created_at
            print(f"Возраст токена: {token_age}")

            if token_age > timedelta(hours=24):
                print("❌ Токен устарел")
                messages.error(request, 'Ссылка для сброса пароля устарела.')
                user.reset_token = None
                user.reset_token_created_at = None
                user.save()
                return redirect('users:password_reset')
            else:
                print("✅ Токен действителен")
        else:
            print("⚠️ Нет времени создания токена")

    except CustomUser.DoesNotExist:
        print(f"❌ Пользователь с токеном {token} не найден")
        messages.error(request, 'Неверная или устаревшая ссылка.')
        return redirect('users:login')
    except Exception as e:
        print(f"❌ Ошибка при поиске пользователя: {e}")
        messages.error(request, f'Ошибка: {e}')
        return redirect('users:login')

    # Если user is None, значит произошла ошибка и мы уже сделали редирект
    if user is None:
        return redirect('users:login')

    try:
        if request.method == 'POST':
            form = PasswordResetConfirmForm(request.POST)
            if form.is_valid():
                new_password1 = form.cleaned_data['new_password1']
                new_password2 = form.cleaned_data['new_password2']

                if new_password1 != new_password2:
                    messages.error(request, 'Пароли не совпадают.')
                elif len(new_password1) < 8:
                    messages.error(request, 'Пароль должен содержать минимум 8 символов.')
                else:
                    # Устанавливаем новый пароль
                    user.set_password(new_password1)

                    # Очищаем токен
                    user.reset_token = None
                    user.reset_token_created_at = None
                    user.save()

                    messages.success(request, '✅ Пароль успешно изменен! Теперь вы можете войти.')
                    return redirect('users:login')
        else:
            form = PasswordResetConfirmForm()

        context = {
            'form': form,
            'user_email': user.email
        }
        return render(request, 'users/password_reset_confirm.html', context)

    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА В password_reset_confirm:")
        print(traceback.format_exc())
        print(f"{'=' * 60}\n")

        messages.error(
            request,
            f'Произошла ошибка: {str(e)}. Пожалуйста, попробуйте еще раз.'
        )
        return redirect('users:password_reset')


@login_required
def profile(request):
    user = request.user
    context = {
        'user': user,
    }
    return render(request, 'users/profile.html', context)


# Менеджерские представления
@login_required
def user_list(request):
    if not request.user.is_manager:
        messages.error(request, _('Доступ запрещен'))
        return redirect('home')

    users = CustomUser.objects.all()
    return render(request, 'users/user_list.html', {'users': users})


@login_required
def toggle_user_block(request, pk):
    if not request.user.is_manager:
        messages.error(request, _('Доступ запрещен'))
        return redirect('home')

    user = get_object_or_404(CustomUser, pk=pk)

    if user == request.user:
        messages.error(request, _('Нельзя заблокировать самого себя'))
    else:
        user.is_blocked = not user.is_blocked
        user.save()

        status = _('заблокирован') if user.is_blocked else _('разблокирован')
        messages.success(request, f'Пользователь {user.username} {status}')

    return redirect('users:user_list')


def confirm_email(request, token):
    """Упрощенная функция подтверждения email для курсовой"""
    try:
        # Находим пользователя по confirmation_code
        user = CustomUser.objects.get(confirmation_code=token)
        user.email_confirmed = True
        user.confirmation_code = None
        user.save()

        messages.success(request, 'Email успешно подтвержден! Теперь вы можете войти.')
        return redirect('users:login')

    except CustomUser.DoesNotExist:
        messages.error(request, 'Неверная ссылка подтверждения')
        return redirect('mailer:home')


def send_confirmation_email(user):
    """Отправка письма для подтверждения email"""
    print(f"=== EMAIL ДЛЯ ПОДТВЕРЖДЕНИЯ ===")
    print(f"Кому: {user.email}")
    print(f"Ссылка: http://127.0.0.1:8000/users/confirm-email/test-token/")
    print(f"=== КОНЕЦ СООБЩЕНИЯ ===")
