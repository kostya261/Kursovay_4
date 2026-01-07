from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from mailer.models import Mailing, Recipient, Message, Attempt
from users.models import CustomUser


class Command(BaseCommand):
    help = 'Создает группы и назначает права'

    def handle(self, *args, **options):
        # 1. Группа Менеджеров
        manager_group, created = Group.objects.get_or_create(name='Менеджеры')

        if created:
            self.stdout.write(self.style.SUCCESS('Группа "Менеджеры" создана'))
        else:
            self.stdout.write('Группа "Менеджеры" уже существует')

        # 2. Группа Пользователей
        user_group, created = Group.objects.get_or_create(name='Пользователи')

        if created:
            self.stdout.write(self.style.SUCCESS('Группа "Пользователи" создана'))
        else:
            self.stdout.write('Группа "Пользователи" уже существует')

        # 3. Права для менеджеров
        # Все права на модели mailer
        mailer_models = [Mailing, Recipient, Message, Attempt]

        for model in mailer_models:
            content_type = ContentType.objects.get_for_model(model)
            permissions = Permission.objects.filter(content_type=content_type)
            manager_group.permissions.add(*permissions)
            self.stdout.write(f'Добавлены права на {model.__name__} для менеджеров')

        # Право просмотра всех пользователей
        user_content_type = ContentType.objects.get_for_model(CustomUser)
        view_permission = Permission.objects.get(
            codename='view_customuser',
            content_type=user_content_type
        )
        manager_group.permissions.add(view_permission)
        self.stdout.write('Добавлено право просмотра пользователей для менеджеров')

        # 4. Права для обычных пользователей
        # Только базовые права на свои объекты
        user_permissions = Permission.objects.filter(
            codename__in=['add_mailing', 'change_mailing', 'delete_mailing',
                          'add_recipient', 'change_recipient', 'delete_recipient',
                          'add_message', 'change_message', 'delete_message']
        )
        user_group.permissions.add(*user_permissions)
        self.stdout.write('Добавлены базовые права для пользователей')

        # 5. Создаем суперпользователя-менеджера (для теста)
        if not CustomUser.objects.filter(username='manager').exists():
            manager_user = CustomUser.objects.create_user(
                username='manager',
                email='manager@example.com',
                password='manager123',
                role='manager',
                email_confirmed=True
            )
            manager_user.groups.add(manager_group)
            self.stdout.write(self.style.SUCCESS('Создан тестовый менеджер: manager / manager123'))

        self.stdout.write(self.style.SUCCESS('Группы и права успешно настроены!'))
