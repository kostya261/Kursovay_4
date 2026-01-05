from django.core.cache import cache
from mailer.models import Recipient
from config.settings import CACHE_ENABLED


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
