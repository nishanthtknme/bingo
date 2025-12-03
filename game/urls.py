from django.urls import path
from . views import *
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('bingo', views.bingo, name='bingo'),
    path("room/<str:code>/", views.game_room, name="game_room"),
]
