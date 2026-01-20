# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0003_alter_message_chat_group_message_group_groupmember_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('chat', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='favorited_by', to='home.privatechat')),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='favorited_by', to='home.group')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'chat'), ('user', 'group')},
            },
        ),
    ]
