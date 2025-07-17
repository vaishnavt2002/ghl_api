from django.urls import path, include
from . import views
urlpatterns = [
    path('login/', views.login, name= 'login'),
    path('home/', views.home, name='home'),
    path('', views.callback, name='callback'),
    path('update-contact/', views.update_contact, name='update_contact'),
    path('logout/', views.logout, name='logout')
]