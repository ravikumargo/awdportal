# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0009_auto_20180726_0321'),
    ]

    operations = [
        migrations.AlterField(
            model_name='award',
            name='status',
            field=models.IntegerField(default=0, choices=[(0, b'New'), (1, b'Award Intake'), (2, b'Award Negotiation'), (3, b'Award Setup'), (4, b'Subaward & Award Management'), (5, b'Award Closeout'), (6, b'Complete')]),
        ),
    ]
