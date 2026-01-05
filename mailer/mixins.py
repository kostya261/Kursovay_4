from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _


class OwnerRequiredMixin(LoginRequiredMixin):
    """Проверяет, что пользователь является владельцем объекта (у которого есть поле user)"""

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == 'manager':  # Менеджеры видят всё
            return qs
        return qs.filter(user=self.request.user)  # Обычные пользователи видят только своё

    def dispatch(self, request, *args, **kwargs):
        """Проверяем доступ перед выполнением view"""
        obj = self.get_object() if hasattr(self, 'get_object') else None

        if obj and not request.user.role == 'manager':
            # Проверяем что у объекта есть поле user и это текущий пользователь
            if hasattr(obj, 'user') and obj.user != request.user:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('У вас нет прав для доступа к этому объекту')

        return super().dispatch(request, *args, **kwargs)


class ManagerRequiredMixin(UserPassesTestMixin):
    """Только для менеджеров"""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'manager'

    def handle_no_permission(self):
        from django.contrib import messages
        messages.error(self.request, _('Только менеджеры имеют доступ к этой странице'))
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
