from django.contrib import admin
from django.urls import path, include
from .views import CartAddView,CartInfoView,CartUpdateView,CartDeleteView

app_name='cart'
urlpatterns = [
    path('add/', CartAddView.as_view(),name='add'),
    path('update/',CartUpdateView.as_view(),name='update'),
    path('delete/',CartDeleteView.as_view(),name='delete'),
    path('',CartInfoView.as_view(),name='show')
]