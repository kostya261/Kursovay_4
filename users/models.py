from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """Кастомная модель пользователя с ролями"""

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Role(models.TextChoices):
        USER = 'user', _('Пользователь')
        MANAGER = 'manager', _('Менеджер')

    email = models.EmailField(
        _('email address'),
        unique=True,
        blank=False,
        null=False
    )
    role = models.CharField(
        _('роль'),
        max_length=20,
        choices=Role.choices,
        default=Role.USER
    )
    is_blocked = models.BooleanField(
        _('заблокирован'),
        default=False
    )
    email_confirmed = models.BooleanField(
        _('email подтвержден'),
        default=False
    )

    confirmation_code = models.CharField(
        max_length=64,
        blank=True,
        null=True
    )
    reset_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Токен сброса пароля'
    )
    reset_token_created_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Время создания токена'
    )

    email_confirmation_token = models.CharField(
        max_length=64,
        blank=True,
        null=True
    )

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        related_name='customuser_set',
        related_query_name='user'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        related_name='customuser_set',
        related_query_name='user'
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
