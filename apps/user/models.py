from django.db import models
from django.contrib.auth.models import AbstractUser
from db.base_model import BaseModel


# Create your models here.

class User(AbstractUser, BaseModel):
    """用户模型类"""

    class Meta:
        db_table = 'lm_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name


class AddressManager(models.Manager):
    """地址模型管理器类"""
    def get_default_address(self, user):
        # 获取用户的默认收货地址
        try:
            address = self.get(user=user, is_default=True)
        except self.model.DoesNotExist:
            address = None  # 不存在默认地址

        return address

    def get_all_address(self, user):
        """获取用户的所有收货地址"""
        address = self.filter(user=user)
        return address

    def update_address(self, id, receiver, province, city, area, addr,
                                          zip_code, phone):
        """修改用户的收货地址"""
        try:
            address = self.get(id=id)
            address.receiver = receiver
            address.province = province
            address.city = city
            address.area = area
            address.addr = addr
            address.zip_code = zip_code
            address.phone = phone
            address.save()
            return True
        except:
            return False

    def del_address(self, id):
        """删除地址"""
        return  self.filter(id=id).delete()

    def set_default(self, user, id):
        """设置默认地址"""
        try:
            address2 = self.get(user=user, is_default=True)
            address2.is_default = False
            address2.save()
        except Exception:
            pass

        try:
            address = self.get(id=id)
            address.is_default = True
        except Exception:
            return False


        address.save()
        return True


class Address(BaseModel):
    """地址模型类"""
    user = models.ForeignKey('User', on_delete=models.CASCADE, verbose_name='所属账户')
    receiver = models.CharField(max_length=20, verbose_name='收件人')
    province = models.CharField(max_length=20, verbose_name='省')
    city = models.CharField(max_length=20, verbose_name='市')
    area = models.CharField(max_length=20, verbose_name='区')
    addr = models.CharField(max_length=256, verbose_name='收件地址')
    zip_code = models.IntegerField(null=True, verbose_name='邮政编码')
    phone = models.IntegerField(verbose_name='联系电话')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')
    # 自定义一个模型管理器类
    objects = AddressManager()

    class Meta:
        db_table = 'lm_address'
        verbose_name = '地址'
        verbose_name_plural = verbose_name
