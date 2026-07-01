from django.db import models


class ReportType(models.Model):
    name = models.CharField('نام نوع گزارش', max_length=200)
    name_en = models.CharField('نام انگلیسی', max_length=200, blank=True)
    code = models.CharField('کد', max_length=50, unique=True)
    color_hex = models.CharField('رنگ', max_length=7, default='#00ff88')
    icon = models.CharField('آیکون', max_length=50, blank=True)

    class Meta:
        verbose_name = 'نوع گزارش'
        verbose_name_plural = 'انواع گزارش'
        ordering = ['name']

    def __str__(self):
        return self.name