from django.core.management.base import BaseCommand
from django.utils import timezone
from mailer.services import process_due_mailings, send_mailing_task
from mailer.models import Mailing


class Command(BaseCommand):
    help = 'Отправка рассылок'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mailing-id',
            type=int,
            help='ID конкретной рассылки для отправки'
        )
        parser.add_argument(
            '--all-due',
            action='store_true',
            help='Отправить все рассылки, которые должны быть отправлены сейчас'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительная отправка вне временного окна'
        )

    def handle(self, *args, **options):
        mailing_id = options.get('mailing_id')
        all_due = options.get('all_due')
        force = options.get('force')

        if mailing_id:
            # Отправка конкретной рассылки
            self.stdout.write(f'Отправка рассылки #{mailing_id}')

            if force:
                # Принудительная отправка
                result = send_mailing_task(mailing_id)
                if result:
                    self.stdout.write(self.style.SUCCESS('Рассылка отправлена'))
                else:
                    self.stdout.write(self.style.ERROR('Ошибка отправки рассылки'))
            else:
                # Проверка времени
                try:
                    mailing = Mailing.objects.get(id=mailing_id)
                    now = timezone.now()

                    if mailing.start_time <= now <= mailing.end_time:
                        result = send_mailing_task(mailing_id)
                        if result:
                            self.stdout.write(self.style.SUCCESS('Рассылка отправлена'))
                        else:
                            self.stdout.write(self.style.ERROR('Ошибка отправки рассылки'))
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Рассылка не в активном временном окне. '
                                f'Активна с {mailing.start_time} по {mailing.end_time}. '
                                f'Используйте --force для принудительной отправки.'
                            )
                        )

                except Mailing.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'Рассылка #{mailing_id} не найдена'))

        elif all_due:
            # Отправка всех рассылок, которые должны быть отправлены сейчас
            self.stdout.write('Поиск и отправка активных рассылок...')
            results = process_due_mailings()

            if results:
                success_count = sum(1 for r in results if r['success'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Обработано {len(results)} рассылок. '
                        f'Успешно: {success_count}'
                    )
                )
            else:
                self.stdout.write('Нет активных рассылок для отправки')

        else:
            # Показать справку
            self.stdout.write('Использование:')
            self.stdout.write('  python manage.py send_mailings --mailing-id=1')
            self.stdout.write('  python manage.py send_mailings --all-due')
            self.stdout.write('  python manage.py send_mailings --mailing-id=1 --force')
