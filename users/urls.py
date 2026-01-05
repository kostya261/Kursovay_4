from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),

    path('password-reset/', views.password_reset, name='password_reset'),
    path('password-reset-confirm/<str:token>/',
         views.password_reset_confirm,
         name='password_reset_confirm'),

    # Менеджерские URLs
    path('users/', views.user_list, name='user_list'),
    path('users/<int:pk>/toggle-block/',
         views.toggle_user_block,
         name='toggle_user_block'),

    path('confirm-email/<str:token>/', views.confirm_email, name='confirm_email'),
]
