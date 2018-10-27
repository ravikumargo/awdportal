# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0004_awardsetup_date_wait_for_updated'),
    ]

    operations = [
        migrations.AddField(
            model_name='awardmodification',
            name='wait_for_reson',
            field=models.CharField(blank=True, max_length=2, verbose_name=b'Wait for', choices=[(b'RB', b'Revised Budget'), (b'PA', b'PI Access'), (b'CA', b'Cost Share Approval'), (b'FC', b'FCOI'), (b'PS', b'Proposal Submission'), (b'SC', b'Sponsor Clarity'), (b'NO', b'New Org needed'), (b'IC', b'Internal Clarification'), (b'DC', b'Documents not in GW Docs')]),
        ),
        migrations.AddField(
            model_name='awardsetup',
            name='wait_for_reson',
            field=models.CharField(blank=True, max_length=2, verbose_name=b'Wait for', choices=[(b'RB', b'Revised Budget'), (b'PA', b'PI Access'), (b'CA', b'Cost Share Approval'), (b'FC', b'FCOI'), (b'PS', b'Proposal Submission'), (b'SC', b'Sponsor Clarity'), (b'NO', b'New Org needed'), (b'IC', b'Internal Clarification'), (b'DC', b'Documents not in GW Docs')]),
        ),
    ]
