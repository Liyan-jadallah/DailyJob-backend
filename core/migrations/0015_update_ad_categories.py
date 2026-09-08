from django.db import migrations

def update_categories(apps, schema_editor):
    AdCategory = apps.get_model('core', 'AdCategory')
    # Clear existing categories
    AdCategory.objects.all().delete()
    
    # Define new categories matching the website's categories and order
    categories = [
        {'key': 'daily', 'label_ar': 'عمل يومي', 'label_en': 'Daily Jobs', 'icon_name': 'bolt', 'order': 1},
        {'key': 'fulltime', 'label_ar': 'وظائف دوام كامل', 'label_en': 'Full-Time Jobs', 'icon_name': 'work', 'order': 2},
        {'key': 'ads', 'label_ar': 'إعلانات وأخبار', 'label_en': 'Ads & News', 'icon_name': 'campaign', 'order': 3},
        {'key': 'services', 'label_ar': 'خدمات', 'label_en': 'Services', 'icon_name': 'handshake', 'order': 4},
        {'key': 'construction', 'label_ar': 'أعمال بناء', 'label_en': 'Construction & Building', 'icon_name': 'build', 'order': 5},
        {'key': 'delivery', 'label_ar': 'توصيل', 'label_en': 'Delivery & Courier', 'icon_name': 'local_shipping', 'order': 6},
        {'key': 'cleaning', 'label_ar': 'نظافة', 'label_en': 'Housekeeping & Cleaning', 'icon_name': 'cleaning_services', 'order': 7},
        {'key': 'moving', 'label_ar': 'نقل وأثاث', 'label_en': 'Moving & Packing', 'icon_name': 'local_mall', 'order': 8},
        {'key': 'plumbing', 'label_ar': 'سباكة وتدفئة', 'label_en': 'Plumbing & Heating', 'icon_name': 'plumbing', 'order': 9},
        {'key': 'electrical', 'label_ar': 'كهرباء', 'label_en': 'Electrical Work', 'icon_name': 'electrical_services', 'order': 10},
        {'key': 'hospitality', 'label_ar': 'ضيافة ومطاعم', 'label_en': 'Restaurants & Catering', 'icon_name': 'restaurant', 'order': 11},
        {'key': 'caregiving', 'label_ar': 'رعاية أطفال', 'label_en': 'Babysitting & Care', 'icon_name': 'child_care', 'order': 12},
        {'key': 'used', 'label_ar': 'أشياء مستعملة', 'label_en': 'Used Items', 'icon_name': 'sell', 'order': 13},
        {'key': 'electronics', 'label_ar': 'إلكترونيات مستعملة', 'label_en': 'Used Electronics', 'icon_name': 'devices', 'order': 14},
        {'key': 'furniture', 'label_ar': 'أثاث مستعمل', 'label_en': 'Used Furniture', 'icon_name': 'chair', 'order': 15},
        {'key': 'free', 'label_ar': 'هدايا مجانية', 'label_en': 'Freebies', 'icon_name': 'card_giftcard', 'order': 16},
        {'key': 'other', 'label_ar': 'أخرى', 'label_en': 'Other', 'icon_name': 'more_horiz', 'order': 17},
    ]
    
    for cat in categories:
        AdCategory.objects.create(
            key=cat['key'],
            label_ar=cat['label_ar'],
            label_en=cat['label_en'],
            icon_name=cat['icon_name'],
            is_active=True,
            order=cat['order']
        )

def reverse_categories(apps, schema_editor):
    AdCategory = apps.get_model('core', 'AdCategory')
    AdCategory.objects.all().delete()
    
    # Restore original seeded categories
    categories = [
        {'key': 'daily', 'label_ar': 'شغل يومي', 'label_en': 'Daily Work', 'icon_name': 'bolt', 'order': 1},
        {'key': 'fulltime', 'label_ar': 'دوام كامل', 'label_en': 'Full Time', 'icon_name': 'work', 'order': 2},
        {'key': 'used', 'label_ar': 'مستعمل', 'label_en': 'Used Items', 'icon_name': 'sell', 'order': 3},
        {'key': 'free', 'label_ar': 'مجاناً', 'label_en': 'Free', 'icon_name': 'card_giftcard', 'order': 4},
        {'key': 'services', 'label_ar': 'خدمات', 'label_en': 'Services', 'icon_name': 'handshake', 'order': 5},
        {'key': 'ads', 'label_ar': 'إعلان عام', 'label_en': 'General Ad', 'icon_name': 'campaign', 'order': 6},
        {'key': 'rental', 'label_ar': 'إيجار', 'label_en': 'Rental', 'icon_name': 'home_outlined', 'order': 7},
    ]
    
    for cat in categories:
        AdCategory.objects.create(
            key=cat['key'],
            label_ar=cat['label_ar'],
            label_en=cat['label_en'],
            icon_name=cat['icon_name'],
            is_active=True,
            order=cat['order']
        )

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_alter_user_username'),
    ]

    operations = [
        migrations.RunPython(update_categories, reverse_code=reverse_categories),
    ]
