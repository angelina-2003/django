# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0007_profile_clove_count_profile_golden_heart_count_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='message_color',
            field=models.CharField(blank=True, default='#4a3a6f', max_length=7),
        ),
    ]
