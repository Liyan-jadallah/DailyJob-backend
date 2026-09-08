from django.db import migrations


def add_new_categories(apps, schema_editor):
    AdCategory = apps.get_model('core', 'AdCategory')

    new_categories = [
        {'key': 'real_estate', 'label_ar': 'عقارات',  'label_en': 'Real Estate', 'icon_name': 'apartment',      'order': 18},
        {'key': 'rentals',     'label_ar': 'إيجار',   'label_en': 'Rentals',     'icon_name': 'vpn_key',         'order': 19},
        {'key': 'cars',        'label_ar': 'سيارات',  'label_en': 'Cars',        'icon_name': 'directions_car',  'order': 20},
    ]

    for cat in new_categories:
        AdCategory.objects.get_or_create(
            key=cat['key'],
            defaults={
                'label_ar':  cat['label_ar'],
                'label_en':  cat['label_en'],
                'icon_name': cat['icon_name'],
                'is_active': True,
                'order':     cat['order'],
            }
        )


def remove_new_categories(apps, schema_editor):
    AdCategory = apps.get_model('core', 'AdCategory')
    AdCategory.objects.filter(key__in=['real_estate', 'rentals', 'cars']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_add_welcome_coupon_record'),
    ]

    operations = [
        migrations.RunPython(add_new_categories, reverse_code=remove_new_categories),
    ]
