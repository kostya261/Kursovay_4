from django.core.management import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    def handle(self, *args, **options):
        User = get_user_model()
        user = User.objects.create(
            email='money261@yandex.ru',
            first_name='Konstantin',
            last_name='Kosarew',
        )

        user.is_stuff = True
        user.is_superuser = True
        user.set_password('MegaFon')

        user.save()

        self.stdout.write(self.style.SUCCESS(f'Администратор успешно создан: {user.email}!'))