# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0011_auto_20180726_0554'),
    ]

    operations = [
        migrations.AddField(
            model_name='award',
            name='award_text',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='awardacceptance',
            name='award_text',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='awardacceptance',
            name='new_funding',
            field=models.NullBooleanField(verbose_name=b'New Funding?'),
        ),
        migrations.AddField(
            model_name='awardmodification',
            name='date_wait_for_updated',
            field=models.DateTimeField(null=True, verbose_name=b'Date Wait for Updated', blank=True),
        ),
        migrations.AddField(
            model_name='awardmodification',
            name='wait_for_reson',
            field=models.CharField(blank=True, max_length=2, verbose_name=b'Wait for', choices=[(b'RB', b'Revised Budget'), (b'PA', b'PI Access'), (b'CA', b'Cost Share Approval'), (b'FC', b'FCOI'), (b'PS', b'Proposal Submission'), (b'SC', b'Sponsor Clarity'), (b'NO', b'New Org needed'), (b'IC', b'Internal Clarification'), (b'DC', b'Documents not in GW Docs')]),
        ),
        migrations.AddField(
            model_name='awardnegotiation',
            name='award_text',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='awardsetup',
            name='date_wait_for_updated',
            field=models.DateTimeField(null=True, verbose_name=b'Date Wait for Updated', blank=True),
        ),
        migrations.AddField(
            model_name='awardsetup',
            name='wait_for_reson',
            field=models.CharField(blank=True, max_length=2, verbose_name=b'Wait for', choices=[(b'RB', b'Revised Budget'), (b'PA', b'PI Access'), (b'CA', b'Cost Share Approval'), (b'FC', b'FCOI'), (b'PS', b'Proposal Submission'), (b'SC', b'Sponsor Clarity'), (b'NO', b'New Org needed'), (b'IC', b'Internal Clarification'), (b'DC', b'Documents not in GW Docs')]),
        ),
        migrations.AddField(
            model_name='proposalintake',
            name='department',
            field=models.ForeignKey(verbose_name=b'Department', blank=True, to='awards.AwardOrganization', null=True),
        ),
        migrations.AlterField(
            model_name='awardnegotiation',
            name='negotiation_status',
            field=models.CharField(default=b'IQ', max_length=3, verbose_name=b'Negotiation Status', blank=True, choices=[(b'IQ', b'In queue'), (b'IP', b'In progress'), (b'WFS', b'Waiting for sponsor'), (b'WFP', b'Waiting for PI'), (b'WFO', b'Waiting for other department'), (b'CD', b'Completed'), (b'UD', b'Unrealized')]),
        ),
        migrations.AlterField(
            model_name='proposalintake',
            name='spa1',
            field=models.CharField(max_length=150, null=True, verbose_name=b'SPA I*', choices=[('Aileen Miller', 'Aileen Miller'), ('Alma Starks', 'Alma Starks'), ('Anna Mansueto', 'Anna Mansueto'), ('Aquinos Butler', 'Aquinos Butler'), ('Asirinaidu Paidi', 'Asirinaidu Paidi'), ('ATP Admin', 'ATP Admin'), ('Begai Johnson', 'Begai Johnson'), ('Carolyn Harvey', 'Carolyn Harvey'), ('Catherine Summers', 'Catherine Summers'), ('Charles Maples', 'Charles Maples'), ('Chris Marchak', 'Chris Marchak'), ('Christine Kim', 'Christine Kim'), ('Dagmar Christensen', 'Dagmar Christensen'), ('Deborah Pomerantz', 'Deborah Pomerantz'), ('DIT Service', 'DIT Service'), ('Edward McKoy', 'Edward McKoy'), ('Emmett Scott', 'Emmett Scott'), ('Gina Lohr', 'Gina Lohr'), ('J. Akua Harris', 'J. Akua Harris'), ('Jamal Brooks', 'Jamal Brooks'), ('Jennifer Strickland', 'Jennifer Strickland'), ('Jennifer Liasson', 'Jennifer Liasson'), ('Jessica Harb', 'Jessica Harb'), ('Joyce Webster', 'Joyce Webster'), ('Kai-Kong Chan', 'Kai-Kong Chan'), ('Karen Johnson', 'Karen Johnson'), ('Katheryne Angevine', 'Katheryne Angevine'), ('Kenrick Kennedy', 'Kenrick Kennedy'), ('Latanya Carter', 'Latanya Carter'), ('Lily Gebru', 'Lily Gebru'), ("Lisa O'Neill", "Lisa O'Neill"), ('Lorenzo Miles', 'Lorenzo Miles'), ('Margaret Roldan', 'Margaret Roldan'), ('Mark Stevens', 'Mark Stevens'), ('Mary Milbauer', 'Mary Milbauer'), ('Megan Dieleman', 'Megan Dieleman'), ('Michael Wolf', 'Michael Wolf'), ('Michael Ng', 'Michael Ng'), ('Michelle Hall', 'Michelle Hall'), ('Monique Foxx', 'Monique Foxx'), ('Myrna Alonzo', 'Myrna Alonzo'), ('Nartasha Richards', 'Nartasha Richards'), ('Nasra Abdi', 'Nasra Abdi'), ('Nasrin Khoshand', 'Nasrin Khoshand'), ('Natalie Linear', 'Natalie Linear'), ('Neg Watling', 'Neg Watling'), ('Ofelia Olsen', 'Ofelia Olsen'), ('Rachma Saukani', 'Rachma Saukani'), ('Radojka Faguy', 'Radojka Faguy'), ('Rita Dikdan', 'Rita Dikdan'), ('Robert Harrison', 'Robert Harrison'), ('Robert Donnally', 'Robert Donnally'), ('Robert Pitysingh', 'Robert Pitysingh'), ('Shandra White', 'Shandra White'), ('Steven Arledge', 'Steven Arledge'), ('Sylvia Ezekilova', 'Sylvia Ezekilova'), ('Test User', 'Test User'), ('Tracy Clark', 'Tracy Clark')]),
        ),
        migrations.AlterIndexTogether(
            name='award',
            index_together=set([]),
        ),
    ]
