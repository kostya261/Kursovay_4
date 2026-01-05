from django.contrib import admin
from .models import Recipient, Message, Mailing, Attempt, UserStatistics

admin.site.register(Recipient)
admin.site.register(Message)
admin.site.register(Mailing)
admin.site.register(Attempt)
admin.site.register(UserStatistics)
