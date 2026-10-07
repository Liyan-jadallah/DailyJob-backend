from django.db import migrations

def seed_system_settings(apps, schema_editor):
    SystemSetting = apps.get_model('core', 'SystemSetting')
    
    defaults = [
        {
            'key': 'notification_retention_days',
            'value': '7',
            'description': 'عدد أيام الاحتفاظ بالإشعارات قبل حذفها تلقائياً (مثال: 7 أو 14 أو 30 يوماً)'
        },
        {
            'key': 'ad_retention_days',
            'value': '7',
            'description': 'عدد الأيام لحذف الإعلانات المنتهية التي مر عليها أسبوع كامل (الافتراضي: 7 أيام)'
        },
        {
            'key': 'ad_auto_approve_minutes',
            'value': '10',
            'description': 'فترة سماح الموافقة التلقائية على الإعلانات بالدقائق بعد الدفع'
        }
    ]

    for item in defaults:
        SystemSetting.objects.get_or_create(
            key=item['key'],
            defaults={'value': item['value'], 'description': item['description']}
        )

def unseed_system_settings(apps, schema_editor):
    SystemSetting = apps.get_model('core', 'SystemSetting')
    SystemSetting.objects.filter(key__in=['notification_retention_days', 'ad_retention_days', 'ad_auto_approve_minutes']).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_transaction_ad_title_alter_transaction_ad'),
    ]

    operations = [
        migrations.RunPython(seed_system_settings, unseed_system_settings),
    ]
