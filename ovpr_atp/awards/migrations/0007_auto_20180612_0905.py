# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0006_proposalintake_department'),
    ]

    operations = [
        migrations.AddField(
            model_name='award',
            name='award_text',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='awardacceptance',
            name='award_acceptance_text',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='awardnegotiation',
            name='award_negotiation_text',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
    ]
