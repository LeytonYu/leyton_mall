from django.contrib import admin
from apps.order.models import OrderInfo, OrderGoods

# Register your models here.

admin.site.register(OrderInfo)
admin.site.register(OrderGoods)
