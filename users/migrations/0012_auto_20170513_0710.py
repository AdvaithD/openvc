# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-13 07:10
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_auto_20170329_1835'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='company',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='company_account', to='data.Company'),
        ),
    ]
