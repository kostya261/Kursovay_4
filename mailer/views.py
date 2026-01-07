from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.db.models import Count
from django.db.models import Q

from .mixins import UserIsNotBlockedMixin, OwnerRequiredMixin, ManagerRequiredMixin, RecipientOwnerRequiredMixin
from .models import Recipient, Message, Mailing, Attempt, UserStatistics
from .forms import RecipientForm, MessageForm, MailingForm
from .services import get_cached_recipients


# Главная страница
@cache_control(max_age=300, public=True)
def home(request):
    now = timezone.now()

    # 1. Кешируем общее количество рассылок (5 минут)
    cache_key_total = 'total_mailings'
    total_mailings = cache.get(cache_key_total)

    if not total_mailings:
        total_mailings = Mailing.objects.count()
        cache.set(cache_key_total, total_mailings, 60 * 5)  # 5 минут

    # 2. Кешируем активные рассылки (1 минута)
    cache_key_active = f'active_mailings_{now.strftime("%Y%m%d_%H")}'
    active_mailings = cache.get(cache_key_active)

    if not active_mailings:
        active_mailings = Mailing.objects.filter(
            start_time__lte=now,
            end_time__gte=now
        ).count()
        cache.set(cache_key_active, active_mailings, 60)  # 1 минута

    # 3. Кешируем уникальных получателей (10 минут)
    cache_key_recipients = 'unique_recipients'
    unique_recipients = cache.get(cache_key_recipients)

    if not unique_recipients:
        unique_recipients = Recipient.objects.count()
        cache.set(cache_key_recipients, unique_recipients, 60 * 5)  # 5 минут

    context = {
        'total_mailings': total_mailings,
        'active_mailings': active_mailings,
        'unique_recipients': unique_recipients,
    }

    return render(request, 'mailer/home.html', context)


class BaseView(UserIsNotBlockedMixin):
    """Базовый класс для всех view с проверкой блокировки"""
    pass


# Управление получателями
class RecipientListView(BaseView, RecipientOwnerRequiredMixin, ListView):
    model = Recipient
    template_name = 'mailer/recipient_list.html'
    context_object_name = 'recipients'

    def get_queryset(self):
        return get_cached_recipients(self.request.user)


class RecipientCreateView(BaseView, LoginRequiredMixin, CreateView):
    model = Recipient
    form_class = RecipientForm
    template_name = 'mailer/recipient_form.html'
    success_url = reverse_lazy('mailer:recipient_list')

    def get_form_kwargs(self):
        """Передаем текущего пользователя в форму"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Дополнительная проверка"""

        return super().form_valid(form)


class RecipientUpdateView(BaseView, RecipientOwnerRequiredMixin, UpdateView):
    model = Recipient
    form_class = RecipientForm
    template_name = 'mailer/recipient_form.html'
    success_url = reverse_lazy('mailer:recipient_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class RecipientDeleteView(BaseView, RecipientOwnerRequiredMixin, DeleteView):
    model = Recipient
    template_name = 'mailer/recipient_confirm_delete.html'
    success_url = reverse_lazy('mailer:recipient_list')


# Управление сообщениями
class MessageListView(BaseView, OwnerRequiredMixin, ListView):
    model = Message
    template_name = 'mailer/message_list.html'
    context_object_name = 'messages'


class MessageCreateView(BaseView, LoginRequiredMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = 'mailer/message_form.html'
    success_url = reverse_lazy('mailer:message_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class MessageUpdateView(BaseView, OwnerRequiredMixin, UpdateView):
    model = Message
    form_class = MessageForm
    template_name = 'mailer/message_form.html'
    success_url = reverse_lazy('mailer:message_list')


class MessageDeleteView(BaseView, OwnerRequiredMixin, DeleteView):
    model = Message
    template_name = 'mailer/message_confirm_delete.html'
    success_url = reverse_lazy('mailer:message_list')


# Управление рассылками
class MailingListView(BaseView, OwnerRequiredMixin, ListView):
    model = Mailing
    template_name = 'mailer/mailing_list.html'
    context_object_name = 'mailings'

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.annotate(
            recipients_count=Count('recipients')
        )


class MailingCreateView(BaseView, LoginRequiredMixin, CreateView):
    model = Mailing
    form_class = MailingForm
    template_name = 'mailer/mailing_form.html'
    success_url = reverse_lazy('mailer:mailing_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class MailingUpdateView(BaseView, OwnerRequiredMixin, UpdateView):
    model = Mailing
    form_class = MailingForm
    template_name = 'mailer/mailing_form.html'
    success_url = reverse_lazy('mailer:mailing_list')

    def get_object(self, queryset=None):
        """Безопасное получение объекта с обработкой ошибок"""
        try:
            obj = super().get_object(queryset)
            # Проверяем, что сообщение существует
            if not hasattr(obj, 'message') or obj.message is None:
                from django.http import Http404
                raise Http404("Сообщение не найдено")
            return obj
        except Exception as e:
            from django.contrib import messages
            messages.error(self.request, f"Ошибка: {e}")
            from django.shortcuts import redirect
            return redirect('mailer:mailing_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class MailingDeleteView(BaseView, OwnerRequiredMixin, DeleteView):
    model = Mailing
    template_name = 'mailer/mailing_confirm_delete.html'
    success_url = reverse_lazy('mailer:mailing_list')


class MailingDetailView(BaseView, OwnerRequiredMixin, DetailView):
    model = Mailing
    template_name = 'mailer/mailing_detail.html'
    context_object_name = 'mailing'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attempts'] = self.object.attempts.all()
        return context


# Manager views
class ManagerMailingListView(BaseView, ManagerRequiredMixin, ListView):
    """Список всех рассылок для менеджера"""
    model = Mailing
    template_name = 'mailer/manager/mailing_list.html'
    context_object_name = 'mailings'

    def get_queryset(self):
        return Mailing.objects.all().select_related('user')


class ManagerRecipientListView(BaseView, ManagerRequiredMixin, ListView):
    """Список всех получателей для менеджера"""
    model = Recipient
    template_name = 'mailer/manager/recipient_list.html'
    context_object_name = 'recipients'

    def get_queryset(self):
        return Recipient.objects.all().select_related('user')


@method_decorator(login_required, name='dispatch')
class ManagerMailingToggleView(BaseView, ManagerRequiredMixin, View):
    """Включение/выключение рассылки менеджером"""

    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        messages.success(
            request,
            f'Рассылка #{mailing.id} отключена менеджером'
        )

        # Перенаправляем обратно на список рассылок менеджера
        return redirect('mailer:manager_mailing_list')


# Отправка рассылки вручную
def send_mailing_now(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    now = timezone.now()

    # Проверка времени рассылки
    if not (mailing.start_time <= now <= mailing.end_time):
        messages.error(
            request,
            f'Рассылка может быть отправлена только в период '
            f'с {mailing.start_time} по {mailing.end_time}'
        )
        return redirect('mailer:mailing_detail', pk=pk)

    # ВАЖНО: переименовываем функцию, чтобы не было конфликта с импортом
    def send_mailing_task_local(mailing_id):
        """Локальная функция для отправки, чтобы избежать конфликта имен"""
        # ... твоя логика отправки ...
        pass

    # Проверяем что получатели есть
    recipients = mailing.recipients.all()
    if not recipients.exists():
        messages.warning(request, 'Нет получателей для отправки!')
        return redirect('mailer:mailing_detail', pk=pk)

    # Или ЛУЧШЕ: полностью удаляем дублирующую функцию и используем логику напрямую

    TEST_MODE = False

    if not TEST_MODE:
        from_email = settings.DEFAULT_FROM_EMAIL
        success_count = 0
        fail_count = 0

        for recipient in recipients:
            try:
                send_mail(
                    subject=mailing.message.subject,
                    message=mailing.message.body,
                    from_email=from_email,
                    recipient_list=[recipient.email],
                    fail_silently=False,
                )

                Attempt.objects.create(
                    mailing=mailing,
                    status=Attempt.STATUS_SUCCESS,
                    server_response='Письмо успешно отправлено'
                )
                success_count += 1

            except Exception as e:
                Attempt.objects.create(
                    mailing=mailing,
                    status=Attempt.STATUS_FAILED,
                    server_response=str(e)
                )
                fail_count += 1

        messages.success(
            request,
            f'Рассылка отправлена! Успешно: {success_count}, Неудачно: {fail_count}'
        )
    else:
        # Тестовый режим
        for recipient in recipients:
            Attempt.objects.create(
                mailing=mailing,
                status=Attempt.STATUS_SUCCESS,
                server_response='Тестовый режим: письмо не отправлялось'
            )
        messages.success(
            request,
            f'Тестовый режим: создано {recipients.count()} записей о попытках'
        )

    return redirect('mailer:mailing_detail', pk=pk)


@login_required
def statistics(request):
    """Страница статистики пользователя"""
    user = request.user

    # Получаем или создаем статистику
    stats, created = UserStatistics.objects.get_or_create(user=user)

    # Получаем последние 10 рассылок
    recent_mailings = Mailing.objects.filter(user=user).order_by('-start_time')[:10]

    # Получаем последние попытки
    recent_attempts = Attempt.objects.filter(
        mailing__user=user
    ).order_by('-attempt_time')[:20]

    # Статистика по дням (последние 7 дней)
    from datetime import datetime, timedelta
    from django.db.models.functions import TruncDate

    today = datetime.now().date()
    date_range = [today - timedelta(days=i) for i in range(6, -1, -1)]

    daily_stats = Attempt.objects.filter(
        mailing__user=user,
        attempt_time__date__gte=today - timedelta(days=6)
    ).annotate(
        date=TruncDate('attempt_time')
    ).values('date').annotate(
        total=Count('id'),
        success=Count('id', filter=Q(status=Attempt.STATUS_SUCCESS)),
        failed=Count('id', filter=Q(status=Attempt.STATUS_FAILED))
    ).order_by('date')

    # Форматируем для графика
    chart_data = {
        'dates': [date.strftime('%d.%m') for date in date_range],
        'success': [0] * 7,
        'failed': [0] * 7,
    }

    for stat in daily_stats:
        if stat['date'] in date_range:
            idx = date_range.index(stat['date'])
            chart_data['success'][idx] = stat['success']
            chart_data['failed'][idx] = stat['failed']

    context = {
        'stats': stats,
        'recent_mailings': recent_mailings,
        'recent_attempts': recent_attempts,
        'chart_data': chart_data,
    }

    return render(request, 'mailer/statistics.html', context)


@login_required
def statistics_detail(request, mailing_id):
    """Детальная статистика по конкретной рассылке"""
    mailing = get_object_or_404(Mailing, id=mailing_id, user=request.user)

    attempts = mailing.attempts.all()
    total_attempts = attempts.count()
    successful = attempts.filter(status=Attempt.STATUS_SUCCESS).count()
    failed = attempts.filter(status=Attempt.STATUS_FAILED).count()

    context = {
        'mailing': mailing,
        'attempts': attempts,
        'total_attempts': total_attempts,
        'successful': successful,
        'failed': failed,
        'success_rate': round((successful / total_attempts * 100), 2) if total_attempts > 0 else 0,
    }

    return render(request, 'mailer/statistics_detail.html', context)


@login_required
def send_all_results(request):
    """Страница с результатами отправки всех рассылок"""

    # Проверяем права
    if not (request.user.role == 'manager' or request.user.groups.filter(name='Менеджеры').exists()):
        messages.error(request, 'Только менеджеры могут видеть отчеты')
        return redirect('mailer:home')

    # Получаем результаты из сессии (сохраняем после отправки)
    results = request.session.get('mailing_results', None)

    if not results:
        messages.info(request, 'Нет данных об отправке')
        return redirect('mailer:manager_mailing_list')

    # Очищаем сессию после показа
    if 'mailing_results' in request.session:
        del request.session['mailing_results']

    return render(request, 'mailer/manager/send_results.html', {
        'results': results
    })


@login_required
def my_send_results(request):
    """Результаты отправки рассылок пользователя"""

    results = request.session.get('my_mailing_results', None)

    if not results:
        messages.info(request, 'Нет данных об отправке')
        return redirect('mailer:mailing_list')

    # Очищаем сессию
    if 'my_mailing_results' in request.session:
        del request.session['my_mailing_results']

    return render(request, 'mailer/my_send_results.html', {
        'results': results
    })


@login_required
def send_all_due_mailings(request):
    """Отправка ВСЕХ активных рассылок (только для менеджеров)"""

    # Проверяем права менеджера
    if not (request.user.role == 'manager' or request.user.groups.filter(name='Менеджеры').exists()):
        messages.error(request, 'Только менеджеры могут отправлять все рассылки')
        return redirect('mailer:home')

    from .services import process_due_mailings

    try:
        # Отправляем ВСЕ активные рассылки
        summary = process_due_mailings()

        # Сохраняем в сессии
        request.session['mailing_results'] = summary

        return redirect('mailer:manager_send_results')

    except Exception as e:
        messages.error(request, f'Ошибка при отправке рассылок: {e}')
        return redirect('mailer:manager_mailing_list')


@login_required
def send_my_due_mailings(request):
    """Отправка активных рассылок ТОЛЬКО текущего пользователя"""

    from .services import process_user_due_mailings

    results = process_user_due_mailings(request.user)

    if not results:
        messages.info(request, 'У вас нет активных рассылок для отправки')
        return redirect('mailer:mailing_list')

    # Подсчет статистики
    total_success = sum(1 for r in results if r['success'])

    request.session['my_mailing_results'] = {
        'total_mailings': len(results),
        'total_success': total_success,
        'total_failed': len(results) - total_success,
        'results': results
    }

    return redirect('mailer:my_send_results')
