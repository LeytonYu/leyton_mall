from django.contrib import admin
from .models import GoodsType, IndexPromotionBanner, IndexTypeGoodsBanner, IndexGoodsBanner, GoodsSKU, Goods
from django.core.cache import cache

# Register your models here.


class BaseModel(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()
        cache.delete('index_page_data')

class GoodsTypeAdmin(BaseModel):
    pass


class IndexPromotionBannerAdmin(BaseModel):
    pass


class IndexTypeGoodsBannerAdmin(BaseModel):
    pass


class IndexGoodsBannerAdmin(BaseModel):
    pass


admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(GoodsSKU)
admin.site.register(Goods)