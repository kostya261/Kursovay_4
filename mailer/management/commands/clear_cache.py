from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = 'Очищает весь кеш приложения'

    def handle(self, *args, **options):
        # Увеличиваем версию кеша
        current_version = cache.get('cache_version', 0)
        new_version = current_version + 1
        cache.set('cache_version', new_version, None)  # None = никогда не истекает

        # Также очищаем основные ключи (на всякий случай)
        cache.delete('total_mailings')
        cache.delete('unique_recipients')

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Кеш очищен! Старая версия: {current_version}, Новая версия: {new_version}'
            )
        )