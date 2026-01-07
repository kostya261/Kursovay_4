from django.db import models
from django.utils import timezone

from config import settings


class Recipient(models.Model):
    """Получатель рассылки (клиент)"""

    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name='Пользователи',
        related_name='recipients_accessible',
        blank=True
    )

    email = models.EmailField(
        verbose_name='Email',
        unique=True
    )
    full_name = models.CharField(
        verbose_name='Ф.И.О.',
        max_length=255
    )
    comment = models.TextField(
        verbose_name='Комментарий',
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    class Meta:
        verbose_name = 'Получатель'
        verbose_name_plural = 'Получатели'


class Message(models.Model):
    """Сообщение для рассылки"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='messages',
        null=True,
        blank=True
    )

    subject = models.CharField(
        verbose_name='Тема письма',
        max_length=255
    )
    body = models.TextField(
        verbose_name='Тело письма'
    )

    def save(self, *args, **kwargs):
        if not self.user and hasattr(self, '_current_user'):
            self.user = self._current_user
        super().save(*args, **kwargs)

    def __str__(self):
        return self.subject

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'


class Mailing(models.Model):
    """Рассылка"""
    STATUS_CREATED = 'Создана'
    STATUS_STARTED = 'Запущена'
    STATUS_COMPLETED = 'Завершена'

    STATUS_CHOICES = [
        (STATUS_CREATED, 'Создана'),
        (STATUS_STARTED, 'Запущена'),
        (STATUS_COMPLETED, 'Завершена'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Создатель',
        related_name='created_mailings'
    )

    start_time = models.DateTimeField(
        verbose_name='Дата и время начала отправки'
    )
    end_time = models.DateTimeField(
        verbose_name='Дата и время окончания отправки'
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        verbose_name='Сообщение',
        related_name='mailings'
    )
    recipients = models.ManyToManyField(
        Recipient,
        verbose_name='Получатели',
        related_name='mailings'
    )

    def save(self, *args, **kwargs):
        if not self.user and hasattr(self, '_current_user'):
            self.user = self._current_user
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Рассылка #{self.id} ({self.status})"

    @property
    def status(self):
        """Динамический расчет статуса рассылки"""
        now = timezone.now()

        if now < self.start_time:
            return self.STATUS_CREATED
        elif self.start_time <= now <= self.end_time:
            return self.STATUS_STARTED
        else:
            return self.STATUS_COMPLETED

    def clean(self):
        """Валидация дат"""
        from django.core.exceptions import ValidationError
        now = timezone.now()

        # Проверяем что start_time не None
        if self.start_time is None:
            raise ValidationError(
                {'start_time': 'Дата начала обязательна для заполнения'}
            )

        # Проверяем что end_time не None
        if self.end_time is None:
            raise ValidationError(
                {'end_time': 'Дата окончания обязательна для заполнения'}
            )

        if self.start_time < now:
            raise ValidationError(
                {'start_time': 'Дата начала не может быть в прошлом'}
            )

        if self.start_time >= self.end_time:
            raise ValidationError(
                {'end_time': 'Дата окончания должна быть позже даты начала'}
            )

    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        ordering = ['-start_time']


class Attempt(models.Model):
    """Попытка рассылки"""
    STATUS_SUCCESS = 'Успешно'
    STATUS_FAILED = 'Не успешно'

    STATUS_CHOICES = [
        (STATUS_SUCCESS, 'Успешно'),
        (STATUS_FAILED, 'Не успешно'),
    ]

    attempt_time = models.DateTimeField(
        verbose_name='Дата и время попытки',
        auto_now_add=True
    )
    status = models.CharField(
        verbose_name='Статус',
        max_length=20,
        choices=STATUS_CHOICES
    )
    server_response = models.TextField(
        verbose_name='Ответ почтового сервера',
        blank=True
    )
    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        verbose_name='Рассылка',
        related_name='attempts'
    )

    def __str__(self):
        return f"Попытка #{self.id} ({self.status})"

    class Meta:
        verbose_name = 'Попытка рассылки'
        verbose_name_plural = 'Попытки рассылок'
        ordering = ['-attempt_time']


class UserStatistics(models.Model):
    """Статистика пользователя"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='statistics'
    )
    total_mailings = models.IntegerField(default=0)
    active_mailings = models.IntegerField(default=0)
    total_recipients = models.IntegerField(default=0)
    total_attempts = models.IntegerField(default=0)
    successful_attempts = models.IntegerField(default=0)
    failed_attempts = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def success_rate(self):
        if self.total_attempts > 0:
            return round((self.successful_attempts / self.total_attempts) * 100, 2)
        return 0

    def __str__(self):
        return f"Статистика {self.user.username}"

    class Meta:
        verbose_name = 'Статистика пользователя'
        verbose_name_plural = 'Статистика пользователей'
