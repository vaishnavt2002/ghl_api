from django.urls import path, include
from . import views
urlpatterns = [
    path('login/', views.login, name= 'login'),
    path('', views.callback, name='callback'),
    path('update-contact/', views.update_contact, name='update_contact'),
]