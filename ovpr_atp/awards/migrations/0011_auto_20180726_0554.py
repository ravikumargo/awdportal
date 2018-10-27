# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0010_auto_20180726_0335'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='award',
            index_together=set([('id', 'status')]),
        ),
    ]
