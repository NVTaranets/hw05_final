# Generated by Django 2.2.16 on 2021-12-20 13:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0009_follow'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='follow',
            name='pub_date',
        ),
    ]
