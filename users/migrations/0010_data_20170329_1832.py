# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-29 18:32
from __future__ import unicode_literals

from django.db import migrations, models

def migrate_opportunities(apps, schema_editor):
    """
    Migrate user/account relationship off the UserAccount model.
    """

    User = apps.get_model('users', 'User')
    UserAccount = apps.get_model('users', 'UserAccount')

    print '\nUpdating User Account reference'
    for user in User.objects.all():
        try:
            user.account = user.user_accounts.get(active=True).account
            user.save()
        except UserAccount.DoesNotExist:
            # Consider setting to default account instead. Doing this for now
            # because the account with id 1 is currently tied to a non-default
            # company (Mixpanel).
            user.delete()
    print 'Done'

def reverse_migrate_opportunities(apps, schema_editor):
    """
    Reverse above migration.
    """
    User = apps.get_model('users', 'User')
    Account = apps.get_model('users', 'Account')
    UserAccount = apps.get_model('users', 'UserAccount')

    print '\nUpdating User Account reference'
    for user in User.objects.all():
        account = user.account
        UserAccount.objects.create(user=user, account=account, active=True)
    print 'Done'

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_auto_20170329_1815'),
    ]

    operations = [
        migrations.RunPython(migrate_opportunities,
                             reverse_migrate_opportunities),
    ]
