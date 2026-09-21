from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, PaymentMethod, Ad, AdCategory, AdImage, Transaction, Notification, Coupon, Referral

# Register custom user model
admin.site.register(User, UserAdmin)

@admin.register(AdCategory)
class AdCategoryAdmin(admin.ModelAdmin):
    list_display = ('key', 'label_ar', 'label_en', 'icon_name', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active',)
    search_fields = ('key', 'label_ar', 'label_en')
    ordering = ('order', 'key')


class AdImageInline(admin.TabularInline):
    model = AdImage
    extra = 0
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:120px; border-radius:6px;" />', obj.image.url)
        return "لا توجد صورة"
    image_preview.short_description = "معاينة"


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'duration_badge', 'category', 'status', 'image_preview', 'created_at')
    list_filter = ('ad_duration', 'status', 'category')
    search_fields = ('title', 'description', 'user__email', 'user__username')
    readonly_fields = ('image_preview',)
    inlines = [AdImageInline]

    def duration_badge(self, obj):
        if obj.ad_duration == '1_week':
            return format_html('<span style="background-color:#EDE7F6; color:#512DA8; font-weight:bold; padding:3px 8px; border-radius:4px;">أسبوع (2 د.أ)</span>')
        return format_html('<span style="background-color:#E3F2FD; color:#1565C0; font-weight:bold; padding:3px 8px; border-radius:4px;">يوم (1 د.أ)</span>')
    duration_badge.short_description = "المدة المطلوبة"
    duration_badge.admin_order_field = 'ad_duration'

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:120px; border-radius:6px;" />', obj.image.url)
        return "لا توجد صورة"
    image_preview.short_description = "الصورة الرئيسية"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'get_ad_title', 'amount', 'status', 'receipt_preview', 'submitted_at')
    list_filter = ('status', 'submitted_at')
    search_fields = ('user__email', 'user__username', 'ad_title', 'ad__title')
    readonly_fields = ('receipt_preview',)

    def get_ad_title(self, obj):
        title = obj.ad_title or (obj.ad.title if obj.ad else 'إعلان محذوف')
        if obj.ad:
            return format_html('<span style="color:#2E9E5B; font-weight:600;">{}</span>', title)
        return format_html('<span style="color:#7A8099;">{} <em style="font-size:11px;">(محذوف)</em></span>', title)
    get_ad_title.short_description = "عنوان الإعلان"

    def receipt_preview(self, obj):
        if obj.receipt_image:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="max-height:120px; border-radius:6px;" /></a>', obj.receipt_image.url, obj.receipt_image.url)
        return "لا يوجد إيصال"
    receipt_preview.short_description = "إيصال الدفع"

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('method_name', 'account_alias', 'is_active')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read',)

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'user', 'coupon_type', 'is_used', 'expires_at')
    list_filter = ('coupon_type', 'is_used')
    search_fields = ('code', 'user__email', 'user__username')

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'referred', 'created_at')
    search_fields = ('referrer__email', 'referred__email')
