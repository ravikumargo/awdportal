# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0002_awardacceptance_new_funding'),
    ]

    operations = [
        migrations.AddField(
            model_name='awardmodification',
            name='date_wait_for_updated',
            field=models.DateTimeField(null=True, verbose_name=b'Date Wait for Updated', blank=True),
        ),
    ]
