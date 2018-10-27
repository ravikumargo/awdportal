# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0008_auto_20180613_0300'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='award',
            name='award_text',
        ),
        migrations.RemoveField(
            model_name='awardacceptance',
            name='award_text',
        ),
        migrations.RemoveField(
            model_name='awardacceptance',
            name='new_funding',
        ),
        migrations.RemoveField(
            model_name='awardmodification',
            name='date_wait_for_updated',
        ),
        migrations.RemoveField(
            model_name='awardmodification',
            name='wait_for_reson',
        ),
        migrations.RemoveField(
            model_name='awardnegotiation',
            name='award_text',
        ),
        migrations.RemoveField(
            model_name='awardsetup',
            name='date_wait_for_updated',
        ),
        migrations.RemoveField(
            model_name='awardsetup',
            name='wait_for_reson',
        ),
        migrations.RemoveField(
            model_name='proposalintake',
            name='department',
        ),
        migrations.AlterField(
            model_name='award',
            name='status',
            field=models.IntegerField(default=0, db_index=True, choices=[(0, b'New'), (1, b'Award Intake'), (2, b'Award Negotiation'), (3, b'Award Setup'), (4, b'Subaward & Award Management'), (5, b'Award Closeout'), (6, b'Complete')]),
        ),
        migrations.AlterField(
            model_name='awardnegotiation',
            name='negotiation_status',
            field=models.CharField(blank=True, max_length=3, verbose_name=b'Negotiation Status', choices=[(b'IQ', b'In queue'), (b'IP', b'In progress'), (b'WFS', b'Waiting for sponsor'), (b'WFP', b'Waiting for PI'), (b'WFO', b'Waiting for other department'), (b'CD', b'Completed'), (b'UD', b'Unrealized')]),
        ),
        migrations.AlterField(
            model_name='proposalintake',
            name='spa1',
            field=models.CharField(max_length=150, null=True, verbose_name=b'SPA I'),
        ),
    ]
