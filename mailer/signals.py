from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Mailing, Recipient, Attempt, UserStatistics

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_statistics(sender, instance, created, **kwargs):
    """Создаем статистику при создании пользователя"""
    if created:
        UserStatistics.objects.create(user=instance)


@receiver(post_save, sender=Mailing)
@receiver(post_delete, sender=Mailing)
def update_mailing_stats(sender, instance, **kwargs):
    """Обновляем статистику при изменении рассылок"""
    if hasattr(instance, 'user'):
        update_user_statistics(instance.user)


@receiver(post_save, sender=Attempt)
@receiver(post_delete, sender=Attempt)
def update_attempt_stats(sender, instance, **kwargs):
    """Обновляем статистику при изменении попыток"""
    if hasattr(instance.mailing, 'user'):
        update_user_statistics(instance.mailing.user)


def update_user_statistics(user):
    """Функция обновления статистики пользователя"""
    try:
        stats = UserStatistics.objects.get(user=user)
        now = timezone.now()

        # Рассылки
        stats.total_mailings = Mailing.objects.filter(user=user).count()

        # Активные рассылки (текущее время между start_time и end_time)
        stats.active_mailings = Mailing.objects.filter(
            user=user,
            start_time__lte=now,  # начало уже прошло
            end_time__gte=now  # еще не закончилось
        ).count()

        # Получатели
        stats.total_recipients = Recipient.objects.filter(users=user).count()

        # Попытки
        user_mailings = Mailing.objects.filter(user=user)
        attempts = Attempt.objects.filter(mailing__in=user_mailings)

        stats.total_attempts = attempts.count()
        stats.successful_attempts = attempts.filter(
            status=Attempt.STATUS_SUCCESS
        ).count()
        stats.failed_attempts = attempts.filter(
            status=Attempt.STATUS_FAILED
        ).count()

        stats.save()
    except UserStatistics.DoesNotExist:
        pass
