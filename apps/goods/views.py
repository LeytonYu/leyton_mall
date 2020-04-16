from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View

from apps.order.models import OrderGoods
from .models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner, GoodsSKU
from django_redis import get_redis_connection
from django.core.cache import cache


# Create your views here.


class IndexView(View):
    def get(self, request):
        """展示首页"""
        # 先判断缓存中是否有数据,没有数据不会报错返回None
        context = cache.get('index_page_data')

        if context is None:
            print('缓存为空')
            # 查询商品的分类信息
            types = GoodsType.objects.all()
            # 获取首页轮播的商品的信息
            index_banner = IndexGoodsBanner.objects.all().order_by('index')
            # 获取首页促销的活动信息
            promotion_banner = IndexPromotionBanner.objects.all().order_by('index')

            # 获取首页分类商品信息展示
            for type in types:
                # 查询首页显示的type类型的文字商品信息
                title_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
                # 查询首页显示的图片商品信息
                image_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
                # 动态给type对象添加两个属性保存数据
                type.title_banner = title_banner
                type.image_banner = image_banner

            context = {
                'types': types,
                'goods_banners': index_banner,
                'promotion_banners': promotion_banner,
            }
            # cache.set(key, value, timeout=DEFAULT_TIMEOUT, version=None)
            cache.set('index_page_data', context, 3600)
        print('从redis读取缓存')
        # 获取user
        user = request.user
        # 获取登录用户的额购物车中的商品的数量
        cart_count = 0
        if user.is_authenticated:
            # 用户已经登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            # 获取用户购物车中的商品条目数
            cart_count = conn.hlen(cart_key)  # hlen hash中的数目
        # 组织上下文
        context['cart_count'] = cart_count

        return render(request, 'goods/index.html', context)


class DetailView(View):
    """详情页"""

    def get(self, request, goods_id):
        """显示详情页"""
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))

        # 获取商品的分类信息
        types = GoodsType.objects.all()
        # 获取商品的评论信息
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')

        # 获取新品推荐信息
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:3]
        # 获取同一个SPU的其他规格商品
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)
        # 获取登录用户的购物车中的商品的数量
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 用户已经登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            # 获取用户购物车中的商品条目数
            cart_count = conn.hlen(cart_key)

            conn = get_redis_connection('default')
            # 添加用户的历史记录
            history_key = 'history_%d' % user.id
            # 移除列表中的goods_id
            conn.lrem(history_key, 0, goods_id)
            # 把goods_id插入到列表的左侧
            conn.lpush(history_key, goods_id)
            # 只保存用户最新浏览的5条信息
            conn.ltrim(history_key, 0, 4)

            # 组织模版上下文
        context = {'sku': sku, 'types': types,
                   'sku_orders': sku_orders,
                   'new_skus': new_skus,
                   'same_spu_skus': same_spu_skus,
                   'cart_count': cart_count}
        return render(request, 'goods/detail.html', context)

class ListView(View):
    """列表页"""
    def get(self,request,type_id,page):
        """获取列表页详情"""
        try:
            type=GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return redirect(reverse('goods:index'))

        types = GoodsType.objects.all()

        sort = request.GET.get('sort')
        if sort=='price':
            skus = GoodsSKU.objects.filter(type=type_id).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort='default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')

        paginator = Paginator(skus,2)
        try:
            page=int(page)
        except Exception:
            page=1
        num_pages = paginator.num_pages
        if page>num_pages or page<=0:
            page =1

        skus_page=paginator.page(page)

        if num_pages<5:
            pages =range(1,num_pages+1)
        elif page<=3:
            pages= range(1,6)
        elif page>=num_pages-2:
            pages=range(num_pages-4,num_pages+1)
        else:
            pages=range(page-2,page+3)

        # 获取新品推荐信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:3]

        # 获取登录用户的额购物车中的商品的数量
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 用户已经登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id

            # 获取用户购物车中的商品条目数
            cart_count = conn.hlen(cart_key)  # hlen hash中的数目

        # 组织模版上下文
        context = {'type': type, 'types': types,
                   'sort': sort,
                   'skus_page': skus_page,
                   'new_skus': new_skus,
                   'pages': pages,
                   'cart_count': cart_count}

        return render(request, 'goods/list.html', context)

