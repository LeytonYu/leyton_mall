from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from django_redis import get_redis_connection

from apps.goods.models import GoodsSKU


# Create your views here.

# /cart/add
class CartAddView(View):
    """购物车记录添加"""

    def post(self, request):
        """购物车记录添加"""
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            count += int(cart_count)

        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        conn.hset(cart_key, sku_id, count)
        cart_count = conn.hlen(cart_key)
        return JsonResponse({'res': 5, 'message': '添加成功', 'cart_count': cart_count})

# /cart/
class CartInfoView(LoginRequiredMixin, View):
    """获取购物车"""

    def get(self, request):
        """获取购物车"""
        user = request.user
        cart_key = 'cart_%d' % user.id
        conn = get_redis_connection('default')
        cart_dict = conn.hgetall(cart_key)
        cart_count = 0
        cart_price = 0
        skus = []
        for sku_id, count in cart_dict.items():
            sku = GoodsSKU.objects.get(id=sku_id)
            sku.amount = sku.price * int(count)
            sku.count = int(count)
            skus.append(sku)
            cart_count += int(count)
            cart_price += sku.amount

        context = {'cart_count': cart_count,
                   'cart_price': cart_price,
                   'skus': skus}
        return render(request, 'cart/cart.html', context)

# /cart/update
class CartUpdateView(View):
    """更新单件商品购物车数量"""
    def post(self,request):
        user=request.user
        if not user.is_authenticated:
            return JsonResponse({'res':0,'errmsg':'请先登录'})
        sku_id=request.POST.get('sku_id')
        count=request.POST.get('count')
        print('商品id',sku_id,'商品数量',count)
        if not all([sku_id,count]):
            return JsonResponse({'res':1,'errmsg':'数据不完整'})
        try:
            count=int(count)
        except Exception:
            return JsonResponse({'res':2,'errmsg':'商品数目出错'})

        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except Exception:
            return JsonResponse({'res':3,'errmsg':'商品不存在'})

        if count>sku.stock:
            return JsonResponse({'res':4,'errmsg':'商品库存不足'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        conn.hset(cart_key,sku_id,count)
        cart_count=0
        vals=conn.hvals(cart_key)
        for val in vals:
            cart_count+=int(val)
        # print(cart_count)
        return JsonResponse({'res':5,'cart_count':cart_count,'message':'更新成功'})


# /cart/delete
class CartDeleteView(View):
    """购物车记录删除"""
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        sku_id = request.POST.get('sku_id')
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的商品'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

        # 业务处理: 删除购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # 删除 hdel
        conn.hdel(cart_key, sku_id)
        cart_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            cart_count += int(val)

        return JsonResponse({'res': 3, 'cart_count': cart_count, 'message': '删除成功'})