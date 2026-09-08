from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_adimage'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text="e.g. 'daily', 'fulltime', 'used'", max_length=50, unique=True)),
                ('label_ar', models.CharField(help_text='Arabic label shown in app/website', max_length=100)),
                ('label_en', models.CharField(help_text='English label shown in app/website', max_length=100)),
                ('icon_name', models.CharField(default='label', help_text='Material icon name (for reference)', max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0, help_text='Display order (lower = first)')),
            ],
            options={
                'db_table': 'ad_categories',
                'ordering': ['order', 'key'],
            },
        ),
        # Seed default categories so the app works immediately after migration
        migrations.RunSQL(
            sql="""
            INSERT INTO ad_categories (key, label_ar, label_en, icon_name, is_active, "order") VALUES
                ('daily',    'شغل يومي',    'Daily Work',   'bolt',              true, 1),
                ('fulltime', 'دوام كامل',   'Full Time',    'work',              true, 2),
                ('used',     'مستعمل',      'Used Items',   'sell',              true, 3),
                ('free',     'مجاناً',      'Free',         'card_giftcard',     true, 4),
                ('services', 'خدمات',       'Services',     'handshake',         true, 5),
                ('ads',      'إعلان عام',   'General Ad',   'campaign',          true, 6),
                ('rental',   'إيجار',       'Rental',       'home_outlined',     true, 7)
            ON CONFLICT (key) DO NOTHING;
            """,
            reverse_sql="DELETE FROM ad_categories WHERE key IN ('daily','fulltime','used','free','services','ads','rental');",
        ),
    ]
