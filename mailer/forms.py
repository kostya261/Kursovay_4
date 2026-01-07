from django import forms
from .models import Recipient, Message, Mailing


class RecipientForm(forms.ModelForm):
    class Meta:
        model = Recipient
        fields = ['email', 'full_name', 'comment']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        email = self.cleaned_data['email']

        # Ищем существующего получателя по email
        try:
            recipient = Recipient.objects.get(email=email)
            # Обновляем данные, если они изменились
            if recipient.full_name != self.cleaned_data['full_name']:
                recipient.full_name = self.cleaned_data['full_name']
            if recipient.comment != self.cleaned_data.get('comment'):
                recipient.comment = self.cleaned_data.get('comment')
            recipient.save()
        except Recipient.DoesNotExist:
            # Создаем нового получателя
            recipient = super().save(commit=commit)

        # Добавляем текущего пользователя в связь ManyToMany
        if self.user and recipient and self.user not in recipient.users.all():
            recipient.users.add(self.user)

        return recipient


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['subject', 'body']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


class MailingForm(forms.ModelForm):
    recipients = forms.ModelMultipleChoiceField(
        queryset=Recipient.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta:
        model = Mailing
        fields = ['start_time', 'end_time', 'message', 'recipients']
        widgets = {
            'start_time': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}
            ),
            'end_time': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}
            ),
            'message': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            # Показываем только получателей, доступных пользователю
            if self.user.role == 'manager':
                # Менеджер видит всех получателей
                self.fields['recipients'].queryset = Recipient.objects.all()
            else:
                # Пользователь видит только своих получателей
                self.fields['recipients'].queryset = self.user.recipients_accessible.all()

            # Сообщения остаются как были
            self.fields['message'].queryset = Message.objects.filter(user=self.user)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
            self.save_m2m()
        return instance
