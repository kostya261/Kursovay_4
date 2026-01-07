import logging

from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone

from config import settings
from mailer.models import Recipient, Mailing, Attempt
from config.settings import CACHE_ENABLED


logger = logging.getLogger(__name__)

def get_cached_recipients(user):
    """Простая функция кеширования"""

    cache_key = f'recipients_{user.id}'

    if CACHE_ENABLED:
        # Пытаемся получить из кеша
        recipients = cache.get(cache_key)

        if recipients is not None:
            return recipients

    # Делаем запрос к БД
    if user.role == 'manager':
        recipients = Recipient.objects.all()
    else:
        recipients = Recipient.objects.filter(users=user)

    recipients = recipients.order_by('full_name')

    # Сохраняем в кеш на 2 минуты
    if CACHE_ENABLED:
        cache.set(cache_key, recipients, 120)

    return recipients


def send_mailing_task(mailing_id):
    """
    Задача отправки рассылки
    Может вызываться из команды или Celery
    """
    try:
        mailing = Mailing.objects.get(id=mailing_id)
        now = timezone.now()

        # Проверяем время рассылки
        if not (mailing.start_time <= now <= mailing.end_time):
            logger.warning(f'Рассылка {mailing_id} не в активном временном окне')
            return False

        recipients = mailing.recipients.all()
        if not recipients.exists():
            logger.warning(f'Нет получателей для рассылки {mailing_id}')
            return False

        success_count = 0
        fail_count = 0

        for recipient in recipients:
            try:
                send_mail(
                    subject=mailing.message.subject,
                    message=mailing.message.body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient.email],
                    fail_silently=False,
                )

                Attempt.objects.create(
                    mailing=mailing,
                    status=Attempt.STATUS_SUCCESS,
                    server_response='Письмо успешно отправлено'
                )
                success_count += 1
                logger.info(f'Письмо отправлено {recipient.email}')

            except Exception as e:
                Attempt.objects.create(
                    mailing=mailing,
                    status=Attempt.STATUS_FAILED,
                    server_response=str(e)
                )
                fail_count += 1
                logger.error(f'Ошибка отправки {recipient.email}: {e}')

        logger.info(f'Рассылка {mailing_id} завершена. '
                    f'Успешно: {success_count}, Неудачно: {fail_count}')
        return True

    except Mailing.DoesNotExist:
        logger.error(f'Рассылка {mailing_id} не найдена')
        return False
    except Exception as e:
        logger.error(f'Ошибка отправки рассылки {mailing_id}: {e}')
        return False


def process_due_mailings():
    """
    Обработка всех рассылок, которые должны быть отправлены сейчас
    Возвращает подробный отчет
    """
    now = timezone.now()

    # Находим активные рассылки
    active_mailings = Mailing.objects.filter(
        start_time__lte=now,
        end_time__gte=now
    ).select_related('message').prefetch_related('recipients')

    results = []
    total_recipients = 0
    total_success = 0
    total_failed = 0

    for mailing in active_mailings:
        mailing_result = {
            'mailing_id': mailing.id,
            'subject': mailing.message.subject,
            'creator': mailing.user.username,
            'recipients_count': mailing.recipients.count(),
            'success': False,
            'attempts': 0,
            'success_count': 0,
            'fail_count': 0,
            'errors': []
        }

        total_recipients += mailing_result['recipients_count']

        try:
            # Отправляем рассылку
            success_count = 0
            fail_count = 0

            for recipient in mailing.recipients.all():
                try:
                    send_mail(
                        subject=mailing.message.subject,
                        message=mailing.message.body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[recipient.email],
                        fail_silently=False,
                    )

                    Attempt.objects.create(
                        mailing=mailing,
                        status=Attempt.STATUS_SUCCESS,
                        server_response='Письмо успешно отправлено'
                    )
                    success_count += 1
                    total_success += 1

                except Exception as e:
                    Attempt.objects.create(
                        mailing=mailing,
                        status=Attempt.STATUS_FAILED,
                        server_response=str(e)
                    )
                    fail_count += 1
                    total_failed += 1
                    mailing_result['errors'].append(f"{recipient.email}: {str(e)}")

            mailing_result['success_count'] = success_count
            mailing_result['fail_count'] = fail_count
            mailing_result['attempts'] = success_count + fail_count
            mailing_result['success'] = fail_count == 0  # Успех если нет ошибок

            results.append(mailing_result)

            logger.info(f'Рассылка {mailing.id} отправлена. '
                        f'Успешно: {success_count}, Неудачно: {fail_count}')

        except Exception as e:
            mailing_result['errors'].append(f"Общая ошибка: {str(e)}")
            results.append(mailing_result)
            logger.error(f'Ошибка отправки рассылки {mailing.id}: {e}')

    # Итоговый отчет
    summary = {
        'total_mailings': len(results),
        'total_recipients': total_recipients,
        'total_success': total_success,
        'total_failed': total_failed,
        'results': results
    }

    return summary


def process_user_due_mailings(user):
    """
    Обработка активных рассылок конкретного пользователя
    """
    now = timezone.now()

    # Находим активные рассылки пользователя
    active_mailings = Mailing.objects.filter(
        user=user,
        start_time__lte=now,
        end_time__gte=now
    ).select_related('message').prefetch_related('recipients')

    results = []

    for mailing in active_mailings:
        result = send_mailing_task(mailing.id)
        results.append({
            'mailing_id': mailing.id,
            'subject': mailing.message.subject,
            'success': result,
            'recipients_count': mailing.recipients.count()
        })

    return results
