# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0005_auto_20180531_0614'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposalintake',
            name='department',
            field=models.ForeignKey(verbose_name=b'Department', blank=True, to='awards.AwardOrganization', null=True),
        ),
    ]
