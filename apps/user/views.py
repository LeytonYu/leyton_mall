from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.http import HttpResponse, JsonResponse, QueryDict
from django.views.decorators.csrf import csrf_exempt
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
from django.db.models import Q


# Create your views here.

# /user/name_check
@csrf_exempt
def name_check(request):
    """注册校验用户名是否重复"""
    if len(User.objects.filter(username=request.POST.get('name'))) == 0:
        return JsonResponse({'resultCode': 0})  # 没重复
    return JsonResponse({'resultCode': 1})


# /user/email_check
@csrf_exempt
def email_check(request):
    if len(User.objects.filter(email=request.POST.get('email'))) == 0:
        return JsonResponse({'resultCode': 0})  # 没重复
    return JsonResponse({'resultCode': 1})


# /user/register
class RegisterView(View):
    """注册"""

    def get(self, request):
        """显示注册页"""
        return render(request, 'register.html')

    def post(self, request):
        """经行注册处理"""
        print("提交注册请求")
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

        user = User.objects.filter(Q(username=username) | Q(email=username))
        if user:
            user = user[0]
            password2 = user.password
            if check_password(password, password2):
                if user.is_active:
                    print("用户激活了")
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
                    print("用户没激活")
                    return render(request, 'login.html', {'errmsg': '账户未激活'})
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})
        else:
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
        print('总页数：', num_pages, '当前页：', order_page.number)

        if num_pages < 5:
            pages = range(1, num_pages + 1)
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
        address_all = Address.objects.get_all_address(user)
        count = len(address_all)
        context = {
            'title': '用户中心-收货地址',
            'page': 'address',
            'address': address,
            'count': count,
            'address_all': address_all,
        }
        return render(request, 'user_center_site.html', context)

    def post(self, request):
        """地址添加"""
        receiver = request.POST.get('receiver')
        province = request.POST.get('province', '浙江省')
        city = request.POST.get('city', '绍兴市')
        area = request.POST.get('area', '诸暨市')
        print(province, city, area)
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
            return JsonResponse({'message': '数据不完整'})

        # 校验手机号
        if not re.match(r'^1([3-8][0-9]|5[189]|8[6789])[0-9]{8}$', phone):
            return JsonResponse({'message': '手机号格式不合法'})
        phone = int(phone)
        if zip_code == '':
            zip_code = None
        if zip_code:
            try:
                zip_code = int(zip_code)
            except:
                return JsonResponse({'message': '邮编格式不合法'})
        # 添加
        Address.objects.create(user=user,
                               receiver=receiver,
                               province=province,
                               city=city,
                               area=area,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)

        # 返回应答
        return JsonResponse({'message': 'success'})
        # return redirect(reverse('user:address'))  # get的请求方式

    @method_decorator(csrf_exempt)
    def put(self, request):
        """修改地址"""
        querydict = QueryDict(request.body)
        id = int(querydict.get('id'))
        receiver = querydict.get('receiver')
        province = querydict.get('province', '浙江省')
        city = querydict.get('city', '绍兴市')
        area = querydict.get('area', '诸暨市')
        addr = querydict.get('addr')
        try:
            zip_code = int(querydict.get('zip_code'))
        except Exception:
            zip_code = None
        phone = int(querydict.get('phone'))
        if Address.objects.update_address(id, receiver, province, city, area, addr,
                                          zip_code, phone):
            return JsonResponse({'message': 'success'})
        else:
            return JsonResponse({'message': '修改失败'})

    def delete(self, request):
        """删除地址"""
        DELETE = QueryDict(request.body)
        id = eval(list(dict(DELETE.lists()).keys())[0])['id']
        if Address.objects.del_address(id):
            return JsonResponse({'message': 'success'})
        else:
            return JsonResponse({'message': '删除失败'})


def set_default_addr(request):
    """设置默认地址"""
    id = int(request.POST.get('id'))
    user = request.user
    if Address.objects.set_default(user, id):
        return JsonResponse({'message': 'success'})
    else:
        return JsonResponse({'message': '更改失败'})
