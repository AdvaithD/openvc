# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-17 09:00
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0008_auto_20170216_0215'),
    ]

    operations = [
        migrations.CreateModel(
            name='Metric',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('date', models.DateField()),
                ('interval', models.TextField(blank=True, default=b'Quarter', null=True)),
                ('estimated', models.NullBooleanField(default=False)),
                ('value', models.FloatField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='metrics', to='data.Company')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='metric',
            unique_together=set([('company', 'name', 'date', 'interval', 'estimated')]),
        ),
    ]
