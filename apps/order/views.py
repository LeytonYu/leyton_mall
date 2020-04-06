from _datetime import datetime

from alipay import AliPay
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django_redis import get_redis_connection
from django.db import transaction
from .models import OrderInfo, OrderGoods
from apps.goods.models import GoodsSKU
from apps.user.models import Address


# /order/place
class OrderPlaceView(LoginRequiredMixin, View):
    """提交订单页面显示"""

    def post(self, request):
        user = request.user
        sku_ids = request.POST.getlist('sku_id')
        count = request.POST.get("sku_count")
        if not sku_ids:
            return redirect(reverse('cart:show'))
        address = Address.objects.filter(user=user)
        if count:
            try:
                count = int(count)
                sku = GoodsSKU.objects.get(id=sku_ids[0])
                conn = get_redis_connection('default')
                cart_key = 'cart_%d' % user.id
                conn.hset(cart_key, sku.id, count)
                amount = sku.price * count
                sku.count = count
                sku.amount = amount
                context = {
                    'address': address,
                    'total_count': count,
                    'total_price': amount,
                    'total_freight': sku.freight,
                    'total_pay':amount+sku.freight,
                    'skus': [sku],
                    'sku_ids': sku_ids[0],
                }
            except:
                if sku_ids:
                    return redirect(reverse('goods:detail'+sku_ids[0]))
                else:
                    return redirect(reverse('goods:index'))
        else:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id

            total_count = 0
            total_price = 0
            total_freight = 0
            skus = []
            for sku_id in sku_ids:
                sku = GoodsSKU.objects.get(id=sku_id)
                count = int(conn.hget(cart_key, sku_id))
                amount = sku.price * count
                sku.count = count
                sku.amount = amount
                total_count += count
                total_price += amount
                skus.append(sku)
                total_freight += sku.freight
            total_pay = total_price + total_freight
            sku_ids = ','.join(sku_ids)
            context = {
                'address': address,
                'total_count': total_count,
                'total_price': total_price,
                'total_freight': total_freight,
                'total_pay': total_pay,
                'skus': skus,
                'sku_ids': sku_ids,
            }
        return render(request, 'place_order.html', context)


# /order/commit
class OrderCommintView(View):
    """提交订单"""

    @transaction.atomic
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请先登录OK？'})
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')
        print([addr_id, pay_method, sku_ids])
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        try:
            address = Address.objects.get(id=addr_id)
        except Exception:
            return JsonResponse({'res': 2, 'errmsg': '有这个地址吗？嗯？'})

        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 3, 'errmsg': '非法支付方式'})

        order_id = '%s%s' % (datetime.now().strftime('%Y%m%d%H%M%S'), str(user.id))
        total_count = 0
        total_price = 0
        total_freight = 0

        # 设置事务保存点
        save_id = transaction.savepoint()

        try:
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=address,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             total_freight=total_freight)
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            sku_ids = sku_ids.split(',')

            for sku_id in sku_ids:
                try:
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 4, 'errmsg': '哦！商品找不到了'})

                count = int(conn.hget(cart_key, sku_id))
                if count > sku.stock:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})
                OrderGoods.objects.create(order=order,
                                          sku=sku,
                                          count=count,
                                          price=sku.price)
                sku.stock -= count
                sku.sales += count
                sku.save()
                total_freight += sku.freight
                total_price += sku.price * count
                total_count += count

                # print('user:%d stock:%d' % (user.id, sku.stock))
                # import time
                # time.sleep(10)
            order.total_count = total_count
            order.total_price = total_price
            order.total_freight = total_freight
            order.save()
        except Exception:
            print(Exception)
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '抱歉，下单失败了'})

        transaction.savepoint_commit(save_id)
        conn.hdel(cart_key, *sku_ids)
        return JsonResponse({'res': 5, 'message': '下单成功'})


# /order/pay
class OrderPayView(View):
    """订单支付"""

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        order_id = request.POST.get('order_id')
        print('订单id：', order_id, '用户id', user.id)
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 业务处理：使用python sdk调用支付宝的支付接口
        # alipay初始化
        app_private_key_string = open("apps/order/app_private_key.pem").read()
        alipay_public_key_string = open("apps/order/alipay_public_key.pem").read()

        # app_private_key_string = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        # alipay_public_key_string = os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')

        alipay = AliPay(
            appid="2016102000727191",  # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",
            debug=True  # 默认False, 此处沙箱模拟True
        )

        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        total_pay = order.total_price + order.total_freight
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,  # 订单id
            total_amount=str(total_pay),  # 支付总金额
            subject='雷顿商城%s' % order_id,
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?{0}'.format(order_string)

        return JsonResponse({'res': 3, 'pay_url': pay_url})


# /order/check
class OrderCheckView(View):
    """查看订单支付结果"""

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        order_id = request.POST.get('order_id')
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单'})
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 业务处理：使用python sdk调用支付宝的支付接口
        # alipay初始化
        app_private_key_string = open("apps/order/app_private_key.pem").read()
        alipay_public_key_string = open("apps/order/alipay_public_key.pem").read()

        alipay = AliPay(
            appid="2016102000727191",  # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",
            debug=True  # 默认False, 此处沙箱模拟True
        )

        # 调用支付宝的交易查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)

            # response = {
            # "trade_no": "2017032121001004070200176844",  # 支付宝交易号
            # "code": "10000",  # 接口调用成功
            # "invoice_amount": "20.00",
            # "open_id": "20880072506750308812798160715407",
            # "fund_bill_list": [
            #     {
            #         "amount": "20.00",
            #         "fund_channel": "ALIPAYACCOUNT"
            #     }
            # ],
            # "buyer_logon_id": "csq***@sandbox.com",
            # "send_pay_date": "2017-03-21 13:29:17",
            # "receipt_amount": "20.00",
            # "out_trade_no": "out_trade_no15",
            # "buyer_pay_amount": "20.00",
            # "buyer_user_id": "2088102169481075",
            # "msg": "Success",
            # "point_amount": "0.00",
            # "trade_status": "TRADE_SUCCESS",  # 支付结果
            # "total_amount": "20.00"
            # }

            code = response.get('code')

            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                # 支付成功
                # 获取支付宝交易号
                trade_no = response.get('trade_no')
                # 更新订单状态
                order.trade_no = trade_no
                order.order_status = 4  # 待评价
                order.save()
                # 返回应答
                return JsonResponse({'res': 3, 'message': '支付成功'})
            elif code == '40004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):
                # 等待买家付款
                import time
                time.sleep(3)
                continue
            else:
                # 支付出错
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})


# /order/comment
class OrderCommentView(LoginRequiredMixin, View):
    """评论相关"""

    def get(self, request, order_id):
        """处理评论"""
        user = request.user
        if not order_id:
            return redirect(reverse('user:order'))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        order_goods = OrderGoods.objects.filter(order_id=order_id)
        for order_good in order_goods:
            order_good.amount = order_good.price * order_good.count

        order.order_goods = order_goods
        return render(request, 'order_comment.html', {'order': order})

    def post(self, request, order_id):
        """订单评论提交"""
        if not order_id:
            return redirect(reverse('user:order', kwargs={'page': 1}))
        try:
            order = OrderInfo.objects.get(order_id=order_id)
        except Exception:
            return redirect(reverse('user:order', kwargs={'page': 1}))
        total_count = int(request.POST.get('total_count'))

        for i in range(1, total_count + 1):
            sku_id = request.POST.get("sku_%d" % i)
            comment = request.POST.get('content_%d' % i)
            try:
                order_good = OrderGoods.objects.get(order=order, sku_id=sku_id)
                order_good.comment = comment
                order_good.save()
            except Exception:
                print(Exception)

        order.order_status = 5
        order.save()
        return redirect(reverse('user:order', kwargs={'page': 1}))
