from django.urls import path
from django.views.decorators.cache import cache_page

from . import views

app_name = 'mailer'
urlpatterns = [
    # Главная страница
    path('', views.home, name='home'),

    # Получатели
    path('recipients/', views.RecipientListView.as_view(), name='recipient_list'),
    path('recipients/create/', views.RecipientCreateView.as_view(), name='recipient_create'),
    path('recipients/<int:pk>/edit/', cache_page(120)(views.RecipientUpdateView.as_view()), name='recipient_update'),
    path('recipients/<int:pk>/delete/', views.RecipientDeleteView.as_view(), name='recipient_delete'),

    # Сообщения
    path('messages/', views.MessageListView.as_view(), name='message_list'),
    path('messages/create/', views.MessageCreateView.as_view(), name='message_create'),
    path('messages/<int:pk>/edit/', cache_page(120)(views.MessageUpdateView.as_view()), name='message_update'),
    path('messages/<int:pk>/delete/', views.MessageDeleteView.as_view(), name='message_delete'),

    # Рассылки
    path('mailings/', views.MailingListView.as_view(), name='mailing_list'),
    path('mailings/create/', views.MailingCreateView.as_view(), name='mailing_create'),
    path('mailings/<int:pk>/', cache_page(120)(views.MailingDetailView.as_view()), name='mailing_detail'),
    path('mailings/<int:pk>/edit/', cache_page(120)(views.MailingUpdateView.as_view()), name='mailing_update'),
    path('mailings/<int:pk>/delete/', views.MailingDeleteView.as_view(), name='mailing_delete'),
    path('mailings/<int:pk>/send/', views.send_mailing_now, name='mailing_send'),

    # Для обычного пользователя
    path('mailings/send-my/',
         views.send_my_due_mailings,
         name='send_my_due_mailings'),

    path('mailings/my-results/',
         views.my_send_results,
         name='my_send_results'),


    # Manager URLs
    path('manager/mailings/',
         views.ManagerMailingListView.as_view(),
         name='manager_mailing_list'),
    path('manager/recipients/',
         views.ManagerRecipientListView.as_view(),
         name='manager_recipient_list'),
    path('manager/mailings/<int:pk>/toggle/',
         views.ManagerMailingToggleView.as_view(),
         name='manager_mailing_toggle'),
    path('manager/mailings/send-all/',
         views.send_all_due_mailings,
         name='manager_send_all_mailings'),

    path('manager/mailings/send-all/',
         views.send_all_due_mailings,
         name='manager_send_all_mailings'),
    path('manager/mailings/results/',
         views.send_all_results,
         name='manager_send_results'),

    # Статистика
    path('statistics/', views.statistics, name='statistics'),
    path('statistics/<int:mailing_id>/',
         views.statistics_detail,
         name='statistics_detail'),
]
