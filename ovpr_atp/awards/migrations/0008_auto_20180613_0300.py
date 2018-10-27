# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0007_auto_20180612_0905'),
    ]

    operations = [
        migrations.RenameField(
            model_name='awardacceptance',
            old_name='award_acceptance_text',
            new_name='award_text',
        ),
        migrations.RenameField(
            model_name='awardnegotiation',
            old_name='award_negotiation_text',
            new_name='award_text',
        ),
    ]
