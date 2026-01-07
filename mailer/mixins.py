from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _


class OwnerRequiredMixin(LoginRequiredMixin):
    """Проверяет, что пользователь является владельцем ИЛИ имеет права"""

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        # Менеджеры видят всё (по role или по группе)
        if user.role == 'manager' or user.groups.filter(name='Менеджеры').exists():
            return qs

        # Обычные пользователи видят только своё
        return qs.filter(user=user)

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object() if hasattr(self, 'get_object') else None

        if obj:
            user = request.user

            # Если пользователь не менеджер
            if not (user.role == 'manager' or user.groups.filter(name='Менеджеры').exists()):
                # Проверяем, что у объекта есть поле user и это текущий пользователь
                if hasattr(obj, 'user') and obj.user != user:
                    # Но также проверяем права Django
                    if not user.has_perm('mailer.view_mailing'):  # пример права
                        from django.core.exceptions import PermissionDenied
                        raise PermissionDenied('У вас нет прав для доступа к этому объекту')

        return super().dispatch(request, *args, **kwargs)


class ManagerRequiredMixin(UserPassesTestMixin):
    """Только для менеджеров (проверяем И role И группу)"""

    def test_func(self):
        user = self.request.user

        if not user.is_authenticated:
            return False

        # Способ 1: Проверяем по полю role (твоя существующая логика)
        if user.role == 'manager':
            return True

        # Способ 2: Проверяем по группе Django (новое требование)
        if user.groups.filter(name='Менеджеры').exists():
            # Автоматически обновляем role для согласованности
            if user.role != 'manager':
                user.role = 'manager'
                user.save()
            return True

        return False  # Не менеджер

    def handle_no_permission(self):
        from django.contrib import messages
        messages.error(self.request, 'Только менеджеры имеют доступ к этой странице')
        return super().handle_no_permission()


class UserIsNotBlockedMixin:
    """Проверяет, что пользователь не заблокирован"""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_blocked:
            from django.contrib import messages
            messages.error(request, _('Ваш аккаунт заблокирован'))
            from django.contrib.auth import logout
            logout(request)
            from django.shortcuts import redirect
            return redirect('users:login')
        return super().dispatch(request, *args, **kwargs)


class RecipientOwnerRequiredMixin(LoginRequiredMixin):
    """Проверяет, что пользователь имеет доступ к получателю через ManyToMany"""

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == 'manager':
            return qs  # Менеджеры видят всех
        return qs.filter(users=self.request.user)  # <-- фильтр по ManyToMany

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object() if hasattr(self, 'get_object') else None

        if obj and not request.user.role == 'manager':
            # Проверяем, есть ли пользователь в связанных users
            if not obj.users.filter(id=request.user.id).exists():
                raise PermissionDenied('У вас нет прав для доступа к этому получателю')

        return super().dispatch(request, *args, **kwargs)
