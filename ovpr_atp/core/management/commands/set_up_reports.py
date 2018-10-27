# Custom django-admin command for setting up the example reports
#
# See Django documentation at https://docs.djangoproject.com/en/1.6/howto/custom-management-commands/

from django.contrib.auth.models import User
from django.db.models.fields.related import ForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from awards.models import Award, Proposal, AwardAcceptance, AwardNegotiation, AwardSetup, AwardManagement, AwardCloseout
from report_builder.models import Report, DisplayField, FilterField


FK_DISPLAY_FIELDS = {
    'User': 'username',
    'AwardManager': 'full_name',
    'AllowedCostSchedule': 'name',
    'AwardOrganization': 'name',
    'AwardTemplate': 'short_name',
    'CFDANumber': 'flex_value',
    'FedNegRate': 'description',
    'FundingSource': 'number',
    'IndirectCost': 'rate_schedule',
    'PrimeSponsor': 'name',
}


class Command(BaseCommand):
    help = 'Creates example reports based on all fields in certain models'

    position_counter = 1

    def add_field_to_report(
            self,
            report,
            model,
            field_name,
            allow_recursion=True):
        """Adds the given field to the report.  Includes logic to follow
        foreign keys in order to display their text value properly.
        """

        field = model._meta.get_field(field_name)

        if isinstance(field, ForeignKey):
            fk_model = field.rel.to

            if fk_model.__name__ in FK_DISPLAY_FIELDS:
                report_field = FK_DISPLAY_FIELDS[fk_model.__name__]

                if fk_model == User:
                    path = '%s__' % field_name
                else:
                    path = '%s__%s__' % (model._meta.model_name, field_name)

                display_field = DisplayField(
                    report=report,
                    field=report_field,
                    field_verbose='%s [%s]' %
                    (field.verbose_name,
                     type(field).__name__),
                    name=field.verbose_name,
                    path=path,
                    path_verbose=fk_model._meta.model_name,
                    position=self.position_counter,
                )
                display_field.save()
                return

        display_field = DisplayField(
            report=report,
            field=field_name,
            field_verbose='%s [%s]' %
            (field.verbose_name,
             type(field).__name__),
            name=field.verbose_name,
            position=self.position_counter)

        if model != Award:
            display_field.path = '%s__' % model._meta.model_name
            display_field.path_verbose = model._meta.model_name

        display_field.save()

    def add_display_fields_to_report(self, report, model):
        """Adds all fields from the given model to the report"""

        fields = [field.name for field in model._meta.fields]
        fields.remove('id')

        if hasattr(model, 'MULTIPLE_SELECT_FIELDS'):
            [fields.remove(field) for field in model.MULTIPLE_SELECT_FIELDS]

        for field_name in fields:
            if field_name not in model.HIDDEN_FIELDS:
                self.add_field_to_report(report, model, field_name)
                self.position_counter += 1

        # Add comments field last
        if 'comments' in fields:
            self.add_field_to_report(report, model, 'comments')
            self.position_counter += 1

    def add_filter_fields_to_report(self, report):
        """Adds default filters to the given report"""

        award_acceptance_filter = FilterField(
            report=report,
            path='awardacceptance__',
            path_verbose='awardacceptance',
            field='current_modification',
            field_verbose='current modification [BooleanField]',
            filter_type='exact',
            filter_value='True',
        )
        award_acceptance_filter.save()

        award_negotiation_filter = FilterField(
            report=report,
            path='awardnegotiation__',
            path_verbose='awardnegotiation',
            field='current_modification',
            field_verbose='current modification [BooleanField]',
            filter_type='exact',
            filter_value='True',
        )
        award_negotiation_filter.save()

        first_proposal_filter = FilterField(
            report=report,
            path='proposal__',
            path_verbose='proposal',
            field='is_first_proposal',
            field_verbose='is first proposal [BooleanField]',
            filter_type='exact',
            filter_value='True',
        )
        first_proposal_filter.save()

    def handle(self, *args, **options):
        """The 'main' method of this command.  Gets called by default when running the command."""

        admin = User.objects.get(username='admin')

        report = Report(
            name='Sample award report (all fields)',
            slug='sample-award-report-all-fields',
            description='Copy this report to add your own filters for your own reports',
            root_model=ContentType.objects.get(
                app_label="awards",
                model="award"),
            user_created=admin,
            user_modified=admin,
        )
        report.save()

        self.add_display_fields_to_report(report, Award)
        self.add_display_fields_to_report(report, Proposal)
        self.add_display_fields_to_report(report, AwardAcceptance)
        self.add_display_fields_to_report(report, AwardNegotiation)
        self.add_display_fields_to_report(report, AwardSetup)
        self.add_display_fields_to_report(report, AwardManagement)
        self.add_display_fields_to_report(report, AwardCloseout)

        self.add_filter_fields_to_report(report)

        empty_report = Report(
            name='Sample award report (add your own fields)',
            slug='sample-award-report-no-fields',
            description='Copy this report to add your own fields and filters for your own reports',
            root_model=ContentType.objects.get(
                app_label="awards",
                model="award"),
            user_created=admin,
            user_modified=admin,
        )
        empty_report.save()

        self.add_filter_fields_to_report(empty_report)

        self.stdout.write('Report setup complete')
