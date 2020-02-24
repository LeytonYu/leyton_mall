from django.urls import path
from .views import OrderPlaceView, OrderCommintView, OrderPayView,OrderCheckView,OrderCommentView

app_name='order'
urlpatterns = [
    path('place/', OrderPlaceView.as_view(),name='place'),
    path('commit/',OrderCommintView.as_view(),name='commit'),
    path('pay/',OrderPayView.as_view(),name='pay'),
    path('check/',OrderCheckView.as_view(),name='check'),
    path('comment/<str:order_id>',OrderCommentView.as_view(),name='comment'),
]