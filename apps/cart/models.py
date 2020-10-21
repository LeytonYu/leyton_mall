from django.db import models


# Create your models here.
class FuckYou(models.Model):
    name = models.CharField('名字', max_length=100)

    class Meta:
        verbose_name_plural = verbose_name = 'lm_fucku'
