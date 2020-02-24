from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, reverse
from django.views import View
from django.http import HttpResponse
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import check_password

from apps.order.models import OrderInfo, OrderGoods
from celery_tasks.tasks import send_register_active_email
import re
from .models import User, Address
from apps.goods.models import GoodsSKU
from django_redis import get_redis_connection


# Create your views here.

# /user/register
class RegisterView(View):
    """注册"""

    def get(self, request):
        """显示注册页"""
        return render(request, 'register.html')

    def post(self, request):
        """经行注册处理"""
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        if not re.match('^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        if user:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})
        # 用户注册数据库操作
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()
        #  加密用户信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info)
        token = token.decode()
        # 发邮件
        # """发送激活邮件"""
        # subject = 'Leyton商城欢迎信息'
        # message = '您的浏览器不支持此消息类型，请更换浏览器'
        # html_message = message = '<h1>尊敬的{0},欢迎您注册Leyton商城会员</h1>请点击下面链接激活您的账户<br/>' \
        #                          '<a href="http://127.0.0.1:8000/user/active/{1}">' \
        #                          'http://127.0.0.1:8000/user/active/{2}</a>'.format(username, token, token)
        # sender = settings.EMAIL_FROM
        # receiver = [email]
        # send_mail(subject, message, sender, receiver, html_message=html_message)
        print('发邮件前')
        # celery异步发邮件
        send_register_active_email.delay(email, username, token)
        print('委托发邮件后')
        return redirect(reverse('goods:index'))


# /user/active/token
class ActiveView(View):
    """用户激活"""

    def get(self, request, token):
        """经行用户激活"""
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            return HttpResponse('激活链接已过期')


# /user/login
class LoginView(View):
    """登录"""

    def get(self, request):
        """显示登录页面"""

        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''

        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        """登录校验"""
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        print(username, password)
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '请检查信息完整性'})
        try:
            user = User.objects.get(username=username)
            password2 = user.password
            if check_password(password, password2):
                if user.is_active:
                    print("User is valid")
                    login(request, user)
                    next_url = request.GET.get('next', reverse('goods:index'))
                    response = redirect(next_url)
                    remember = request.POST.get('remember')
                    if remember == 'on':
                        response.set_cookie('username', username, max_age=7 * 24 * 3600)
                    else:
                        response.delete_cookie('username')

                    return response
                else:
                    print("User is not valid")
                    return render(request, 'login.html', {'errmsg': '账户未激活'})
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})
        except:
            return render(request, 'login.html', {'errmsg': '用户不存在'})


# /user/logout
class LogoutView(View):
    """退出登录"""

    def get(self, request):
        """退出登录"""
        logout(request)

        return redirect(reverse('goods:index'))


# /user
class UserInfoView(LoginRequiredMixin, View):
    """用户中心-信息页"""

    def get(self, request):
        """显示"""
        user = request.user
        address = Address.objects.get_default_address(user)

        con = get_redis_connection('default')
        history_key = 'history_%d' % user.id
        # 获取用户最新浏览的5个商品的id
        sku_ids = con.lrange(history_key, 0, 4)
        goods_list = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_list.append(goods)

        context = {
            'page': 'user',
            'address': address,
            'goods_list': goods_list
        }

        return render(request, 'user_center_info.html', context)


# /user/order
class UserOrderView(LoginRequiredMixin, View):
    """用户中心-订单页"""

    def get(self, request, page):
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')

        for order in orders:
            order_goods = OrderGoods.objects.filter(order_id=order.order_id)
            for order_good in order_goods:
                amount = order_good.count * order_good.price
                order_good.amount = amount
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            order.order_goods = order_goods

        paginator = Paginator(orders, 2)
        try:
            page = int(page)
        except Exception:
            page = 1
        num_pages = paginator.num_pages
        if page > num_pages or page <= 0:
            page = 1
        # 获取当前页的Page实例对象
        order_page = paginator.page(page)
        print('总页数：',num_pages,'当前页：',order_page.number)

        if num_pages < 5:
            pages = range(1, num_pages+1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        context = {
            'order_page': order_page,
            'pages': pages,
            'page': 'order',
        }
        print(pages)
        return render(request, 'user_center_order.html', context)


# /user/address
class AddressView(LoginRequiredMixin, View):
    """用户中心-地址页"""

    def get(self, request):
        """显示"""
        user = request.user
        address = Address.objects.get_default_address(user)
        return render(request, 'user_center_site.html',
                      {'title': '用户中心-收货地址', 'page': 'address', 'address': address})

    def post(self, request):
        # 地址添加
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        user = request.user
        address = Address.objects.get_default_address(user)

        if address:
            is_default = False
        else:
            is_default = True

        # 数据校验
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html',
                          {'page': 'address',
                           'address': address,
                           'errmsg': '数据不完整'})

        # 校验手机号
        if not re.match(r'^1([3-8][0-9]|5[189]|8[6789])[0-9]{8}$', phone):
            return render(request, 'user_center_site.html',
                          {'page': 'address',
                           'address': address,
                           'errmsg': '手机号格式不合法'})

        # 添加
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)

        # 返回应答
        return redirect(reverse('user:address'))  # get的请求方式

