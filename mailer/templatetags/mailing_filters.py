from django import template

register = template.Library()


@register.filter
def filter_by(queryset, condition):
    """Фильтрация QuerySet по условию 'field:value'"""
    if not queryset:
        return queryset

    field, value = condition.split(':')

    if hasattr(queryset, 'filter'):
        return queryset.filter(**{field: value})

    # Если это список
    return [obj for obj in queryset if getattr(obj, field) == value]


@register.filter
def divide(value, arg):
    """Делит значение на аргумент"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0


@register.filter
def multiply(value, arg):
    """Умножает значение на аргумент"""
    try:
        return float(value) * float(arg)
    except ValueError:
        return 0
