from django.db import migrations


def reorder_categories(apps, schema_editor):
    AdCategory = apps.get_model('core', 'AdCategory')
    AdCategory.objects.filter(key='real_estate').update(order=17)
    AdCategory.objects.filter(key='rentals').update(order=18)
    AdCategory.objects.filter(key='cars').update(order=19)
    AdCategory.objects.filter(key='other').update(order=99)


def reverse_reorder(apps, schema_editor):
    AdCategory = apps.get_model('core', 'AdCategory')
    AdCategory.objects.filter(key='other').update(order=17)
    AdCategory.objects.filter(key='real_estate').update(order=18)
    AdCategory.objects.filter(key='rentals').update(order=19)
    AdCategory.objects.filter(key='cars').update(order=20)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0030_ad_is_auto_approved'),
    ]

    operations = [
        migrations.RunPython(reorder_categories, reverse_code=reverse_reorder),
    ]
