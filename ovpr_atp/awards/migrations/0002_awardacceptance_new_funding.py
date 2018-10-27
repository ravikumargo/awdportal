# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='awardacceptance',
            name='new_funding',
            field=models.NullBooleanField(verbose_name=b'New Funding?'),
        ),
    ]
