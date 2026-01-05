from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

from users.models import CustomUser

User = get_user_model()


class EmailBackend(ModelBackend):
    """Аутентификация по email или username"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:

            email_or_username = username

            # Пробуем найти пользователя по email или username
            user = CustomUser.objects.get(
                Q(email=email_or_username) | Q(username=email_or_username)
            )

            if user.check_password(password):
                return user
        except CustomUser.DoesNotExist:
            return None
        except CustomUser.MultipleObjectsReturned:
            return CustomUser.objects.filter(email=email_or_username).first()