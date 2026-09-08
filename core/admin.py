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
    list_display = ('title', 'user', 'category', 'status', 'image_preview', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('title', 'description', 'user__email')
    readonly_fields = ('image_preview',)
    inlines = [AdImageInline]

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:120px; border-radius:6px;" />', obj.image.url)
        return "لا توجد صورة"
    image_preview.short_description = "الصورة الرئيسية"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'ad', 'amount', 'status', 'receipt_preview', 'submitted_at')
    list_filter = ('status',)
    search_fields = ('user__email', 'ad__title')
    readonly_fields = ('receipt_preview',)

    def receipt_preview(self, obj):
        if obj.receipt_image:
            return format_html('<img src="{}" style="max-height:120px; border-radius:6px;" />', obj.receipt_image.url)
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
