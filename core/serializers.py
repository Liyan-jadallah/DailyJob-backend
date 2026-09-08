from rest_framework import serializers
from .models import User, PaymentMethod, Ad, AdCategory, AdImage, Transaction, Notification, Coupon, Referral, ContactMessage
from .minimal_user_serializer import MinimalUserSerializer

class AdCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdCategory
        fields = ['id', 'key', 'label_ar', 'label_en', 'icon_name', 'order']


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    referred_by_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name', 'phone_number', 'role', 'referral_code', 'referred_by_code', 'date_joined', 'device_id', 'fcm_token']
        read_only_fields = ['id', 'date_joined', 'role', 'referral_code']

    def validate_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        if not value or len(value) < 6:
            raise serializers.ValidationError("كلمة المرور يجب أن تكون 6 خانات على الأقل.")
        try:
            validate_password(value)
        except Exception as e:
            error_messages = e.messages if hasattr(e, 'messages') else [str(e)]
            raise serializers.ValidationError(" ".join(error_messages))
        return value

    def create(self, validated_data):
        referred_by_code = validated_data.pop('referred_by_code', None)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            phone_number=validated_data.get('phone_number', ''),
            device_id=validated_data.get('device_id', ''),
            fcm_token=validated_data.get('fcm_token', '')
        )
        if referred_by_code:
            referrer = User.objects.filter(referral_code=referred_by_code.strip().upper()).first()
            if referrer:
                Referral.objects.create(referrer=referrer, referred=user)
        return user

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'

class AdImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    class Meta:
        model = AdImage
        fields = ['id', 'image']

class AdSerializer(serializers.ModelSerializer):
    # تفاصيل المستخدم مختصرة
    user_details = MinimalUserSerializer(source='user', read_only=True)

    # السطر الجديد: جلب إيميل صاحب الإعلان مباشرة لزر الحذف
    user_email = serializers.ReadOnlyField(source='user.email')

    # الصور الإضافية
    extra_images = AdImageSerializer(many=True, read_only=True)

    # الصورة الرئيسية للإعلان كـ absolute URL
    image = serializers.SerializerMethodField()

    # صورة الوصل من Transaction
    receipt_image = serializers.SerializerMethodField()

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        
        # Fallback to the first extra image if main image is not set
        first_extra = obj.extra_images.first()
        if first_extra and first_extra.image:
            if request:
                return request.build_absolute_uri(first_extra.image.url)
            return first_extra.image.url
            
        return None

    def validate_category(self, value):
        if value and value != 'all':
            from .models import AdCategory
            if not AdCategory.objects.filter(key=value, is_active=True).exists():
                import logging
                logging.getLogger(__name__).warning(f"Category '{value}' not found in AdCategory table")
        return value

    def get_receipt_image(self, obj):
        tx = obj.transactions.order_by('-submitted_at').first()
        if tx and tx.receipt_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(tx.receipt_image.url)
            return tx.receipt_image.url
        return None

    class Meta:
        model = Ad
        fields = ['id', 'user', 'user_details', 'user_email', 'title', 'description', 'category', 'ad_type', 'governorate', 'price', 'contact_phone', 'contact_method', 'ad_duration', 'image', 'extra_images', 'receipt_image', 'status', 'views', 'created_at', 'approved_at']
        read_only_fields = ['id', 'created_at', 'approved_at', 'user', 'views']

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        # status قابل للتعديل فقط من الأدمن
        is_admin = getattr(getattr(request, 'user', None), 'role', None) == 'admin'
        if not is_admin:
            fields['status'].read_only = True
        return fields

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['id', 'submitted_at', 'status', 'user']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'title', 'message', 'ad_id', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']

class CouponSerializer(serializers.ModelSerializer):
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = ['id', 'code', 'coupon_type', 'is_used', 'used_at', 'created_at', 'expires_at', 'is_expired']

    def get_is_expired(self, obj):
        return obj.is_expired()


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'is_resolved', 'created_at']
        read_only_fields = ['id', 'is_resolved', 'created_at']
