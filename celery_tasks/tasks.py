from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
from django.template import loader

# django环境的初始化，在任务处理者worker一端加以下几句
import os

# import django
# # os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leyton_mall.settings')
# # django.setup()

from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner

# 创建一个Celery的实例对象
app = Celery('celery_tasks.tasks', broker=settings.REDIS_CONFIG)


# 定义任务函数
@app.task
def send_register_active_email(to_mail, username, token):
    """发送激活邮件"""
    subject = 'Leyton商城欢迎信息'
    message = '您的浏览器不支持此消息类型，请更换浏览器'
    html_message = message = '<h1>尊敬的{0},欢迎您注册Leyton商城会员</h1>请点击下面链接激活您的账户<br/>' \
                             '<a href="http://yldatomic.cn:8000/user/active/{1}">' \
                             'http://yldatomic.cn:8000/user/active/{2}</a>'.format(username, token, token)
    sender = settings.EMAIL_FROM
    receiver = [to_mail]
    send_mail(subject, message, sender, receiver, html_message=html_message)
    print('执行了发邮件的任务')


@app.task
def generate_static_index_html():
    """产生首页静态页面"""
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
        # 组织上下文
    context = {
        'types': types,
        'goods_banners': index_banner,
        'promotion_banners': promotion_banner,
    }

    # 使用模板
    temp = loader.get_template('static_index.html')
    static_index_html = temp.render(context)

    # 生成首页对应静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static_page/index.html')
    with open(save_path, 'w') as f:
        f.write(static_index_html)
    print("执行了生成静态页面任务")

