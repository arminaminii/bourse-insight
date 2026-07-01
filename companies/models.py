from django.db import models


class Sector(models.Model):
    name = models.CharField('نام صنعت', max_length=200)
    name_en = models.CharField('نام انگلیسی', max_length=200, blank=True)
    code = models.CharField('کد صنعت', max_length=50, unique=True)
    is_active = models.BooleanField('فعال', default=True)

    class Meta:
        verbose_name = 'صنعت'
        verbose_name_plural = 'صنایع'
        ordering = ['name']

    def __str__(self):
        return self.name

    def company_count(self):
        return self.companies.filter(is_active=True).count()


class Company(models.Model):
    COMPANY_TYPE_CHOICES = [
        ('بورس', 'بورس'),
        ('فرابورس', 'فرابورس'),
        ('پایه', 'پایه فرابورس'),
    ]

    name = models.CharField('نام شرکت', max_length=300)
    symbol = models.CharField('نماد', max_length=50, unique=True)
    name_en = models.CharField('نام انگلیسی', max_length=300, blank=True)
    sector = models.ForeignKey(
        Sector,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='companies',
        verbose_name='صنعت',
    )
    company_type = models.CharField(
        'نوع بازار',
        max_length=20,
        choices=COMPANY_TYPE_CHOICES,
        blank=True,
        default='بورس',
    )
    isin = models.CharField('کد ISIN', max_length=20, blank=True)
    tsetmc_code = models.CharField('کد تسنیم', max_length=20, blank=True)
    codal_url = models.URLField('آدرس کدال', blank=True)
    is_active = models.BooleanField('فعال', default=True)
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('تاریخ بروزرسانی', auto_now=True)

    class Meta:
        verbose_name = 'شرکت'
        verbose_name_plural = 'شرکت‌ها'
        ordering = ['symbol']

    def __str__(self):
        return f"{self.symbol} - {self.name}"

    def get_codal_url(self):
        if self.codal_url:
            return self.codal_url
        return f"https://codal.ir/ReportList.aspx?search&Symbol={self.symbol}"