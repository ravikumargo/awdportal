# Defines the data models used within the application
#
# See the Django documentation at https://docs.djangoproject.com/en/1.6/topics/db/models/

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from django.contrib.admin.models import LogEntry
from django.core.urlresolvers import reverse
from django.utils.html import format_html
from django.utils import timezone
from itertools import chain
from decimal import Decimal
from datetime import datetime, date, timedelta, tzinfo
from dateutil.tz import tzutc, tzlocal
from multiselectfield import MultiSelectField
import reversion


def get_value_from_choices(choices, code_to_find):
    """Returns the value that corresponds to the given code in the list of choices.

    This is used to translate a code value, as stored in the database, to its
    corresponding text value from the choices tuple.
    """
    return next((value for code, value in choices if code == code_to_find), '')

class FieldIteratorMixin(models.Model):
    """Returns the verbose_name and value for each non-HIDDEN_FIELD on an object"""

    def _get_field(self, field):
        """Gets the specified field from the model"""

        model_field = self._meta.get_field(field)
        name = model_field.verbose_name

        if model_field.choices:
            display_method = getattr(self, 'get_' + field + '_display')
            data = display_method()
        else:
            data = getattr(self, field)

        boolean_field = isinstance(model_field, models.NullBooleanField)

        return (name, data, boolean_field)

    def _get_field_full(self, field):
        """Gets the specified field from the model, along with the field name"""

        model_field = self._meta.get_field(field)
        name = model_field.verbose_name

        if model_field.choices:
            display_method = getattr(self, 'get_' + field + '_display')
            data = display_method()
        else:
            data = getattr(self, field)

        boolean_field = isinstance(model_field, models.NullBooleanField)

        return (name, data, boolean_field, model_field.name)

    def get_model_fields(self):
        """Gets all fields from the model that aren't defined in HIDDEN_FIELDS"""

        fields = [field.name for field in self._meta.fields]
        fields.remove('id')

        for field in self.HIDDEN_FIELDS:
            fields.remove(field)

        return fields

    def get_table_fields(self):
        """Gets all fields from the model to display in table format
        Fields defined in HIDDEN_TABLE_FIELDS are excluded.
        """

        fields = self.get_model_fields()

        for field in self.HIDDEN_TABLE_FIELDS:
            fields.remove(field)
        field_data = [self._get_field(field) for field in fields]

        return field_data

    def get_all_fields(self):
        """Gets all non-HIDDEN_FIELDs from the model and their data"""

        fields = self.get_model_fields()
        field_data = [self._get_field(field) for field in fields]

        return field_data

    def get_search_fields(self):
        """Gets fields necessary for searching
        Fields defined in HIDDEN_SEARCH_FIELDS are excluded
        """

        fields = self.get_model_fields()

        for field in self.HIDDEN_SEARCH_FIELDS:
            fields.remove(field)

        field_data = [self._get_field_full(field) for field in fields]

        if isinstance(self, Subaward) and hasattr(self, 'comments'):
            field_data.append(self._get_field_full('comments'))

        return field_data

    def get_fieldsets(self):
        """Gets the model's fields and separates them out into the defined FIELDSETS"""

        fields = self.get_model_fields()

        fieldset_data = []
        for fieldset in self.FIELDSETS:
            fieldset_fields = []
            for field in fieldset['fields']:
                fieldset_fields.append(self._get_field(field))
                fields.remove(field)
            fieldset_data.append((fieldset['title'], fieldset_fields))

        if hasattr(self, 'DISPLAY_TABLES'):
            for display_table in self.DISPLAY_TABLES:
                for row in display_table['rows']:
                    for field in row['fields']:
                        fields.remove(field)

        fieldset_data.append(
            (None, [self._get_field(field) for field in fields]))

        return fieldset_data

    def get_display_tables(self):
        """Gets the fields and data defined in DISPLAY_TABLES for tabular display"""

        display_tables = []
        for item in self.DISPLAY_TABLES:
            rows = []
            for row in item['rows']:
                data = {'label': row['label']}
                data['fields'] = [
                    self._get_field(field) for field in row['fields']]
                rows.append(data)

            display_table = {
                'title': item['title'],
                'columns': item['columns'],
                'rows': rows}
            display_tables.append(display_table)

        return display_tables

    def get_award_setup_report_fields(self):
        """Gets the fields needed for EAS report"""

        return [self._get_field(field) for field in self.EAS_REPORT_FIELDS]

    class Meta:
        abstract = True


class EASUpdateMixin(object):
    """If it's expired or inactive, unset this object from any foriegn key fields"""

    def save(self, *args, **kwargs):
        super(EASUpdateMixin, self).save(*args, **kwargs)
        expired = False

        if hasattr(self, 'end_date'):
            if self.end_date:
                if isinstance(self.end_date, date):
                    expired = self.end_date < date.today()
                else:
                    expired = self.end_date < datetime.now()
            else:
                expired = False

        if not self.active or expired:
            for related_object in self._meta.get_all_related_objects():
                accessor_name = related_object.get_accessor_name()
                if not hasattr(self, accessor_name):
                    break
                related_queryset = eval('self.%s' % accessor_name)
                field_name = related_object.field.name
                for item in related_queryset.all():
                    setattr(item, field_name, None)
                    item.save()


class AllowedCostSchedule(EASUpdateMixin, models.Model):
    """Model for the AllowedCostSchedule data"""

    EAS_FIELD_ORDER = [
        'id',
        'name',
        'end_date',
        'active'
    ]

    id = models.BigIntegerField(primary_key=True, unique=True)
    name = models.CharField(max_length=30)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class AwardManager(FieldIteratorMixin, EASUpdateMixin, models.Model):
    """Model for the AwardManager data"""

    EAS_FIELD_ORDER = [
        'id',
        'full_name',
        'gwid',
        'system_user',
        'end_date',
        'active'
    ]

    CAYUSE_FIELDS = [
        'title',
        'first_name',
        'middle_name',
        'last_name',
        'phone',
        'email'
    ]

    FIELDSETS = []

    HIDDEN_FIELDS = [
        'system_user',
        'end_date',
        'active',
        'first_name',
        'middle_name',
        'last_name'
    ]

    id = models.BigIntegerField(primary_key=True, unique=True)
    full_name = models.CharField(max_length=240)
    gwid = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='GWID')
    system_user = models.BooleanField()
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField()

    # Cayuse fields
    title = models.CharField(max_length=64, blank=True, null=True)
    first_name = models.CharField(max_length=64, blank=True)
    middle_name = models.CharField(max_length=32, blank=True)
    last_name = models.CharField(max_length=64, blank=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
    email = models.CharField(max_length=64, blank=True, null=True)

    def __unicode__(self):
        return self.full_name


class AwardOrganization(EASUpdateMixin, models.Model):
    """Model for the AwardOrganization data"""

    EAS_FIELD_ORDER = [
        'id',
        'name',
        'organization_type',
        'org_info1_meaning',
        'org_info2_meaning',
        'end_date',
        'active'
    ]

    id = models.BigIntegerField(primary_key=True, unique=True)
    name = models.CharField(max_length=240)
    organization_type = models.CharField(max_length=30, blank=True, null=True)
    org_info1_meaning = models.CharField(max_length=80)
    org_info2_meaning = models.CharField(max_length=80)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class AwardTemplate(EASUpdateMixin, models.Model):
    """Model for the AwardTemplate data"""

    EAS_FIELD_ORDER = [
        'id',
        'number',
        'short_name',
        'active'
    ]

    id = models.BigIntegerField(primary_key=True, unique=True)
    number = models.CharField(max_length=15)
    short_name = models.CharField(max_length=30)
    active = models.BooleanField()

    def __unicode__(self):
        return u'%s - %s' % (self.number, self.short_name)

    class Meta:
        ordering = ['number']


class CFDANumber(EASUpdateMixin, models.Model):
    """Model for the CFDANumber data"""

    EAS_FIELD_ORDER = [
        'flex_value',
        'description',
        'end_date',
        'active'
    ]

    flex_value = models.CharField(
        max_length=150,
        primary_key=True,
        unique=True)
    description = models.CharField(max_length=240)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField()

    def __unicode__(self):
        return u'%s - %s' % (self.flex_value, self.description)

    class Meta:
        ordering = ['flex_value']


class FedNegRate(EASUpdateMixin, models.Model):
    """Model for the FedNegRate data"""

    EAS_FIELD_ORDER = [
        'flex_value',
        'description',
        'end_date',
        'active'
    ]

    flex_value = models.CharField(
        max_length=150,
        primary_key=True,
        unique=True)
    description = models.CharField(max_length=240)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField()

    def __unicode__(self):
        return self.description

    class Meta:
        ordering = ['description']


class FundingSource(EASUpdateMixin, models.Model):
    """Model for the FundingSource data"""

    EAS_FIELD_ORDER = [
        'name',
        'number',
        'id',
        'active',
        'end_date'
    ]

    id = models.BigIntegerField(primary_key=True, unique=True)
    name = models.CharField(max_length=50)
    number = models.CharField(max_length=10)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField()

    def __unicode__(self):
        return u'%s - %s' % (self.number, self.name)

    class Meta:
        ordering = ['number']


class IndirectCost(EASUpdateMixin, models.Model):
    """Model for the IndirectCost data"""

    EAS_FIELD_ORDER = [
        'id',
        'rate_schedule',
        'end_date',
        'active'
    ]

    id = models.BigIntegerField(primary_key=True, unique=True)
    rate_schedule = models.CharField(max_length=30)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField()

    def __unicode__(self):
        return self.rate_schedule

    class Meta:
        ordering = ['rate_schedule']


class PrimeSponsor(EASUpdateMixin, models.Model):
    """Model for the PrimeSponsor data"""

    EAS_FIELD_ORDER = [
        'name',
        'number',
        'id',
        'active',
    ]

    id = models.BigIntegerField(primary_key=True, unique=True)
    name = models.CharField(max_length=50)
    number = models.IntegerField()
    active = models.BooleanField()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class EASMapping(models.Model):
    """Model used to define a mapping between EAS data and the corresponding value in ATP"""

    INTERFACE_CHOICES = (
        ('C', 'Cayuse'),
        ('L', 'Lotus'),
    )

    interface = models.CharField(
        choices=INTERFACE_CHOICES,
        max_length=1,
        default='C')
    field = models.CharField(max_length=50)
    incoming_value = models.CharField(max_length=250)
    atp_model = models.CharField(max_length=50)
    atp_pk = models.IntegerField()

    def __unicode__(self):
        return u'(%s) %s=%s -> %s=%s' % (self.interface,
                                         self.field,
                                         self.incoming_value,
                                         self.atp_model,
                                         self.atp_pk)

    class Meta:
        unique_together = (
            'interface',
            'field',
            'incoming_value',
            'atp_model',
            'atp_pk')


class EASMappingException(Exception):
    """Custom exception import processes throw when a new mapping is required"""

    def __init__(self, message, interface, field, incoming_value, atp_model):
        super(EASMappingException, self).__init__(self, message)

        self.interface = interface
        self.field = field
        self.incoming_value = incoming_value
        self.atp_model = atp_model


class ATPAuditTrail(models.Model):
    """It is used internally to track each point of time when an award assinged and completed from a particular stage"""
    award = models.IntegerField()
    modification = models.CharField(max_length=100)
    workflow_step = models.CharField(max_length=100)
    date_created = models.DateTimeField(blank=True, null=True)
    date_completed = models.DateTimeField(blank=True, null=True)
    assigned_user = models.CharField(max_length=100)


class Award(models.Model):
    """The primary model"""
    WAIT_FOR = {'RB': 'Revised Budget', 'PA': 'PI Access', 'CA': 'Cost Share Approval', 'FC': 'FCOI',
                'PS': 'Proposal Submission', 'SC': 'Sponsor Clarity', 'NO': 'New Org needed',
                'IC': 'Internal Clarification', 'DC': 'Documents not in GW Docs'
                }
    # These fields aren't displayed by the FieldIteratorMixin
    HIDDEN_FIELDS = [
        'subaward_done',
        'award_management_done',
        'extracted_to_eas',
    ]

    # Workflow statuses
    STATUS_CHOICES = (
        (0, 'New'),
        (1, 'Award Intake'),
        (2, 'Award Negotiation'),
        (3, 'Award Setup'),
        (4, 'Subaward & Award Management'),
        (5, 'Award Closeout'),
        (6, 'Complete'),
    )

    # A mapping for which sections are active in which statuses
    STATUS_SECTION_MAPPING = [
        [],
        ['AwardAcceptance'],
        ['AwardNegotiation'],
        ['AwardSetup', 'AwardModification'],
        ['Subaward', 'AwardManagement'],
        ['AwardCloseout'],
        []
    ]

    # A mapping for relevant user fields, groups, URLs, and statuses for each section
    SECTION_FIELD_MAPPING = {
        'ProposalIntake': {
            'user_field': None,
            'group': 'Proposal Intake',
            'edit_url': 'edit_proposal_intake',
            'edit_status': 0},
        'AwardAcceptance': {
            'user_field': 'award_acceptance_user',
            'group': 'Award Acceptance',
            'edit_url': 'edit_award_acceptance',
            'edit_status': 1},
        'AwardNegotiation': {
            'user_field': 'award_negotiation_user',
            'group': 'Award Negotiation',
            'edit_url': 'edit_award_negotiation',
            'edit_status': 2},
        'AwardSetup': {
            'user_field': 'award_setup_user',
            'group': 'Award Setup',
            'edit_url': 'edit_award_setup',
            'edit_status': 3},
        'AwardModification': {
            'user_field': 'award_modification_user',
            'group': 'Award Modification',
            'edit_url': 'edit_award_setup',
            'edit_status': 3},
        'Subaward': {
            'user_field': 'subaward_user',
            'group': 'Subaward Management',
            'edit_url': 'edit_subawards',
                        'edit_status': 4},
        'AwardManagement': {
            'user_field': 'award_management_user',
            'group': 'Award Management',
            'edit_url': 'edit_award_management',
            'edit_status': 4},
        'AwardCloseout': {
            'user_field': 'award_closeout_user',
            'group': 'Award Closeout',
            'edit_url': 'edit_award_closeout',
            'edit_status': 5},
    }

    # Associates subsections with their parent sections (used in edit permission checks)
    SECTION_PARENT_MAPPING = {
        'PTANumber': 'AwardSetup',
        'PriorApproval': 'AwardManagement',
        'ReportSubmission': 'AwardManagement',
        'FinalReport': 'AwardCloseout',
    }

    START_STATUS = 0
    END_STATUS = 6
    AWARD_SETUP_STATUS = 3
    AWARD_ACCEPTANCE_STATUS = 1

    status = models.IntegerField(choices=STATUS_CHOICES, default=0)
    creation_date = models.DateField(auto_now_add=True)
    extracted_to_eas = models.BooleanField(default=False)

    # Limit assignment users to members of the appropriate group
    award_acceptance_user = models.ForeignKey(
        User,
        related_name='+',
        verbose_name='Award Intake User',
        limit_choices_to=Q(
            groups__name='Award Acceptance'))
    award_negotiation_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='Award Negotiation User',
        limit_choices_to=Q(
            groups__name='Award Negotiation'))
    award_setup_user = models.ForeignKey(
        User,
        related_name='+',
        verbose_name='Award Setup User',
        limit_choices_to=Q(
            groups__name='Award Setup'))
    award_modification_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='Award Modification User',
        limit_choices_to=Q(
            groups__name='Award Modification'))
    subaward_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='Subaward User',
        limit_choices_to=Q(
            groups__name='Subaward Management'))
    award_management_user = models.ForeignKey(
        User,
        related_name='+',
        verbose_name='Award Management User',
        limit_choices_to=Q(
            groups__name='Award Management'))
    award_closeout_user = models.ForeignKey(
        User,
        related_name='+',
        verbose_name='Award Closeout User',
        limit_choices_to=Q(
            groups__name='Award Closeout'))

    # Because these two sections are active in the same status, we need to
    # track their completion independently
    subaward_done = models.BooleanField(default=False)
    award_management_done = models.BooleanField(default=False)
    send_to_modification = models.BooleanField(default=False)
    send_to_setup = models.BooleanField(default=False)
    common_modification = models.BooleanField(default=False)
    award_dual_negotiation = models.BooleanField(default=False)
    award_dual_setup = models.BooleanField(default=False)
    award_dual_modification = models.BooleanField(default=False)
    award_text = models.CharField(max_length=50, blank=True, null=True)

    # If an award has a proposal, use that to determine its name. Otherwise,
    # use its internal ID
    def __unicode__(self):
        proposal = self.get_first_real_proposal()
        if proposal and proposal.get_unique_identifier() != '':
            return u'Award for proposal #%s' % proposal.get_unique_identifier()
        else:
            return u'Award #%s' % self.id

    @classmethod
    def get_priority_assignments_for_award_setup_user(cls, user):
        assignment_list = []
        assign_filter = cls.objects.filter(
            (Q(Q(award_setup_user=user) & Q(status=2) & Q(award_dual_setup=True)) | Q(Q(award_setup_user=user) & Q(status=3) & Q(award_dual_setup=True))) |
            (Q(award_setup_user=user) & Q(status=3) & Q(send_to_modification=False)) |
            (Q(award_modification_user=user) & Q(status=3) & Q(send_to_modification=True)) |
            (Q(award_modification_user=user) & Q(status=2) & Q(award_dual_modification=True))
        )
        award_ids = []
        temp_ids = []
        award_assignments = []
        for award_ in assign_filter:
            award_ids.append(award_.id)

        assignments_on = AwardAcceptance.objects.filter(award_id__in=award_ids, award_setup_priority='on',
                                                        current_modification=True).order_by('creation_date')
        assignments_tw = AwardAcceptance.objects.filter(award_id__in=award_ids, award_setup_priority='tw',
                                                        current_modification=True).order_by('creation_date')
        assignments_th = AwardAcceptance.objects.filter(award_id__in=award_ids, award_setup_priority='th',
                                                        current_modification=True).order_by('creation_date')
        assignments_fo = AwardAcceptance.objects.filter(award_id__in=award_ids, award_setup_priority='fo',
                                                        current_modification=True).order_by('creation_date')
        assignments_fi = AwardAcceptance.objects.filter(award_id__in=award_ids, award_setup_priority='fi',
                                                        current_modification=True).order_by('creation_date')
        assignments_ni = AwardAcceptance.objects.filter(award_id__in=award_ids, award_setup_priority='ni',
                                                        current_modification=True).order_by('creation_date')
        assignments_none = AwardAcceptance.objects.filter(award_id__in=award_ids, award_setup_priority='',
                                                          current_modification=True).order_by('creation_date')
        assignments = list(chain(assignments_on, assignments_tw, assignments_th,
                                 assignments_fo, assignments_fi, assignments_ni, assignments_none))

        for award in assignments:
            if award.award_id in award_ids:
                temp_ids.append(award.award_id)

        assignments = cls.objects.filter(id__in=temp_ids)
        for id in temp_ids:
            for award in assignments:
                if award.id == id:
                    award_assignments.append(award)
        for award in award_assignments:
            active_sections = award.STATUS_SECTION_MAPPING[award.status]
            for section in active_sections:
                for user_group in user.groups.all():
                    if section == 'AwardNegotiation' and user_group.name == 'Award Setup':
                        section = 'AwardSetup'
                    if section == 'AwardNegotiation' and user_group.name == 'Award Modification':
                        section = 'AwardModification'
                    if award.get_user_for_section(section) == user:
                        edit_url = reverse(
                            award.SECTION_FIELD_MAPPING[section]['edit_url'],
                            kwargs={
                                'award_pk': award.pk})
            assignment_list.append((award, edit_url))

        return assignment_list

    @classmethod
    def get_assignments_for_user(cls, user):
        """Given a user, find all currently assigned awards"""
        assignments = cls.objects.filter(
            (Q(award_acceptance_user=user) & Q(status=1)) |
            (Q(Q(award_negotiation_user=user) & Q(status=2)) | Q(Q(award_negotiation_user=user) & Q(status=2) & Q(award_dual_negotiation=True))) |
            (Q(Q(award_setup_user=user) & Q(status=2) & Q(award_dual_setup=True)) | Q(Q(award_setup_user=user) & Q(status=3) & Q(award_dual_setup=True))) |
            (Q(award_setup_user=user) & Q(status=3) & Q(send_to_modification=False)) |
            (Q(award_modification_user=user) & Q(status=3) & Q(Q(send_to_modification=True))) |
            (Q(award_modification_user=user) & Q(status=2) & Q(Q(award_dual_modification=True))) |
            (Q(subaward_user=user) & Q(status=4)) |
            (Q(award_management_user=user) & Q(status=4)) |
            (Q(award_closeout_user=user) & Q(status=5))
        )

        assignment_list = []
        for award in assignments:
            active_sections = award.STATUS_SECTION_MAPPING[award.status]
            for section in active_sections:
                for user_group in user.groups.all():
                    if section == 'AwardNegotiation' and user_group.name == 'Award Setup':
                        section = 'AwardSetup'
                    if section == 'AwardNegotiation' and user_group.name == 'Award Modification':
                        section = 'AwardModification'
                    if award.get_user_for_section(section) == user:
                        edit_url = reverse(
                            award.SECTION_FIELD_MAPPING[section]['edit_url'],
                            kwargs={
                                'award_pk': award.pk})
            assignment_list.append((award, edit_url))

        return assignment_list

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object"""

        return reverse('award_detail', kwargs={'award_pk': self.pk})

    def save(self, *args, **kwargs):
        # On initial save, create a dummy proposal and blank sections
        if not self.pk:
            super(Award, self).save(*args, **kwargs)
            Proposal.objects.create(award=self, dummy=True)
            AwardAcceptance.objects.create(award=self)
            AwardNegotiation.objects.create(award=self)
            AwardSetup.objects.create(award=self)
            AwardManagement.objects.create(award=self)
            AwardCloseout.objects.create(award=self)
        else:
            check_status = kwargs.pop('check_status', True)
            try:
                old_object = Award.objects.get(pk=self.pk)
            except Award.DoesNotExist:
                super(Award, self).save(*args, **kwargs)
                return

            if any([self.award_acceptance_user != old_object.award_acceptance_user, self.award_closeout_user != old_object.award_closeout_user,
                    self.award_management_user != old_object.award_management_user, self.award_modification_user != old_object.award_modification_user,
                    self.award_negotiation_user != old_object.award_negotiation_user, self.award_setup_user != old_object.award_setup_user]):
                self.send_to_setup = old_object.send_to_setup
                self.send_to_modification = old_object.send_to_modification
                self.common_modification = old_object.common_modification
                self.award_dual_modification = old_object.award_dual_modification
                self.award_dual_setup = old_object.award_dual_setup
                self.award_dual_negotiation = old_object.award_dual_negotiation

            super(Award, self).save(*args, **kwargs)

            if check_status and old_object.status > 1 and self.status == 1 and self.get_current_award_acceptance().phs_funded:
                self.send_phs_funded_notification()

    def get_proposals(self):
        """Gets all Proposals associated with this Award"""

        proposals = []

        first_proposal = self.get_first_real_proposal()
        if first_proposal:
            proposals.append(first_proposal)
            proposals.extend(self.get_supplemental_proposals())

        return proposals

    def get_first_real_proposal(self):
        """Gets the first non-dummy Proposal associated with this Award"""

        try:
            first_proposal = self.proposal_set.get(
                is_first_proposal=True,
                dummy=False)
        except Proposal.DoesNotExist:
            first_proposal = None

        return first_proposal

    def get_supplemental_proposals(self):
        """Gets all non-dummy Proposals after the first one"""

        first_proposal = self.get_first_real_proposal()
        supplemental_proposals = None

        if first_proposal:
            supplemental_proposals = self.proposal_set.filter(dummy=False).exclude(id=first_proposal.id).order_by('id')

        return supplemental_proposals

    def get_most_recent_proposal(self):
        """Gets the most recent Proposal"""
        return self.proposal_set.filter(dummy=False).order_by('id').last()

    def get_current_award_acceptance(self, acceptance_flag=False):
        if acceptance_flag:
            acceptance_object = self.awardacceptance_set.filter(current_modification=True)
            if acceptance_object:
                return acceptance_object[0]
            else:
                acceptance_object = AwardAcceptance()
                return acceptance_object
        award_acceptance = self.awardacceptance_set.filter(current_modification=True).order_by('-creation_date')
        if len(award_acceptance) > 1:
            for award in award_acceptance[1:]:
                award.current_modification = False
                award.save()
            return award_acceptance[0]
        else:
            return self.awardacceptance_set.get(current_modification=True)

    def get_previous_award_acceptances(self):
        return self.awardacceptance_set.filter(current_modification=False)

    def get_current_award_negotiation(self):
        try:
            negotiation_obj = self.awardnegotiation_set.get(current_modification=True)
        except:
            negotiation_obj = None
        award_negotiation = self.awardnegotiation_set.filter(current_modification=True).order_by('-date_assigned')
        if len(award_negotiation) > 1:
            for award in award_negotiation[1:]:
                award.current_modification = False
                award.save()
            return award_negotiation[0]
        elif negotiation_obj:
            return self.awardnegotiation_set.get(current_modification=True)
        else:
            return AwardNegotiation()

    def get_previous_award_negotiations(self):
        return self.awardnegotiation_set.filter(current_modification=False)

    def get_first_pta_number(self):
        pta_number = self.ptanumber_set.all().order_by('id')[:1]
        if pta_number:
            return pta_number[0]
        else:
            return None

    def get_award_numbers(self):
        """Returns a comma-delimited string of award numbers from all PTANumbers in this Award"""

        award_numbers = self.ptanumber_set.exclude(award_number='').values_list('award_number', flat=True)
        return ', '.join(award_numbers)

    def get_date_assigned_to_current_stage(self):
        """Returns the date this Award was moved on to its current stage"""

        dates_assigned = []

        for section in self.get_active_sections():
            try:
                if section == 'AwardAcceptance':
                    correct_instance = AwardAcceptance.objects.get(award=self, current_modification=True)
                    local_date = correct_instance.creation_date.astimezone(tzlocal())
                    dates_assigned.append(local_date.strftime('%m/%d/%Y'))
                elif section == 'Subaward' or section == 'AwardManagement':
                    if Subaward.objects.filter(award=self).count() > 0:
                        correct_instance = Subaward.objects.filter(award=self).latest('creation_date')
                        local_date = correct_instance.creation_date.astimezone(tzlocal())
                        dates_assigned.append(local_date.strftime('%m/%d/%Y'))
                    else:
                        correct_instance = AwardManagement.objects.get(award=self)
                        local_date = correct_instance.date_assigned.astimezone(tzlocal())
                        dates_assigned.append(local_date.strftime('%m/%d/%Y'))
                else:
                    if section == 'AwardNegotiation':
                        correct_instance = AwardNegotiation.objects.get(award=self, current_modification=True)
                    elif section == 'AwardSetup':
                        correct_instance = AwardSetup.objects.get(award=self)
                    elif section == 'AwardCloseout':
                        correct_instance = AwardCloseout.objects.get(award=self)

                    if correct_instance.date_assigned:
                        local_date = correct_instance.date_assigned.astimezone(tzlocal())
                        dates_assigned.append(local_date.strftime('%m/%d/%Y'))
            except:
                pass

        dates_assigned = list(set(dates_assigned))
        if len(dates_assigned) > 0:
            return ', '.join(dates_assigned)
        else:
            return ''

    def get_user_for_section(self, section, modification_flag=False):
        """Uses the SECTION_PARENT_MAPPING to determine the user assigned to the given section"""
        if section == 'AwardSetup' and self.award_dual_modification:
            section = 'AwardModification'
        if modification_flag:
            section = 'AwardModification'
        if section in self.SECTION_PARENT_MAPPING:
            section = self.SECTION_PARENT_MAPPING[section]
        try:
            return getattr(
                self,
                self.SECTION_FIELD_MAPPING[section]['user_field'])
        except TypeError:
            return None

    def get_current_award_status_for_display(self):
        return 'Award Negotiation and Setup'

    def get_award_setup_modification_status(self):
        if self.status == 2:
            return True
        else:
            return False

    def get_active_sections(self, dual_mode=False):
        """Gets the names of the currently active sections"""
        if self.status == self.AWARD_SETUP_STATUS:
            active_sections = ['AwardSetup']
        elif dual_mode:
            active_sections = ['AwardNegotiation', 'AwardSetup']
        else:
            active_sections = self.STATUS_SECTION_MAPPING[self.status]

        return active_sections

    def get_users_for_dual_active_sections(self):
        active_users = []
        for section in ['AwardNegotiation', 'AwardSetup']:
            user = self.get_user_for_section(section)
            if user:
                active_users.append(user)

        return active_users

    def get_users_for_negotiation_and_moidification_sections(self):
        active_users = []
        for section in ['AwardNegotiation', 'AwardModification']:
            user = self.get_user_for_section(section)
            if user:
                active_users.append(user)

        return active_users

    def get_users_for_active_sections(self, section_flag=False):
        """Gets the users assigned to the currently active sections"""

        active_users = []
        if self.status == 3 and self.send_to_modification:
            user_section = "AwardModification"
            user = self.get_user_for_section(user_section)
            if user:
                active_users.append(user)
            return active_users

        for section in self.get_active_sections():
            user = self.get_user_for_section(section)
            if user:
                active_users.append(user)

        return active_users

    def get_current_active_users(self):
        """Returns a comma-delimited list of users assigned to the currently active sections"""
        if self.award_dual_setup and self.award_dual_negotiation and self.status == 2:
            users = self.get_users_for_dual_active_sections()
        elif self.award_dual_modification and self.status == 2:
            users = self.get_users_for_negotiation_and_moidification_sections()
        else:
            users = self.get_users_for_active_sections()
        names = []

        for user in users:
            names.append(user.get_full_name())

        return ', '.join(names)

    def get_award_priority_number(self):
        award_accept = self.awardacceptance_set.get(award_id=self.id, current_modification=True)
        if award_accept.award_setup_priority:
            return AwardAcceptance.PRIORITY_STATUS_DICT[award_accept.award_setup_priority]
        else:
            return ''

    def get_edit_status_for_section(self, section, setup_flow_flag=False):
        """Gets the edit_status for the given section"""

        if setup_flow_flag:
            return self.SECTION_FIELD_MAPPING['AwardNegotiation']['edit_status']

        if section in self.SECTION_PARENT_MAPPING:
            section = self.SECTION_PARENT_MAPPING[section]
        return self.SECTION_FIELD_MAPPING[section]['edit_status']

    def get_editable_sections(self):
        """Returns a list of editable sections.
        A section is editable if the Award's status is at or beyond that section
        """
        if self.award_dual_negotiation and self.award_dual_setup:
            editable_sections = [section for section in self.SECTION_FIELD_MAPPING.keys(
            ) if self.SECTION_FIELD_MAPPING[section]['edit_status'] <= self.status + 1]
        else:
            editable_sections = [section for section in self.SECTION_FIELD_MAPPING.keys(
            ) if self.SECTION_FIELD_MAPPING[section]['edit_status'] <= self.status]

        return editable_sections

    def send_email_update_if_subaward_user(self):
        """Sends an email update to subaward user if the award send to award setup"""
        recipients = [self.get_user_for_section('Subaward').email]

        pi_name = ''
        most_recent_proposal = self.get_most_recent_proposal()
        if most_recent_proposal:
            pi_name = ' (PI: {0})'.format(most_recent_proposal.principal_investigator)

        send_mail(
            'OVPR ATP Update',
            'Award for proposal #%s%s has been assigned to Award Setup in ATP. Go to %s%s to review it.' %
            (self.id,
             pi_name,
             settings.EMAIL_URL_HOSTNAME,
             self.get_absolute_url()),
            'reply@email.gwu.edu',
            recipients,
            fail_silently=False)


    def send_email_update(self, modification_flag=False):
        """Sends an email update to a user when they've been assigned an active section"""
        if self.status == 1:
            origional_text = 'Original Award'
            workflow = 'AwardAcceptance'
            acceptance_count = AwardAcceptance.objects.filter(award=self).count()
            if acceptance_count < 2:
                self.record_current_state_to_atptrail(origional_text, workflow)
            else:
                modification = "Modification #%s" % (acceptance_count - 1)
                self.record_current_state_to_atptrail(modification, workflow)

        if modification_flag:
            recipients = [self.get_user_for_section('AwardSetup', modification_flag).email]
        else:
            if self.award_dual_negotiation and self.award_dual_setup:
                recipients = [user.email for user in self.get_users_for_dual_active_sections()]
            elif self.award_dual_modification:
                recipients = [user.email for user in self.get_users_for_negotiation_and_moidification_sections()]
            else:
                recipients = [user.email for user in self.get_users_for_active_sections()]

        pi_name = ''
        most_recent_proposal = self.get_most_recent_proposal()
        if most_recent_proposal:
            pi_name = ' (PI: {0})'.format(most_recent_proposal.principal_investigator)

        send_mail(
            'OVPR ATP Update',
            '%s%s has been assigned to you in ATP. Go to %s%s to review it.' %
            (self,
             pi_name,
             settings.EMAIL_URL_HOSTNAME,
             self.get_absolute_url()),
            'reply@email.gwu.edu',
            recipients,
            fail_silently=False)

    def send_award_setup_notification(self):
        """Sends an email to the AwardAcceptance user to let them know the award is in Award Setup"""

        recipients = [self.get_user_for_section('AwardAcceptance').email]

        send_mail(
            'OVPR ATP Update',
            '%s has been sent to the Award Setup step. This email is simply a notification \
- you are not assigned to perform Award Setup for this award. \
You can view it here: %s%s' %
            (self,
             settings.EMAIL_URL_HOSTNAME,
             self.get_absolute_url()),
            'reply@email.gwu.edu',
            recipients,
            fail_silently=False)

    def send_fcoi_cleared_notification(self, fcoi_cleared_date):
        """Sends an email to the AwardSetup user when the Award's fcoi_cleared_date is set"""

        recipients = [self.get_user_for_section('AwardSetup').email]

        send_mail('OVPR ATP Update',
                  'The FCOI cleared date has been entered on %s - it is %s. \
You can view it here: %s%s' % (self, fcoi_cleared_date, settings.EMAIL_URL_HOSTNAME, self.get_absolute_url()),
                  'reply@email.gwu.edu',
                  recipients, fail_silently=False)

    def send_phs_funded_notification(self):
        """Sends an email to the PHS_FUNDED_RECIPIENTS when the Award has been marked as PHS funded"""

        recipients = settings.PHS_FUNDED_RECIPIENTS

        send_mail('OVPR ATP Update',
                  'PHS funded for %s has been received and requires FCOI verification. \
Please go to %s%s to review it.' % (self, settings.EMAIL_URL_HOSTNAME, self.get_absolute_url()),
                  'reply@email.gwu.edu',
                  recipients, fail_silently=False)

    def send_phs_funded_notification_with_modification(self):
        """Sends an email to the PHS_FUNDED_RECIPIENTS when and Award Modification is created 
        and it's marked as PHS funded
        """

        recipients = settings.PHS_FUNDED_RECIPIENTS

        send_mail('OVPR ATP Update',
                  'PHS funded for %s (Modification) has been received and may require FCOI verification. \
Please go to %s%s to review it.' % (self, settings.EMAIL_URL_HOSTNAME, self.get_absolute_url()),
                  'reply@email.gwu.edu',
                  recipients, fail_silently=False)

    def set_date_assigned_for_active_sections(self):
        """Sets the date_assigned, if appliccable, for the currently active section(s)"""

        for section in self.get_active_sections():
            if section in self.SECTION_FIELD_MAPPING:
                current_mod = Q()
                if section in ['AwardNegotiation', 'AwardAcceptance']:
                    current_mod = Q(current_modification=True)

                for instance in eval(section).objects.filter(current_mod, award=self):
                    try:
                        instance.set_date_assigned()
                    except AttributeError:
                        pass

    def record_wait_for_reason(self, workflow_old, workflow_new, model_name):
        WAIT_FOR = {'RB': 'Revised Budget', 'PA': 'PI Access', 'CA': 'Cost Share Approval', 'FC': 'FCOI',
                     'PS': 'Proposal Submission', 'SC': 'Sponsor Clarity', 'NO': 'New Org needed',
                     'IC': 'Internal Clarification', 'DC': 'Documents not in GW Docs'
                     }

        count_value = AwardAcceptance.objects.filter(award=self).count()
        if count_value < 2:
            origional_text = 'Original Award'
        else:
            origional_text = "Modification #%s" % (count_value - 1)
        user_name = self.get_user_full_name(model_name)
        if workflow_new:
            try:
                trail_object = ATPAuditTrail.objects.get(award=self.id, modification=origional_text,
                                                         workflow_step=WAIT_FOR[workflow_new], assigned_user=user_name)
            except:
                trail_object = None

            if trail_object:
                trail_object.date_completed = datetime.now()
            else:
                trail_object = ATPAuditTrail(award=self.id, modification=origional_text, workflow_step=WAIT_FOR[workflow_new],
                                             date_created=datetime.now(), assigned_user=user_name)
            trail_object.save()

        if workflow_old:
            try:
                trail_object = ATPAuditTrail.objects.get(award=self.id, modification=origional_text,
                                                         workflow_step=WAIT_FOR[workflow_old], assigned_user=user_name)
            except:
                trail_object = None

            if trail_object:
                trail_object.date_completed = datetime.now()
                trail_object.save()
            elif 'Modification' in origional_text:
                pass
            else:
                trail_object = ATPAuditTrail(award=self.id, modification=origional_text, workflow_step=WAIT_FOR[workflow_old],
                                             date_created=datetime.now(), assigned_user=user_name)
                trail_object.save()

    def record_current_state_to_atptrail(self, modification, workflow):
        user_name = self.get_user_full_name(workflow)
        try:
            trail_object = ATPAuditTrail.objects.get(award=self.id, modification=modification, workflow_step=workflow,
                                                     assigned_user=user_name)
        except:
            trail_object = None
        if trail_object:
            trail_object.date_completed = datetime.now()
        else:
            trail_object = ATPAuditTrail(award=self.id, modification=modification, workflow_step=workflow,
                                         date_created=datetime.now(), assigned_user=user_name)
        trail_object.save()

    def get_user_full_name(self, section):
        user = self.get_user_for_section(section)
        if user:
            return user.first_name + ' ' + user.last_name
        else:
            return None

    def update_completion_date_in_atp_award(self):
        origional_text = 'Original Award'
        acceptance_workflow = 'AwardAcceptance'
        negotiation_workflow = 'AwardNegotiation'
        setup_workflow = 'AwardSetup'
        modification_workflow = 'AwardModification'
        subaward_workflow = 'Subaward'
        management_workflow = 'AwardManagement'
        closeout_workflow = 'AwardCloseout'
        count_value = AwardAcceptance.objects.filter(award=self).count()
        modification = "Modification #%s" % (count_value - 1)

        if all([self.status == 2, self.award_dual_modification]):
            acceptance_object = self.get_current_award_acceptance()
            acceptance_object.acceptance_completion_date = timezone.localtime(timezone.now())
            acceptance_object.save()
            if count_value < 2:
                self.record_current_state_to_atptrail(origional_text, acceptance_workflow)
                self.record_current_state_to_atptrail(origional_text, negotiation_workflow)
            else:
                self.record_current_state_to_atptrail(modification, acceptance_workflow)
                self.record_current_state_to_atptrail(modification, negotiation_workflow)
            self.record_current_state_to_atptrail(modification, modification_workflow)

        elif all([self.status == 2, self.award_dual_setup, self.award_dual_negotiation]):
            acceptance_object = self.get_current_award_acceptance()
            acceptance_object.acceptance_completion_date = timezone.localtime(timezone.now())
            acceptance_object.save()
            if count_value < 2:
                self.record_current_state_to_atptrail(origional_text, acceptance_workflow)
                self.record_current_state_to_atptrail(origional_text, negotiation_workflow)
                self.record_current_state_to_atptrail(origional_text, setup_workflow)
            else:
                self.record_current_state_to_atptrail(modification, acceptance_workflow)
                self.record_current_state_to_atptrail(modification, negotiation_workflow)
                self.record_current_state_to_atptrail(modification, setup_workflow)

        elif self.status == 2:
            acceptance_object = self.get_current_award_acceptance()
            acceptance_object.acceptance_completion_date = timezone.localtime(timezone.now())
            acceptance_object.save()
            if count_value < 2:
                self.record_current_state_to_atptrail(origional_text, acceptance_workflow)
                self.record_current_state_to_atptrail(origional_text, negotiation_workflow)
            else:
                self.record_current_state_to_atptrail(modification, acceptance_workflow)
                self.record_current_state_to_atptrail(modification, negotiation_workflow)

        elif self.status == 3:
            negotiation_user = self.get_user_for_section(negotiation_workflow)
            if negotiation_user:
                negotiation_object = self.get_current_award_negotiation()
                negotiation_object.negotiation_completion_date = timezone.localtime(timezone.now())
                negotiation_object.save()
                if count_value < 2:
                    self.record_current_state_to_atptrail(origional_text, negotiation_workflow)
                else:
                    self.record_current_state_to_atptrail(modification, negotiation_workflow)
            else:
                acceptance_object = self.get_current_award_acceptance()
                acceptance_object.acceptance_completion_date = timezone.localtime(timezone.now())
                acceptance_object.save()
                if count_value < 2:
                    self.record_current_state_to_atptrail(origional_text, acceptance_workflow)
                else:
                    self.record_current_state_to_atptrail(modification, acceptance_workflow)
            if all([not self.award_dual_modification, not self.send_to_modification, not self.award_dual_setup]):
                if count_value < 2:
                    self.record_current_state_to_atptrail(origional_text, setup_workflow)
                else:
                    self.record_current_state_to_atptrail(modification, setup_workflow)
            elif self.send_to_modification and not self.send_to_setup:
                self.record_current_state_to_atptrail(modification, modification_workflow)

        elif self.status == 4:
            if all([not self.award_dual_modification, not self.send_to_modification, not self.award_dual_setup]):
                setup_object = AwardSetup.objects.get(award=self)
                if setup_object.setup_completion_date and count_value == 1:
                    pass
                else:
                    setup_object.setup_completion_date = timezone.localtime(timezone.now())
                    setup_object.save()
                    if count_value < 2:
                        self.record_current_state_to_atptrail(origional_text, setup_workflow)
                    else:
                        self.record_current_state_to_atptrail(modification, setup_workflow)
            elif all([not self.send_to_modification, self.award_dual_setup, self.award_dual_negotiation]):
                pass
            elif all([self.award_dual_modification, self.common_modification]):
                pass
            elif self.award_dual_modification or self.send_to_modification:
                modification_object = AwardModification.objects.all().filter(award=self, is_edited=True).order_by('-id')
                if modification_object:
                    modification_obj = modification_object[0]
                    modification_obj.modification_completion_date = timezone.localtime(timezone.now())
                    modification_obj.save()
                self.record_current_state_to_atptrail(modification, modification_workflow)

            if self.subaward_user:
                if count_value < 2:
                    self.record_current_state_to_atptrail(origional_text, subaward_workflow)
                else:
                    self.record_current_state_to_atptrail(modification, subaward_workflow)
            if count_value < 2:
                self.record_current_state_to_atptrail(origional_text, management_workflow)
            else:
                self.record_current_state_to_atptrail(modification, management_workflow)

        elif self.status == 5:
            if count_value < 2:
                self.record_current_state_to_atptrail(origional_text, closeout_workflow)
            else:
                self.record_current_state_to_atptrail(modification, closeout_workflow)

        elif self.status == 6:
            closeout = AwardCloseout.objects.get(award=self)
            closeout.closeout_completion_date = timezone.localtime(timezone.now())
            closeout.save()
            if count_value < 2:
                self.record_current_state_to_atptrail(origional_text, closeout_workflow)
            else:
                self.record_current_state_to_atptrail(modification, closeout_workflow)

    def move_to_next_step(self, section=None):
        """Moves this Award to the next step in the process"""

        # A while loop because we want to advance the status until we find the next
        # section with an assigned user
        while True:
            # We have to do extra work to make sure both Subawards and Award Management
            # are complete before we move to the next status
            if section in ['Subaward', 'AwardManagement']:
                origional_text = 'Original Award'
                subaward_workflow = 'Subaward'
                management_workflow = 'AwardManagement'
                count_value = AwardAcceptance.objects.filter(award=self).count()
                modification = "Modification #%s" % (count_value - 1)
                if section == 'Subaward' or self.get_user_for_section(
                        'Subaward') is None:
                    self.subaward_done = True
                    if self.subaward_user:
                        if count_value < 2:
                            self.record_current_state_to_atptrail(origional_text, subaward_workflow)
                        else:
                            self.record_current_state_to_atptrail(modification, subaward_workflow)
                        try:
                            correct_instance = Subaward.objects.filter(award=self).latest('creation_date')
                            if correct_instance:
                                correct_instance.subaward_completion_date = timezone.localtime(timezone.now())
                                correct_instance.save()
                        except:
                            pass
                if section == 'AwardManagement' or self.get_user_for_section(
                        'AwardManagement') is None:
                    self.award_management_done = True
                    if count_value < 2:
                        self.record_current_state_to_atptrail(origional_text, management_workflow)
                    else:
                        self.record_current_state_to_atptrail(modification, management_workflow)
                    management_object = AwardManagement.objects.get(award=self)
                    management_object.management_completion_date = timezone.localtime(timezone.now())
                    management_object.save()

                if not (self.subaward_done and self.award_management_done):
                    self.save()
                    return False

            if self.status == 2 and self.award_dual_negotiation:
                self.award_dual_negotiation = False
                self.save()

            if self.status == 3 and self.award_dual_setup:
                self.award_dual_setup = False
                self.save()

            if self.status == 4 and self.award_dual_modification:
                self.award_dual_modification = False
                self.save()

            if self.status == 2 and self.send_to_modification:
                modification_object = AwardModification.objects.all().filter(award=self, is_edited=False).order_by('-id')
                if modification_object:
                    section_object = modification_object[0]
                    section_object.date_assigned = timezone.localtime(timezone.now())
                    section_object.save()

            self.status += 1

            if self.status == self.END_STATUS:
                self.save()
                break
            elif not all(user is None for user in self.get_users_for_active_sections()):
                self.set_date_assigned_for_active_sections()
                self.save()
                break

        if self.status not in (self.START_STATUS, self.END_STATUS) and not self.award_dual_setup:
            self.send_email_update()

        # Send an additional notification when we reach Award Setup
        if self.status == 3:
            self.awardsetup.copy_from_proposal(self.get_most_recent_proposal())

            self.send_award_setup_notification()
        if all([self.status == 3, self.subaward_user, not self.send_to_modification, not self.award_dual_setup]):
            self.send_email_update_if_subaward_user()
        self.update_completion_date_in_atp_award()
        return True

    def move_award_to_multiple_steps(self, dual_mode):
        """ Move award to multiple steps so that multiple teams can work parallel """
        if self.award_negotiation_user:
            self.status += 1
        else:
            if self.status == 1:
                self.status += 2
            try:
                setup_obj = AwardSetup.objects.get(award=self)
            except AwardSetup.DoesNotExist:
                setup_obj = None
            if setup_obj:
                setup_obj.date_assigned = timezone.localtime(timezone.now())
                setup_obj.save()

        if dual_mode:
            try:
                setup_object = AwardSetup.objects.get(award=self)
            except AwardSetup.DoesNotExist:
                setup_object = None
            try:
                negotiation_object = AwardNegotiation.objects.get(award=self, current_modification=True)
            except AwardNegotiation.DoesNotExist:
                negotiation_object = None

            if negotiation_object:
                negotiation_object.date_assigned = timezone.localtime(timezone.now())
                negotiation_object.save()

            if setup_object:
                setup_object.date_assigned = timezone.localtime(timezone.now())
                setup_object.save()

            self.award_dual_negotiation = True
            self.award_dual_setup = True

        self.save()
        if self.status not in (self.START_STATUS, self.END_STATUS):
            self.send_email_update()
        if all([self.status == 2, self.subaward_user, self.award_dual_setup]):
            self.send_email_update_if_subaward_user()
        self.update_completion_date_in_atp_award()
        return True

    def move_award_to_negotiation_and_modification(self, dual_modification):
        """ Move award to award negotiation and modification steps so that these two teams can work parallel """
        if self.award_negotiation_user:
            self.status += 1
            try:
                negotiation_object = AwardNegotiation.objects.get(award=self, current_modification=True)
            except AwardNegotiation.DoesNotExists:
                negotiation_object = None
            if negotiation_object:
                if not negotiation_object.date_assigned:
                    negotiation_object.date_assigned = timezone.localtime(timezone.now())
                    negotiation_object.save()
        else:
            if self.status == 1:
                self.status += 2
            try:
                setup_obj = AwardSetup.objects.get(award=self)
            except AwardSetup.DoesNotExist:
                setup_obj = None
            if setup_obj:
                setup_obj.date_assigned = timezone.localtime(timezone.now())
                setup_obj.save()

        modification_object = AwardModification.objects.all().filter(award=self).order_by('-id')
        if modification_object:
            section_object = modification_object[0]
            section_object.date_assigned = timezone.localtime(timezone.now())
            section_object.save()

        if dual_modification:
            self.common_modification = True
            self.award_dual_modification = True
        self.save()
        if self.status not in (self.START_STATUS, self.END_STATUS):
            self.send_email_update()
        self.update_completion_date_in_atp_award()
        return True

    def move_setup_or_modification_step(self, modification_flag=False, setup_flag=False):
        if self.award_negotiation_user:
            self.status += 1
            try:
                negotiation_object = AwardNegotiation.objects.get(award=self, current_modification=True)
            except AwardNegotiation.DoesNotExists:
                negotiation_object = None
            if negotiation_object:
                if not negotiation_object.date_assigned:
                    negotiation_object.date_assigned = timezone.localtime(timezone.now())
                    negotiation_object.save()
        else:
            if self.status == 1:
                self.status += 2
            try:
                setup_obj = AwardSetup.objects.get(award=self)
            except AwardSetup.DoesNotExist:
                setup_obj = None
            if setup_obj:
                setup_obj.date_assigned = timezone.localtime(timezone.now())
                setup_obj.save()

        if modification_flag:
            self.send_to_modification = True

        self.save()

        if setup_flag:
            self.send_email_update()
        if self.status == self.AWARD_SETUP_STATUS and modification_flag:
            self.send_email_update()

        # Send an additional notification when we reach Award Setup
        if self.status == 3:
            self.awardsetup.copy_from_proposal(self.get_most_recent_proposal())

        if modification_flag:
            try:
                modification = AwardModification.objects.get(award_id=self.id, is_edited=False)
            except AwardModification.DoesNotExist:
                modification = None

            if modification:
                modification.is_edited = True,
                modification.save()
            award_setup_object = AwardSetup.objects.filter(award=self).values()
            for setup in award_setup_object:
                del(setup['id'], setup['is_edited'], setup['setup_completion_date'], setup['wait_for_reson'])
                award_modification_object = AwardModification.objects.create(**setup)
            self.send_to_modification = True
            award_modification_object.save()
            self.save()
        self.update_completion_date_in_atp_award()
        return True

    # Django admin helper methods
    def get_section_admin_link(self, section):
        """Gets the link to the Django Admin site for the given section"""

        return format_html(
            '<a href="{0}">{1}</a>',
            reverse(
                'admin:awards_%s_change' %
                section.__class__.__name__.lower(),
                args=(
                    section.id,
                )),
            section)

    def get_foreignkey_admin_link(self, section_class):
        """Gets the link to the Django Admin site for the given section that has a 
        foreign key to this Award
        """
        section_objects = section_class.objects.filter(award=self)
        if len(section_objects) == 0:
            return '(None)'
        elif len(section_objects) == 1:
            return self.get_section_admin_link(section_objects[0])
        else:
            return format_html(
                '<a href="{0}?award__id__exact={1}">{2}s</a>',
                reverse(
                    'admin:awards_%s_changelist' %
                    section_class.__name__.lower()),
                self.id,
                section_class._meta.verbose_name.capitalize())

    # The following methods are referenced in the list_display section of the AwardAdmin class.
    # They return the Django Admin links to their respective sections

    def proposalintake_admin(self):
        return self.get_section_admin_link(self.proposalintake)

    def proposal_admin(self):
        return format_html('<a href="{0}?award__id__exact={1}">{2}</a>',
                           reverse('admin:awards_proposal_changelist'),
                           self.id,
                           'Proposals')

    def awardacceptance_admin(self):
        return self.get_foreignkey_admin_link(AwardAcceptance)

    def awardnegotiation_admin(self):
        return self.get_foreignkey_admin_link(AwardNegotiation)

    def awardsetup_admin(self):
        return self.get_section_admin_link(self.awardsetup)

    def subaward_admin(self):
        return self.get_foreignkey_admin_link(Subaward)

    def awardmanagement_admin(self):
        return self.get_section_admin_link(self.awardmanagement)

    def awardcloseout_admin(self):
        return self.get_section_admin_link(self.awardcloseout)


class AwardSection(FieldIteratorMixin, models.Model):
    """Abstract base class for all award sections"""
    HIDDEN_FIELDS = ['award', 'comments', 'is_edited']

    HIDDEN_SEARCH_FIELDS = []

    FIELDSETS = []

    comments = models.TextField(blank=True, verbose_name='Comments')
    is_edited = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def get_class_name(self):
        """Gets the Python class name"""

        return self.__class__.__name__

    def get_verbose_class_name(self):
        return self._meta.verbose_name

    def get_most_recent_revision(self):
        latest_revision = reversion.get_for_object(self)
        if latest_revision:
            latest_revision = latest_revision[0].revision
            user = latest_revision.user.get_full_name()
        else:
            user = 'ATP'
        if latest_revision:
            return (user, latest_revision.date_created)
        else:
            return (user, None)


class AssignableAwardSection(AwardSection):
    """Base model class for an Award section that can be assigned to a user"""

    date_assigned = models.DateTimeField(blank=True, null=True, verbose_name='Date Assigned')

    class Meta:
        abstract = True

    def set_date_assigned(self):
        self.date_assigned = datetime.now()
        self.save()


class ProposalIntake(AwardSection):
    """Model for the ProposalIntake data"""
    user_list = User.objects.filter(is_active=True).order_by('first_name')
    users = [(user.first_name + ' ' + user.last_name, user.first_name + ' ' + user.last_name) for user in user_list]
    PROPOSAL_STATUS_CHOICES = (
        ('NS', 'Cancelled - not submitted'),
        ('PE', 'Planned'),
        ('RO', 'Routing'),
        ('SB', 'Submitted'),
    )

    PROPOSAL_OUTCOME_CHOICES = (
        ('AW', 'Awarded'),
        ('UN', 'Unfunded'),
    )
    SPA1_CHOICES = (
        ('', ''),
    )
    SPA1_CHOICES = tuple(users) if users else SPA1_CHOICES
    HIDDEN_SEARCH_FIELDS = AwardSection.HIDDEN_SEARCH_FIELDS + [
        'principal_investigator',
        'agency',
        'prime_sponsor',
        'program_announcement',
        'announcement_link',
        'proposal_due_to_sponsor',
        'proposal_due_to_ovpr',
        'proposal_due_to_aor',
        'school',
        'phs_funded',
        'fcoi_submitted',
        'date_received',
        'proposal_status',
        'proposal_outcome',
        'proposal_number',
        'five_days_requested',
        'five_days_granted',
        'jit_request',
        'jit_response_submitted',
        'creation_date']

    minimum_fields = (

    )

    award = models.OneToOneField(Award, null=True, blank=True)
    creation_date = models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name='Date Created')

    principal_investigator = models.ForeignKey(
        AwardManager,
        blank=True,
        null=True,
        limit_choices_to={
            'active': True},
        verbose_name='Principal Investigator')
    agency = models.CharField(max_length=255, blank=True)
    prime_sponsor = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Prime (if GW is subawardee)')
    program_announcement = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Program announcement number')
    announcement_link = models.CharField(max_length=250, blank=True)
    proposal_due_to_sponsor = models.DateField(null=True, blank=True)
    proposal_due_to_ovpr = models.DateField(
        null=True,
        blank=True,
        verbose_name='Proposal due to OVPR')
    proposal_due_to_aor = models.DateField(
        null=True,
        blank=True,
        verbose_name='Proposal due to AOR')
    spa1 = models.CharField(blank=False, verbose_name='SPA I*', max_length=150, choices=SPA1_CHOICES, null=True)
    school = models.CharField(max_length=150, blank=True)
    department = models.ForeignKey(
        AwardOrganization,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True},
        verbose_name='Department')
    phs_funded = models.NullBooleanField(verbose_name='PHS funded?')
    fcoi_submitted = models.NullBooleanField(
        verbose_name='FCOI disclosure submitted for each investigator?')
    date_received = models.DateField(
        null=True,
        blank=True,
        verbose_name='Date received by SPA I')
    proposal_status = models.CharField(
        choices=PROPOSAL_STATUS_CHOICES,
        max_length=2,
        blank=True)
    proposal_outcome = models.CharField(
        choices=PROPOSAL_OUTCOME_CHOICES,
        max_length=2,
        blank=True)
    proposal_number = models.CharField(max_length=15, blank=True, verbose_name="Cayuse Proposal Number")
    five_days_requested = models.DateField(
        null=True,
        blank=True,
        verbose_name='Date 5 days waiver requested')
    five_days_granted = models.DateField(
        null=True,
        blank=True,
        verbose_name='Date 5 days waiver granted')
    jit_request = models.NullBooleanField(verbose_name='JIT request?')
    jit_response_submitted = models.DateField(
        null=True,
        blank=True,
        verbose_name='JIT response submitted?')
    five_days_waiver_request = models.NullBooleanField(
        null=True,
        blank=True,
        verbose_name="5 day waiver granted?")

    def __unicode__(self):
        return u'Proposal Intake %s' % (self.id)

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object"""

        if self.award:
            return reverse(
                'edit_proposal_intake',
                kwargs={
                    'award_pk': self.award.pk})
        else:
            return reverse(
                'edit_standalone_proposal_intake',
                kwargs={
                    'proposalintake_pk': self.id})

    def get_proposal_status(self):
        """Gets the human-readable value of the Proposal's status"""

        return get_value_from_choices(self.PROPOSAL_STATUS_CHOICES, self.proposal_status)

    def get_proposal_outcome(self):

        return get_value_from_choices(self.PROPOSAL_OUTCOME_CHOICES, self.proposal_outcome)


class Proposal(AwardSection):
    """Model for the Proposal data"""

    # HIDDEN_FIELDS aren't rendered by FieldIteratorMixin
    HIDDEN_FIELDS = AwardSection.HIDDEN_FIELDS + [
        'dummy',
        'is_first_proposal',
        'lotus_id',
        'lotus_agency_name',
        'lotus_department_code',
        'employee_id',
        'proposal_id']

    HIDDEN_SEARCH_FIELDS = AwardSection.HIDDEN_SEARCH_FIELDS + [
        'creation_date',
        'sponsor_deadline',
        'is_subcontract',
        'federal_identifier',
        'is_change_in_grantee_inst',
        'responsible_entity',
        'departmental_id_primary',
        'departmental_id_secondary',
        'departmental_name_primary',
        'departmental_name_secondary',
        'are_vertebrate_animals_used',
        'is_iacuc_review_pending',
        'iacuc_protocol_number',
        'iacuc_approval_date',
        'are_human_subjects_used',
        'is_irb_review_pending',
        'irb_protocol_number',
        'irb_review_date',
        'budget_first_per_start_date',
        'budget_first_per_end_date',
        'cost_shr_mand_is_committed',
        'cost_shr_mand_source',
        'cost_shr_vol_is_committed',
        'cost_shr_vol_source',
        'tracking_number',
        'total_costs_y1',
        'total_costs_y2',
        'total_costs_y3',
        'total_costs_y4',
        'total_costs_y5',
        'total_costs_y6',
        'total_costs_y7',
        'total_costs_y8',
        'total_costs_y9',
        'total_costs_y10',
        'total_direct_costs_y1',
        'total_direct_costs_y2',
        'total_direct_costs_y3',
        'total_direct_costs_y4',
        'total_direct_costs_y5',
        'total_direct_costs_y6',
        'total_direct_costs_y7',
        'total_direct_costs_y8',
        'total_direct_costs_y9',
        'total_direct_costs_y10',
        'total_indirect_costs_y1',
        'total_indirect_costs_y2',
        'total_indirect_costs_y3',
        'total_indirect_costs_y4',
        'total_indirect_costs_y5',
        'total_indirect_costs_y6',
        'total_indirect_costs_y7',
        'total_indirect_costs_y8',
        'total_indirect_costs_y9',
        'total_indirect_costs_y10']

    # Fieldsets are grouped together at the top of the section under the title
    FIELDSETS = [{'title': 'Proposal Summary',
                  'fields': ('creation_date',
                             'proposal_number',
                             'proposal_title',
                             'proposal_type',
                             'principal_investigator',
                             'project_title',
                             'department_name',
                             'division_name',
                             'agency_name',
                             'is_subcontract',
                             'who_is_prime',
                             'tracking_number',
                             'project_start_date',
                             'project_end_date',
                             'submission_date',
                             'sponsor_deadline'
                             )},
                  {'title': 'Project Data',
                   'fields': ('agency_type',
                              'application_type_code',
                              'federal_identifier',
                              'is_change_in_grantee_inst',
                              'project_type'
                              )},
                   {'title': 'Project Administration',
                    'fields': ('responsible_entity',
                               'departmental_id_primary',
                               'departmental_id_secondary',
                               'departmental_name_primary',
                               'departmental_name_secondary'
                              )},
                   {'title': 'Compliance: Animal Subjects',
                    'fields': ('are_vertebrate_animals_used',
                               'is_iacuc_review_pending',
                               'iacuc_protocol_number',
                               'iacuc_approval_date'
                              )},
                   {'title': 'Compliance: Human Subjects',
                    'fields': ('are_human_subjects_used',
                               'is_irb_review_pending',
                               'irb_protocol_number',
                               'irb_review_date'
                              )},
                   {'title': 'Compliance: Lab Safety',
                    'fields': ('is_haz_mat',
                              )},
                   {'title': 'Compliance: Export Controls',
                    'fields': ('will_involve_foreign_nationals',
                               'will_involve_shipment',
                               'will_involve_foreign_contract'
                              )},
                   {'title': 'Budget Data',
                    'fields': ('budget_first_per_start_date',
                               'budget_first_per_end_date',
                               'cost_shr_mand_is_committed',
                               'cost_shr_mand_amount',
                               'cost_shr_mand_source',
                               'cost_shr_vol_is_committed',
                               'cost_shr_vol_amount',
                               'cost_shr_vol_source'
                              )}
                 ]

    # Display tables are displayed at the end of a section in an HTML table
    DISPLAY_TABLES = [
        {
        'title': 'Budgeted Costs', 'columns': (
        'Direct Costs', 'Indirect Costs', 'Total Costs'), 'rows': [
        {
        'label': 'Total', 'fields': (
            'total_direct_costs', 'total_indirect_costs', 'total_costs')}, {
        'label': 'Y1', 'fields': (
            'total_direct_costs_y1', 'total_indirect_costs_y1', 'total_costs_y1')}, {
        'label': 'Y2', 'fields': (
            'total_direct_costs_y2', 'total_indirect_costs_y2', 'total_costs_y2')}, {
        'label': 'Y3', 'fields': (
            'total_direct_costs_y3', 'total_indirect_costs_y3', 'total_costs_y3')}, {
        'label': 'Y4', 'fields': (
            'total_direct_costs_y4', 'total_indirect_costs_y4', 'total_costs_y4')}, {
        'label': 'Y5', 'fields': (
            'total_direct_costs_y5', 'total_indirect_costs_y5', 'total_costs_y5')}, {
        'label': 'Y6', 'fields': (
            'total_direct_costs_y6', 'total_indirect_costs_y6', 'total_costs_y6')}, {
        'label': 'Y7', 'fields': (
            'total_direct_costs_y7', 'total_indirect_costs_y7', 'total_costs_y7')}, {
        'label': 'Y8', 'fields': (
            'total_direct_costs_y8', 'total_indirect_costs_y8', 'total_costs_y8')}, {
        'label': 'Y9', 'fields': (
            'total_direct_costs_y9', 'total_indirect_costs_y9', 'total_costs_y9')}, {
        'label': 'Y10', 'fields': (
            'total_direct_costs_y10', 'total_indirect_costs_y10', 'total_costs_y10')}, ]
        }
    ]

    # Entries here appear on the EAS Award Setup report screen
    EAS_REPORT_FIELDS = [
        'proposal_id',
        'project_title',
        'department_name',
        'is_subcontract',
        'who_is_prime',
        'agency_name',
    ]

    # A small mapping to help figure out which field data to use when conforming
    # Lotus Notes legacy data to EAS data when importing a proposal from Lotus
    LOTUS_FK_LOOKUPS = {
        'lotus_agency_name': 'agency_name',
        'lotus_department_code': 'department_name',
        'employee_id': 'principal_investigator'
    }

    award = models.ForeignKey(
        Award,
        null=True,
        blank=True,
        on_delete=models.SET_NULL)
    dummy = models.BooleanField(default=False)
    is_first_proposal = models.BooleanField(default=False)

    creation_date = models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name='Date Created')
    lotus_id = models.CharField(max_length=20, blank=True)

    employee_id = models.CharField(
        max_length=40,
        blank=True,
        verbose_name='Employee ID')
    proposal_id = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
        verbose_name='Proposal ID')
    proposal_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Proposal Number')
    proposal_title = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Internal Proposal Title')
    proposal_type = models.CharField(max_length=256, blank=True)
    principal_investigator = models.ForeignKey(
        AwardManager,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True},
        verbose_name='Principal Investigator')
    project_title = models.CharField(max_length=255, blank=True)
    lotus_department_code = models.CharField(max_length=128, blank=True)
    department_name = models.ForeignKey(
        AwardOrganization,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True},
        verbose_name='Department Code & Name')
    division_name = models.CharField(max_length=150, blank=True)
    agency_name = models.ForeignKey(
        FundingSource,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True})
    is_subcontract = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Is this a subcontract?')
    who_is_prime = models.ForeignKey(
        PrimeSponsor,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True},
        verbose_name='Prime Sponsor')
    tracking_number = models.CharField(
        max_length=15,
        blank=True,
        verbose_name='Grants.gov tracking number')
    project_start_date = models.DateField(null=True, blank=True)
    project_end_date = models.DateField(null=True, blank=True)
    submission_date = models.DateField(null=True, blank=True)
    sponsor_deadline = models.DateField(null=True, blank=True)
    lotus_agency_name = models.CharField(max_length=250, blank=True)
    project_title = models.CharField(max_length=256, blank=True)
    agency_type = models.CharField(max_length=256, blank=True)
    application_type_code = models.CharField(
        max_length=25,
        blank=True,
        verbose_name='Kind of application')
    federal_identifier = models.CharField(max_length=256, blank=True, verbose_name='Previous Grant #')
    is_change_in_grantee_inst = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Change in grantee institution?')
    project_type = models.CharField(max_length=256, blank=True)
    responsible_entity = models.CharField(max_length=256, blank=True)
    departmental_id_primary = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Departmental ID primary')
    departmental_id_secondary = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='Departmental ID secondary')
    departmental_name_primary = models.CharField(max_length=256, blank=True)
    departmental_name_secondary = models.CharField(max_length=256, blank=True)
    are_vertebrate_animals_used = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Are vertebrate animals used?')
    is_iacuc_review_pending = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Is IACUC review pending?')
    iacuc_protocol_number = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='IACUC protocol number')
    iacuc_approval_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='IACUC approval date')
    are_human_subjects_used = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Are human subjects used?')
    is_irb_review_pending = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Is IRB review pending?')
    irb_protocol_number = models.CharField(
        max_length=256,
        blank=True,
        verbose_name='IRB protocol number')
    irb_review_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='IRB review date')
    is_haz_mat = models.CharField(max_length=10, blank=True, verbose_name='Uses hazardous materials')
    budget_first_per_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Budget first period start date')
    budget_first_per_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Budget first period end date')
    cost_shr_mand_is_committed = models.CharField(max_length=10, blank=True)
    cost_shr_mand_amount = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    cost_shr_mand_source = models.CharField(max_length=256, blank=True)
    cost_shr_vol_is_committed = models.CharField(max_length=10, blank=True)
    cost_shr_vol_amount = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    cost_shr_vol_source = models.CharField(max_length=256, blank=True)
    will_involve_foreign_nationals = models.CharField(
        max_length=10,
        blank=True)
    will_involve_shipment = models.CharField(max_length=10, blank=True)
    will_involve_foreign_contract = models.CharField(max_length=10, blank=True)

    total_costs = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_costs_y1 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_costs_y2 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_costs_y3 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_costs_y4 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_costs_y5 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_costs_y6 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_costs_y7 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_costs_y8 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_costs_y9 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_costs_y10 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_direct_costs = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_direct_costs_y1 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_direct_costs_y2 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_direct_costs_y3 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_direct_costs_y4 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_direct_costs_y5 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_direct_costs_y6 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_direct_costs_y7 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_direct_costs_y8 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_direct_costs_y9 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_direct_costs_y10 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_indirect_costs = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_indirect_costs_y1 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_indirect_costs_y2 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_indirect_costs_y3 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_indirect_costs_y4 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_indirect_costs_y5 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_indirect_costs_y6 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_indirect_costs_y7 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_indirect_costs_y8 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_indirect_costs_y9 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    total_indirect_costs_y10 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)

    def __unicode__(self):
        return u'Proposal #%s' % (self.get_unique_identifier())

    class Meta:
        index_together = [
            ["award", "is_first_proposal"],
        ]

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object"""

        return reverse(
            'edit_proposal',
            kwargs={
                'award_pk': self.award.pk,
                'proposal_pk': self.id})

    def get_unique_identifier(self):
        """Gets a value that uniquely identifies this Proposal"""
        return self.proposal_number

    def save(self, *args, **kwargs):
        """Overrides the parent save method.
        If this is a new Proposal, copy certain fields over to the AwardAcceptance object
        """

        if not self.dummy and not self.pk:
            try:
                award_intake = self.award.get_current_award_acceptance()
                award_intake.copy_from_proposal(self)
            except:
                pass
        super(Proposal, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Overrides the parent delete method.
        If this Proposal came from Lotus, just remove the reference to the Award instead of
        deleting from the database.
        """
        if self.lotus_id:
            self.award = None
            self.save()
        else:
            super(Proposal, self).delete(*args, **kwargs)


def set_first_proposal(award, proposals):
    """Set the is_first_proposal flag on the appropriate proposal"""
    proposals.update(is_first_proposal=False)
    first_proposal = proposals.order_by('id').first()

    first_proposal.is_first_proposal = True
    first_proposal.save()


@receiver(post_delete, sender=Proposal)
@receiver(post_save, sender=Proposal)
def check_first_proposal(sender, instance, **kwargs):
    """Use Django signals to keep the is_first_proposal flag up to date"""
    try:
        award = instance.award
    except Award.DoesNotExist:
        award = None

    if not award:
        return

    proposals = Proposal.objects.filter(award=award)
    try:
        dummy_proposal = Proposal.objects.get(award=award, dummy=True)
    except Proposal.DoesNotExist:
        dummy_proposal = None

    if len(proposals) == 0:
        Proposal.objects.create(award=award, dummy=True)
        return
    elif len(proposals) > 1 and dummy_proposal:
        dummy_proposal.delete()

    first_proposals = Proposal.objects.filter(
        award=award,
        is_first_proposal=True)
    if len(first_proposals) != 1:
        set_first_proposal(award, proposals)


class KeyPersonnel(FieldIteratorMixin, models.Model):
    """Model for the KeyPersonnel data"""

    HIDDEN_FIELDS = ['proposal']

    HIDDEN_TABLE_FIELDS = []

    proposal = models.ForeignKey(Proposal)

    employee_id = models.CharField(
        max_length=40,
        blank=True,
        verbose_name='Emp ID')
    last_name = models.CharField(max_length=64, blank=True)
    first_name = models.CharField(max_length=64, blank=True)
    middle_name = models.CharField(max_length=32, blank=True)
    project_role = models.CharField(max_length=128, blank=True)
    calendar_months = models.DecimalField(
        decimal_places=3,
        max_digits=5,
        null=True,
        blank=True,
        verbose_name='Calendar mos.')
    academic_months = models.DecimalField(
        decimal_places=3,
        max_digits=5,
        null=True,
        blank=True,
        verbose_name='Academic mos.')
    summer_months = models.DecimalField(
        decimal_places=3,
        max_digits=5,
        null=True,
        blank=True,
        verbose_name='Summer mos.')
    effort = models.CharField(max_length=10, blank=True)

    def __unicode__(self):
        return u'%s, %s %s on %s' % (
            self.last_name, self.first_name, self.middle_name, self.proposal)

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object"""

        return reverse(
            'edit_key_personnel',
            kwargs={
                'award_pk': self.proposal.award.pk,
                'proposal_pk': self.proposal.pk,
                'key_personnel_pk': self.id})

    def get_delete_url(self):
        """Gets the URL used to delete this object"""

        return reverse(
            'delete_key_personnel',
            kwargs={
                'award_pk': self.proposal.award.pk,
                'proposal_pk': self.proposal.pk,
                'key_personnel_pk': self.id})


class PerformanceSite(FieldIteratorMixin, models.Model):
    """Model for the PerformanceSite data"""

    HIDDEN_FIELDS = ['proposal']

    HIDDEN_TABLE_FIELDS = []

    proposal = models.ForeignKey(Proposal)

    ps_organization = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Organization')
    ps_duns = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='DUNS')
    ps_street1 = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Street 1')
    ps_street2 = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Street 2')
    ps_city = models.CharField(max_length=255, blank=True, verbose_name='City')
    ps_state = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='State')
    ps_zipcode = models.CharField(
        max_length=128,
        blank=True,
        verbose_name='Zip')
    ps_country = models.CharField(
        max_length=128,
        blank=True,
        verbose_name='Country')

    def __unicode__(self):
        return u'%s %s, %s' % (self.ps_street1, self.ps_city, self.ps_state)

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object"""

        return reverse(
            'edit_performance_site',
            kwargs={
                'award_pk': self.proposal.award.pk,
                'proposal_pk': self.proposal.pk,
                'performance_site_pk': self.id})

    def get_delete_url(self):
        """Gets the URL used to delete this object"""

        return reverse(
            'delete_performance_site',
            kwargs={
                'award_pk': self.proposal.award.pk,
                'proposal_pk': self.proposal.pk,
                'performance_site_pk': self.id})


class AwardModificationMixin(object):
    """Mixin used for Award sections that can have modifications"""

    def clean(self, *args, **kwargs):
        """Overrides the base clean method.  Verifies there are no other current modifications."""

        section = self.__class__
        active_modifications = section.objects.filter(
            award=self.award,
            current_modification=True).exclude(
            pk=self.id)
        if self.current_modification and len(active_modifications) > 0:
            raise ValidationError(
                'Another %s is already the current modification for %s. \
                    Set "current modification" on all other %s objects and try again.' %
                (section.__name__, self.award, section.__name__))
        super(AwardModificationMixin, self).clean(*args, **kwargs)


class AwardAcceptance(AwardModificationMixin, AwardSection):
    """Model for the AwardAcceptance data"""

    EAS_STATUS_CHOICES = (
        ('A', 'Active'),
        ('OH', 'On hold'),
        ('AR', 'At risk'),
        ('C', 'Closed')
    )
    PRIORITY_STATUS_CHOICES = (
        ('on', 1),
        ('tw', 2),
        ('th', 3),
        ('fo', 4),
        ('fi', 5),
        ('ni', 9)
    )
    PRIORITY_STATUS_DICT = {'on': 1,
                            'tw': 2,
                            'th': 3,
                            'fo': 4,
                            'fi': 5,
                            'ni': 9
                            }
    HIDDEN_FIELDS = AwardSection.HIDDEN_FIELDS + ['current_modification', 'award_text']

    HIDDEN_SEARCH_FIELDS = AwardSection.HIDDEN_SEARCH_FIELDS + [
        'fcoi_cleared_date',
        'project_title',
        'full_f_a_recovery',
        'explanation',
        'mfa_investigators',
        'award_total_costs_y1',
        'award_total_costs_y2',
        'award_total_costs_y3',
        'award_total_costs_y4',
        'award_total_costs_y5',
        'award_total_costs_y6',
        'award_total_costs_y7',
        'award_total_costs_y8',
        'award_total_costs_y9',
        'award_total_costs_y10',
        'award_direct_costs_y1',
        'award_direct_costs_y2',
        'award_direct_costs_y3',
        'award_direct_costs_y4',
        'award_direct_costs_y5',
        'award_direct_costs_y6',
        'award_direct_costs_y7',
        'award_direct_costs_y8',
        'award_direct_costs_y9',
        'award_direct_costs_y10',
        'award_indirect_costs_y1',
        'award_indirect_costs_y2',
        'award_indirect_costs_y3',
        'award_indirect_costs_y4',
        'award_indirect_costs_y5',
        'award_indirect_costs_y6',
        'award_indirect_costs_y7',
        'award_indirect_costs_y8',
        'award_indirect_costs_y9',
        'award_indirect_costs_y10',
        'contracting_official',
        'gmo_co_email',
        'gmo_co_phone_number',
        'creation_date']

    DISPLAY_TABLES = [
        {
        'title': 'Costs', 'columns': (
            'Total Direct Costs', 'Total Indirect Costs', 'Total Costs'), 'rows': [
        {
        'label': 'Total', 'fields': (
            'award_direct_costs', 'award_indirect_costs', 'award_total_costs')}, {
        'label': 'Y1', 'fields': (
            'award_direct_costs_y1', 'award_indirect_costs_y1', 'award_total_costs_y1')}, {
        'label': 'Y2', 'fields': (
            'award_direct_costs_y2', 'award_indirect_costs_y2', 'award_total_costs_y2')}, {
        'label': 'Y3', 'fields': (
            'award_direct_costs_y3', 'award_indirect_costs_y3', 'award_total_costs_y3')}, {
        'label': 'Y4', 'fields': (
            'award_direct_costs_y4', 'award_indirect_costs_y4', 'award_total_costs_y4')}, {
        'label': 'Y5', 'fields': (
            'award_direct_costs_y5', 'award_indirect_costs_y5', 'award_total_costs_y5')}, {
        'label': 'Y6', 'fields': (
            'award_direct_costs_y6', 'award_indirect_costs_y6', 'award_total_costs_y6')}, {
        'label': 'Y7', 'fields': (
            'award_direct_costs_y7', 'award_indirect_costs_y7', 'award_total_costs_y7')}, {
        'label': 'Y8', 'fields': (
            'award_direct_costs_y8', 'award_indirect_costs_y8', 'award_total_costs_y8')}, {
        'label': 'Y9', 'fields': (
            'award_direct_costs_y9', 'award_indirect_costs_y9', 'award_total_costs_y9')}, {
        'label': 'Y10', 'fields': (
            'award_direct_costs_y10', 'award_indirect_costs_y10', 'award_total_costs_y10')}, ]
        }
    ]

    EAS_REPORT_FIELDS = [
        'eas_status',
        'award_issue_date',
        'award_acceptance_date',
        'sponsor_award_number',
        'agency_award_number',
    ]

    # These fields must have values before this section can be completed
    minimum_fields = (
        'award_issue_date',
    )

    award = models.ForeignKey(Award)
    creation_date = models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name='Date Created')
    current_modification = models.BooleanField(default=True)

    eas_status = models.CharField(
        choices=EAS_STATUS_CHOICES,
        max_length=2,
        blank=True,
        verbose_name='EAS status')
    new_funding = models.NullBooleanField(verbose_name='New Funding?')
    fcoi_cleared_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='FCOI cleared date')
    phs_funded = models.NullBooleanField(verbose_name='PHS funded?')
    award_setup_priority = models.CharField(
        choices=PRIORITY_STATUS_CHOICES,
        max_length=2,
        blank=True,
        verbose_name='Award Setup Priority'
    )
    priority_by_director = models.NullBooleanField(blank=True, null=True, verbose_name='Prioritized by Director?')
    project_title = models.CharField(
        max_length=250,
        blank=True,
        verbose_name='Project Title (if different from Proposal)')
    foreign_travel = models.NullBooleanField(verbose_name='Foreign Travel?')
    f_a_rate = models.CharField(
        max_length=250,
        blank=True,
        verbose_name='F&A rate')
    full_f_a_recovery = models.NullBooleanField(
        verbose_name='Full F&A Recovery?')
    explanation = models.CharField(
        max_length=250,
        blank=True,
        verbose_name='If no full F&A, provide explanation')
    mfa_investigators = models.NullBooleanField(
        verbose_name='MFA investigators?')
    admin_establishment = models.NullBooleanField(
        verbose_name='Administrative establishment?')
    award_issue_date = models.DateField(null=True, blank=True)
    award_acceptance_date = models.DateField(null=True, blank=True)
    agency_award_number = models.CharField(max_length=50, blank=True)
    sponsor_award_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Prime Award # (if GW is subawardee)')

    award_total_costs = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True,
        verbose_name='Total award costs')
    award_direct_costs = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True,
        verbose_name='Total award direct costs')
    award_indirect_costs = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True,
        verbose_name='Total award indirect costs')
    award_total_costs_y1 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_direct_costs_y1 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_indirect_costs_y1 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_total_costs_y2 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_direct_costs_y2 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_indirect_costs_y2 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_total_costs_y3 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_direct_costs_y3 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_indirect_costs_y3 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_total_costs_y4 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_direct_costs_y4 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_indirect_costs_y4 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_total_costs_y5 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_direct_costs_y5 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_indirect_costs_y5 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_total_costs_y6 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_direct_costs_y6 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_indirect_costs_y6 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_total_costs_y7 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_direct_costs_y7 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_indirect_costs_y7 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_total_costs_y8 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_direct_costs_y8 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_indirect_costs_y8 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_total_costs_y9 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_direct_costs_y9 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_indirect_costs_y9 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_total_costs_y10 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_direct_costs_y10 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)
    award_indirect_costs_y10 = models.DecimalField(
        decimal_places=2,
        max_digits=15,
        null=True,
        blank=True)

    contracting_official = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='GMO or CO')
    gmo_co_phone_number = models.CharField(
        max_length=15,
        blank=True,
        verbose_name='GMO/CO phone number')
    gmo_co_email = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='GMO/CO email')
    pta_modification = models.NullBooleanField(verbose_name='Do you want to send this to the post-award team for modification?')
    acceptance_completion_date = models.DateTimeField(blank=True, null=True, verbose_name='Completion Date')
    award_text = models.CharField(max_length=50, blank=True, null=True)

    def __unicode__(self):
        return u'Award Intake %s' % (self.id)

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object."""

        return reverse(
            'edit_award_acceptance',
            kwargs={
                'award_pk': self.award.pk})

    def copy_from_proposal(self, proposal):
        """Copies common fields to this object from the given Proposal."""

        self.project_title = proposal.project_title

        self.award_total_costs = proposal.total_costs
        self.award_total_costs_y1 = proposal.total_costs_y1
        self.award_total_costs_y2 = proposal.total_costs_y2
        self.award_total_costs_y3 = proposal.total_costs_y3
        self.award_total_costs_y4 = proposal.total_costs_y4
        self.award_total_costs_y5 = proposal.total_costs_y5
        self.award_total_costs_y6 = proposal.total_costs_y6
        self.award_total_costs_y7 = proposal.total_costs_y7
        self.award_total_costs_y8 = proposal.total_costs_y8
        self.award_total_costs_y9 = proposal.total_costs_y9
        self.award_total_costs_y10 = proposal.total_costs_y10

        self.award_direct_costs = proposal.total_direct_costs
        self.award_direct_costs_y1 = proposal.total_direct_costs_y1
        self.award_direct_costs_y2 = proposal.total_direct_costs_y2
        self.award_direct_costs_y3 = proposal.total_direct_costs_y3
        self.award_direct_costs_y4 = proposal.total_direct_costs_y4
        self.award_direct_costs_y5 = proposal.total_direct_costs_y5
        self.award_direct_costs_y6 = proposal.total_direct_costs_y6
        self.award_direct_costs_y7 = proposal.total_direct_costs_y7
        self.award_direct_costs_y8 = proposal.total_direct_costs_y8
        self.award_direct_costs_y9 = proposal.total_direct_costs_y9
        self.award_direct_costs_y10 = proposal.total_direct_costs_y10

        self.award_indirect_costs = proposal.total_indirect_costs
        self.award_indirect_costs_y1 = proposal.total_indirect_costs_y1
        self.award_indirect_costs_y2 = proposal.total_indirect_costs_y2
        self.award_indirect_costs_y3 = proposal.total_indirect_costs_y3
        self.award_indirect_costs_y4 = proposal.total_indirect_costs_y4
        self.award_indirect_costs_y5 = proposal.total_indirect_costs_y5
        self.award_indirect_costs_y6 = proposal.total_indirect_costs_y6
        self.award_indirect_costs_y7 = proposal.total_indirect_costs_y7
        self.award_indirect_costs_y8 = proposal.total_indirect_costs_y8
        self.award_indirect_costs_y9 = proposal.total_indirect_costs_y9
        self.award_indirect_costs_y10 = proposal.total_indirect_costs_y10

        self.save()

    class Meta:
        verbose_name = 'Award intake'
        verbose_name_plural = 'Award intakes'

    def save(self, *args, **kwargs):
        """Overrides the base save method.
        If it was an existing AwardAcceptance, check to see if FCOI and/or PHS funded
        emails need to be sent.
        """

        try:
            old_object = AwardAcceptance.objects.get(pk=self.pk)
        except AwardAcceptance.DoesNotExist:
            super(AwardAcceptance, self).save(*args, **kwargs)
            return

        super(AwardAcceptance, self).save(*args, **kwargs)

        # Send email to Award Setup user when FCOI cleared date is populated
        if not old_object.fcoi_cleared_date and self.fcoi_cleared_date:
            self.award.send_fcoi_cleared_notification(self.fcoi_cleared_date)

        if not old_object.phs_funded and self.phs_funded:
            self.award.send_phs_funded_notification()


class NegotiationStatus(models.Model):

    NEGOTIATION_CHOICES = (
        ('IQ', 'In queue'),
        ('IP', 'In progress'),
        ('WFS', 'Waiting for sponsor'),
        ('WFP', 'Waiting for PI'),
        ('WFO', 'Waiting for other department'),
        ('CD', 'Completed'),
        ('UD', 'Unrealized')
    )
    NEGOTIATION_STATUS_CHOICES = (
        'In queue',
        'In progress',
        'Waiting for sponsor',
        'Waiting for PI',
        'Waiting for other department',
        'Completed',
        'Unrealized'
    )

    NEGOTIATION_CHOICES_DICT = {'IQ': 'In queue',
                                'IP': 'In progress',
                                'WFS': 'Waiting for sponsor',
                                'WFP': 'Waiting for PI',
                                'WFO': 'Waiting for other department',
                                'CD': 'Completed',
                                'UD': 'Unrealized'
                                }
    negotiation_status = models.CharField(
        choices=NEGOTIATION_CHOICES,
        max_length=50,
        blank=True)
    negotiation_status_changed_user = models.CharField(
        max_length=100,
        blank=True)
    negotiation_notes = models.TextField(
        blank=True)
    award = models.ForeignKey(Award)
    negotiation_status_date = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return u'%s  Status %s' % (self.award, self.negotiation_status)


class AwardNegotiation(AwardModificationMixin, AssignableAwardSection):
    """Model for the AwardNegotiation data"""

    AWARD_TYPE_CHOICES = (
        ('CR', 'Contract: Cost-reimbursable'),
        ('FP', 'Contract: Fixed price'),
        ('TM', 'Contract: Time & materials'),
        ('GC', 'Grant: Cost-reimbursable'),
        ('GF', 'Grant: Fixed amount award'),
        ('CA', 'Cooperative agreement'),
        ('CD', 'CRADA'),
        ('ND', 'NDA'),
        ('TA', 'Teaming agreement'),
        ('DU', 'DUA'),
        ('RF', 'RFP'),
        ('MT', 'MTA'),
        ('MA', 'Master agreement'),
        ('OT', 'Other')
    )

    NEGOTIATION_CHOICES = (
        ('IQ', 'In queue'),
        ('IP', 'In progress'),
        ('WFS', 'Waiting for sponsor'),
        ('WFP', 'Waiting for PI'),
        ('WFO', 'Waiting for other department'),
        ('CD', 'Completed'),
        ('UD', 'Unrealized')
    )

    HIDDEN_FIELDS = AwardSection.HIDDEN_FIELDS + ['current_modification', 'date_received', 'award_text']

    HIDDEN_SEARCH_FIELDS = AwardSection.HIDDEN_SEARCH_FIELDS + [
        'subcontracting_plan',
        'under_master_agreement',
        'retention_period',
        'gw_doesnt_own_ip',
        'gw_background_ip',
        'foreign_restrictions',
        'certificates_insurance',
        'insurance_renewal',
        'government_property',
        'everify',
        'date_assigned']

    EAS_REPORT_FIELDS = [
        'award_type',
    ]

    minimum_fields = (
        'award_type',
    )

    award = models.ForeignKey(Award)
    current_modification = models.BooleanField(default=True)

    subcontracting_plan = models.NullBooleanField(
        verbose_name='Is Small Business Subcontracting Plan required?')
    under_master_agreement = models.NullBooleanField(
        verbose_name='Under Master Agreement?')
    award_type = models.CharField(
        choices=AWARD_TYPE_CHOICES,
        max_length=3,
        blank=True,
        verbose_name='Award Type')
    other_award_type = models.CharField(max_length=255, blank=True)
    related_other_agreements = models.NullBooleanField(
        verbose_name='Related Other Agreements?')
    related_other_comments = models.TextField(
        blank=True,
        verbose_name='Related other agreements comments')
    negotiator = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Negotiator Assist')
    date_received = models.DateField(
        null=True,
        blank=True,
        verbose_name='Date Received')
    retention_period = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Sponsor Retention Period')
    gw_doesnt_own_ip = models.NullBooleanField(
        verbose_name="GW Doesn't Own IP?")
    gw_background_ip = models.NullBooleanField(
        verbose_name='GW Background IP?')
    negotiation_status = models.CharField(
        choices=NEGOTIATION_CHOICES,
        max_length=3,
        blank=True,
        verbose_name='Negotiation Status',
        default='IQ')
    negotiation_notes = models.TextField(
        blank=True,
        verbose_name='Negotiation Notes')
    foreign_restrictions = models.NullBooleanField(
        verbose_name='Foreign Participation Restrictions?')
    certificates_insurance = models.NullBooleanField(
        verbose_name='Certificate of Insurance Needed?')
    insurance_renewal = models.DateField(
        null=True,
        blank=True,
        verbose_name='Certificate of Insurance Renewal Date')
    government_property = models.NullBooleanField(
        verbose_name='Government Furnished Property?')
    data_security_restrictions = models.NullBooleanField(
        verbose_name='Data/Security Restrictions?')
    everify = models.NullBooleanField(verbose_name='E-verify?')
    publication_restriction = models.NullBooleanField(
        verbose_name='Publication Restriction?')
    negotiation_completion_date = models.DateTimeField(blank=True, null=True, verbose_name='Completion Date')
    award_text = models.CharField(max_length=50, blank=True, null=True)

    def __unicode__(self):
        return u'Award Negotiation %s' % (self.id)

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object"""

        return reverse(
            'edit_award_negotiation',
            kwargs={
                'award_pk': self.award.pk})


class AwardSetup(AssignableAwardSection):
    """Model for the AwardSetup data"""
    WAIT_FOR = {'RB': 'Revised Budget', 'PA': 'PI Access', 'CA': 'Cost Share Approval', 'FC': 'FCOI',
                'PS': 'Proposal Submission', 'SC': 'Sponsor Clarity', 'NO': 'New Org needed',
                'IC': 'Internal Clarification', 'DC': 'Documents not in GW Docs'
                }

    WAIT_FOR_CHOICES = (
        ('RB', 'Revised Budget'),
        ('PA', 'PI Access'),
        ('CA', 'Cost Share Approval'),
        ('FC', 'FCOI'),
        ('PS', 'Proposal Submission'),
        ('SC', 'Sponsor Clarity'),
        ('NO', 'New Org needed'),
        ('IC', 'Internal Clarification'),
        ('DC', 'Documents not in GW Docs')

    )
    SP_TYPE_CHOICES = (
        ('SP1', 'SP1 - Research and Development'),
        ('SP2', 'SP2 - Training'),
        ('SP3', 'SP3 - Other'),
        ('SP4', 'SP4 - Clearing and Suspense'),
        ('SP5', 'SP5 - Program Income'),
    )

    REPORTING_CHOICES = (
        ('MN', 'Monthly'),
        ('QR', 'Quarterly'),
        ('SA', 'Semi-annually'),
        ('AN', 'Annually'),
        ('OT', 'Other (specify)')
    )

    EAS_AWARD_CHOICES = (
        ('C', 'Contract'),
        ('G', 'Grant'),
        ('I', 'Internal Funding'),
        ('PP', 'Per Patient'),
        ('PA', 'Pharmaceutical')
    )

    PROPERTY_CHOICES = (
        ('TG', 'Title to GW'),
        ('TS', 'Title to Sponsor'),
        ('TD', 'Title to be determined at purchase'),
        ('SE', 'Special EAS Value')
    )

    ONR_CHOICES = (
        ('Y', 'Yes, Administered'),
        ('N', 'No, Administered')
    )

    COST_SHARING_CHOICES = (
        ('M', 'Mandatory'),
        ('V', 'Voluntary'),
        ('B', 'Both')
    )

    PERFORMANCE_SITE_CHOICES = (
        ('ON', 'On-campus'),
        ('OF', 'Off-campus'),
        ('OT', 'Other')
    )

    TASK_LOCATION_CHOICES = (
        ('AL', 'AL - ALEXANDRIA'),
        ('BE', 'BE - BETHESDA'),
        ('CC', 'CC - CRYSTAL CITY'),
        ('CL', 'CL - CLARENDON'),
        ('CM', 'CM - ST MARY\'S COUNTY, CALIFORNIA, MD'),
        ('CW', 'CW - K STREET CENTER OFF-CAMPUS DC'),
        ('DE', 'DE - DISTANCE EDUCATION'),
        ('FB', 'FB - FOGGY BOTTOM'),
        ('FC', 'FC - CITY OF FALLS CHURCH'),
        ('FX', 'FX - FAIRFAX COUNTY'),
        ('GS', 'GS - GODDARD SPACE FLIGHT CENTER'),
        ('HR', 'HR - HAMPTON ROADS'),
        ('IN', 'IN - INTERNATIONAL'),
        ('LA', 'LA - LANGLEY AIR FORCE BASE'),
        ('LO', 'LO - LOUDOUN COUNTY OTHER'),
        ('MV', 'MV - MOUNT VERNON CAMPUS'),
        ('OA', 'OA - OTHER ARLINGTON COUNTY'),
        ('OD', 'OD - OTHER DISTRICT OF COLUMBIA'),
        ('OG', 'OG - OTHER MONTGOMERY COUNTY'),
        ('OM', 'OM - OTHER MARYLAND'),
        ('OV', 'OV - OTHER VIRGINIA'),
        ('PA', 'PA - PACE - Classes at Sea'),
        ('RI', 'RI - RICHMOND, CITY OF'),
        ('RO', 'RO - ROSSLYN ARLINGTON COUNTY'),
        ('RV', 'RV - ROCKVILLE'),
        ('SM', 'SM - SUBURBAN MARYLAND'),
        ('T', 'T - TOTAL LOCATION'),
        ('US', 'US - OTHER US'),
        ('VC', 'VC - VIRGINIA CAMPUS'),
        ('VR', 'VR - VIRGINIA RESEARCH AND TECHNOLOGY CENTER'),
        ('VS', 'VS - VIRGINIA SQUARE'),
    )

    EAS_SETUP_CHOICES = (
        ('Y', 'Yes'),
        ('N', 'No'),
        ('M', 'Manual'),
    )

    HIDDEN_FIELDS = AwardSection.HIDDEN_FIELDS + [
        'award_template',
        'short_name',
        'task_location',
        'start_date',
        'end_date',
        'final_reports_due_date',
        'eas_award_type',
        'sp_type',
        'indirect_cost_schedule',
        'allowed_cost_schedule',
        'cfda_number',
        'federal_negotiated_rate',
        'bill_to_address',
        'billing_events',
        'contact_name',
        'phone',
        'financial_reporting_req',
        'financial_reporting_oth',
        'property_equip_code',
        'onr_administered_code',
        'cost_sharing_code',
        'document_number',
        'performance_site',
        'award_setup_complete',
        'qa_screening_complete',
        'ready_for_eas_setup',
    ]

    HIDDEN_SEARCH_FIELDS = AwardSection.HIDDEN_SEARCH_FIELDS + [
        'nine_ninety_form_needed',
        'patent_reporting_req',
        'invention_reporting_req',
        'property_reporting_req',
        'equipment_reporting_req',
        'budget_restrictions',
        'record_destroy_date',
        'date_assigned']

    EAS_REPORT_FIELDS = [
        # PTA info first
        'award_template',
        'short_name',
        'task_location',
        'start_date',
        'end_date',
        'final_reports_due_date',
        'eas_award_type',
        'sp_type',
        'indirect_cost_schedule',
        'allowed_cost_schedule',
        'cfda_number',
        'federal_negotiated_rate',
        'bill_to_address',
        'contact_name',
        'phone',
        'financial_reporting_req',
        'financial_reporting_oth',
        'property_equip_code',
        'onr_administered_code',
        'cost_sharing_code',
        'billing_events',
        'document_number',
        'nine_ninety_form_needed',
    ]

    minimum_fields = (

    )

    MULTIPLE_SELECT_FIELDS = (
        'financial_reporting_req',
        'technical_reporting_req',
    )

    award = models.OneToOneField(Award)

    short_name = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Award short name')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    final_reports_due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Final Reports/Final Invoice Due Date (Close Date)')
    eas_award_type = models.CharField(
        choices=EAS_AWARD_CHOICES,
        max_length=2,
        blank=True,
        verbose_name='EAS award type')
    sp_type = models.CharField(
        choices=SP_TYPE_CHOICES,
        max_length=3,
        blank=True,
        verbose_name='SP Type')
    indirect_cost_schedule = models.ForeignKey(
        IndirectCost,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True})
    allowed_cost_schedule = models.ForeignKey(
        AllowedCostSchedule,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True})
    cfda_number = models.ForeignKey(
        CFDANumber,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True},
        verbose_name='CFDA number')
    federal_negotiated_rate = models.ForeignKey(
        FedNegRate,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True})
    property_equip_code = models.CharField(
        choices=PROPERTY_CHOICES,
        max_length=2,
        blank=True,
        verbose_name='T&C: Property and Equipment Code')
    onr_administered_code = models.CharField(
        choices=ONR_CHOICES,
        max_length=2,
        blank=True,
        verbose_name='T&C: ONR Administered Code')
    cost_sharing_code = models.CharField(
        choices=COST_SHARING_CHOICES,
        max_length=2,
        blank=True,
        verbose_name='T&C: Cost Sharing Code')
    bill_to_address = models.TextField(blank=True)
    contact_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Contact Name (Last, First)')
    phone = models.CharField(max_length=50, blank=True)
    billing_events = models.TextField(blank=True)
    document_number = models.CharField(max_length=100, blank=True)
    date_wait_for_updated = models.DateTimeField(blank=True, null=True, verbose_name='Date Wait for Updated')
    wait_for_reson = models.CharField(
        choices=WAIT_FOR_CHOICES,
        max_length=2,
        blank=True,
        null=True,
        verbose_name='Wait for'
    )
    nine_ninety_form_needed = models.NullBooleanField(
        verbose_name='990 Form Needed?')
    task_location = models.CharField(
        choices=TASK_LOCATION_CHOICES,
        max_length=2,
        blank=True)
    performance_site = models.CharField(
        choices=PERFORMANCE_SITE_CHOICES,
        max_length=2,
        blank=True)
    expanded_authority = models.NullBooleanField(
        verbose_name='Expanded Authority?')

    financial_reporting_req = MultiSelectField(
        choices=REPORTING_CHOICES,
        blank=True,
        verbose_name='Financial Reporting Requirements')
    financial_reporting_oth = models.CharField(
        max_length=250,
        blank=True,
        verbose_name='Other financial reporting requirements')
    technical_reporting_req = MultiSelectField(
        choices=REPORTING_CHOICES,
        blank=True,
        verbose_name='Technical Reporting Requirements')
    technical_reporting_oth = models.CharField(
        max_length=250,
        blank=True,
        verbose_name='Other technical reporting requirements')
    patent_reporting_req = models.DateField(
        null=True,
        blank=True,
        verbose_name='Patent Report Requirement')
    invention_reporting_req = models.DateField(
        null=True,
        blank=True,
        verbose_name='Invention Report Requirement')
    property_reporting_req = models.DateField(
        null=True,
        blank=True,
        verbose_name='Property Report Requirement')
    equipment_reporting_req = models.DateField(
        null=True,
        blank=True,
        verbose_name='Equipment Report Requirement')

    budget_restrictions = models.NullBooleanField(
        verbose_name='Budget Restrictions?')
    award_template = models.ForeignKey(
        AwardTemplate,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True})
    award_setup_complete = models.DateField(
        null=True,
        blank=True,
        verbose_name='Award Setup Complete')
    qa_screening_complete = models.DateField(
        null=True,
        blank=True,
        verbose_name='QA Screening Complete')
    pre_award_spending_auth = models.NullBooleanField(
        verbose_name='Pre-award spending authorized?')
    record_destroy_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Record Retention Destroy Date')
    ready_for_eas_setup = models.CharField(
        choices=EAS_SETUP_CHOICES,
        max_length=3,
        blank=True,
        verbose_name='Ready for EAS Setup?')

    wait_for = models.TextField(blank=True)
    setup_completion_date = models.DateTimeField(blank=True, null=True, verbose_name='Completion Date')

    def __unicode__(self):
        return u'Award Setup %s' % (self.id)

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object"""
        return reverse('edit_award_setup', kwargs={'award_pk': self.award.pk})

    def copy_from_proposal(self, proposal):
        """Copy common fields from the given proposal to this AwardSetup"""

        if proposal:
            self.start_date = proposal.project_start_date
            self.end_date = proposal.project_end_date

            self.save()

    def get_waiting_reason(self):
            return self.WAIT_FOR.get(self.wait_for_reson) if self.wait_for_reson else ''

class AwardModification(AssignableAwardSection):
    """Model for the AwardModification data"""
    WAIT_FOR_CHOICES = (
        ('RB', 'Revised Budget'),
        ('PA', 'PI Access'),
        ('CA', 'Cost Share Approval'),
        ('FC', 'FCOI'),
        ('PS', 'Proposal Submission'),
        ('SC', 'Sponsor Clarity'),
        ('NO', 'New Org needed'),
        ('IC', 'Internal Clarification'),
        ('DC', 'Documents not in GW Docs'))

    SP_TYPE_CHOICES = (
        ('SP1', 'SP1 - Research and Development'),
        ('SP2', 'SP2 - Training'),
        ('SP3', 'SP3 - Other'),
        ('SP4', 'SP4 - Clearing and Suspense'),
        ('SP5', 'SP5 - Program Income'),
    )

    REPORTING_CHOICES = (
        ('MN', 'Monthly'),
        ('QR', 'Quarterly'),
        ('SA', 'Semi-annually'),
        ('AN', 'Annually'),
        ('OT', 'Other (specify)')
    )

    EAS_AWARD_CHOICES = (
        ('C', 'Contract'),
        ('G', 'Grant'),
        ('I', 'Internal Funding'),
        ('PP', 'Per Patient'),
        ('PA', 'Pharmaceutical')
    )

    PROPERTY_CHOICES = (
        ('TG', 'Title to GW'),
        ('TS', 'Title to Sponsor'),
        ('TD', 'Title to be determined at purchase'),
        ('SE', 'Special EAS Value')
    )

    ONR_CHOICES = (
        ('Y', 'Yes, Administered'),
        ('N', 'No, Administered')
    )

    COST_SHARING_CHOICES = (
        ('M', 'Mandatory'),
        ('V', 'Voluntary'),
        ('B', 'Both')
    )

    PERFORMANCE_SITE_CHOICES = (
        ('ON', 'On-campus'),
        ('OF', 'Off-campus'),
        ('OT', 'Other')
    )

    TASK_LOCATION_CHOICES = (
        ('AL', 'AL - ALEXANDRIA'),
        ('BE', 'BE - BETHESDA'),
        ('CC', 'CC - CRYSTAL CITY'),
        ('CL', 'CL - CLARENDON'),
        ('CM', 'CM - ST MARY\'S COUNTY, CALIFORNIA, MD'),
        ('CW', 'CW - K STREET CENTER OFF-CAMPUS DC'),
        ('DE', 'DE - DISTANCE EDUCATION'),
        ('FB', 'FB - FOGGY BOTTOM'),
        ('FC', 'FC - CITY OF FALLS CHURCH'),
        ('FX', 'FX - FAIRFAX COUNTY'),
        ('GS', 'GS - GODDARD SPACE FLIGHT CENTER'),
        ('HR', 'HR - HAMPTON ROADS'),
        ('IN', 'IN - INTERNATIONAL'),
        ('LA', 'LA - LANGLEY AIR FORCE BASE'),
        ('LO', 'LO - LOUDOUN COUNTY OTHER'),
        ('MV', 'MV - MOUNT VERNON CAMPUS'),
        ('OA', 'OA - OTHER ARLINGTON COUNTY'),
        ('OD', 'OD - OTHER DISTRICT OF COLUMBIA'),
        ('OG', 'OG - OTHER MONTGOMERY COUNTY'),
        ('OM', 'OM - OTHER MARYLAND'),
        ('OV', 'OV - OTHER VIRGINIA'),
        ('PA', 'PA - PACE - Classes at Sea'),
        ('RI', 'RI - RICHMOND, CITY OF'),
        ('RO', 'RO - ROSSLYN ARLINGTON COUNTY'),
        ('RV', 'RV - ROCKVILLE'),
        ('SM', 'SM - SUBURBAN MARYLAND'),
        ('T', 'T - TOTAL LOCATION'),
        ('US', 'US - OTHER US'),
        ('VC', 'VC - VIRGINIA CAMPUS'),
        ('VR', 'VR - VIRGINIA RESEARCH AND TECHNOLOGY CENTER'),
        ('VS', 'VS - VIRGINIA SQUARE'),
    )

    EAS_SETUP_CHOICES = (
        ('Y', 'Yes'),
        ('N', 'No'),
        ('M', 'Manual'),
    )

    HIDDEN_FIELDS = AwardSection.HIDDEN_FIELDS + [
        'award_template',
        'short_name',
        'task_location',
        'start_date',
        'end_date',
        'final_reports_due_date',
        'eas_award_type',
        'sp_type',
        'indirect_cost_schedule',
        'allowed_cost_schedule',
        'cfda_number',
        'federal_negotiated_rate',
        'bill_to_address',
        'billing_events',
        'contact_name',
        'phone',
        'financial_reporting_req',
        'financial_reporting_oth',
        'property_equip_code',
        'onr_administered_code',
        'cost_sharing_code',
        'document_number',
        'performance_site',
        'award_setup_complete',
        'qa_screening_complete',
        'ready_for_eas_setup',
    ]

    HIDDEN_SEARCH_FIELDS = AwardSection.HIDDEN_SEARCH_FIELDS + [
        'nine_ninety_form_needed',
        'patent_reporting_req',
        'invention_reporting_req',
        'property_reporting_req',
        'equipment_reporting_req',
        'budget_restrictions',
        'record_destroy_date',
        'date_assigned']

    EAS_REPORT_FIELDS = [
        # PTA info first
        'award_template',
        'short_name',
        'task_location',
        'start_date',
        'end_date',
        'final_reports_due_date',
        'eas_award_type',
        'sp_type',
        'indirect_cost_schedule',
        'allowed_cost_schedule',
        'cfda_number',
        'federal_negotiated_rate',
        'bill_to_address',
        'contact_name',
        'phone',
        'financial_reporting_req',
        'financial_reporting_oth',
        'property_equip_code',
        'onr_administered_code',
        'cost_sharing_code',
        'billing_events',
        'document_number',
        'nine_ninety_form_needed',
    ]

    minimum_fields = (

    )

    MULTIPLE_SELECT_FIELDS = (
        'financial_reporting_req',
        'technical_reporting_req',
    )

    award = models.ForeignKey(Award)

    short_name = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Award short name')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    final_reports_due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Final Reports/Final Invoice Due Date (Close Date)')
    eas_award_type = models.CharField(
        choices=EAS_AWARD_CHOICES,
        max_length=2,
        blank=True,
        verbose_name='EAS award type')
    sp_type = models.CharField(
        choices=SP_TYPE_CHOICES,
        max_length=3,
        blank=True,
        verbose_name='SP Type')
    indirect_cost_schedule = models.ForeignKey(
        IndirectCost,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True})
    allowed_cost_schedule = models.ForeignKey(
        AllowedCostSchedule,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True})
    cfda_number = models.ForeignKey(
        CFDANumber,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True},
        verbose_name='CFDA number')
    federal_negotiated_rate = models.ForeignKey(
        FedNegRate,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True})
    property_equip_code = models.CharField(
        choices=PROPERTY_CHOICES,
        max_length=2,
        blank=True,
        verbose_name='T&C: Property and Equipment Code')
    onr_administered_code = models.CharField(
        choices=ONR_CHOICES,
        max_length=2,
        blank=True,
        verbose_name='T&C: ONR Administered Code')
    cost_sharing_code = models.CharField(
        choices=COST_SHARING_CHOICES,
        max_length=2,
        blank=True,
        verbose_name='T&C: Cost Sharing Code')
    bill_to_address = models.TextField(blank=True)
    contact_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Contact Name (Last, First)')
    phone = models.CharField(max_length=50, blank=True)
    billing_events = models.TextField(blank=True)
    document_number = models.CharField(max_length=100, blank=True)
    date_wait_for_updated = models.DateTimeField(blank=True, null=True, verbose_name='Date Wait for Updated')
    wait_for_reson = models.CharField(
        choices=WAIT_FOR_CHOICES,
        max_length=2,
        blank=True,
        null=True,
        verbose_name='Wait for'
    )
    nine_ninety_form_needed = models.NullBooleanField(
        verbose_name='990 Form Needed?')
    task_location = models.CharField(
        choices=TASK_LOCATION_CHOICES,
        max_length=2,
        blank=True)
    performance_site = models.CharField(
        choices=PERFORMANCE_SITE_CHOICES,
        max_length=2,
        blank=True)
    expanded_authority = models.NullBooleanField(
        verbose_name='Expanded Authority?')

    financial_reporting_req = MultiSelectField(
        choices=REPORTING_CHOICES,
        blank=True,
        verbose_name='Financial Reporting Requirements')
    financial_reporting_oth = models.CharField(
        max_length=250,
        blank=True,
        verbose_name='Other financial reporting requirements')
    technical_reporting_req = MultiSelectField(
        choices=REPORTING_CHOICES,
        blank=True,
        verbose_name='Technical Reporting Requirements')
    technical_reporting_oth = models.CharField(
        max_length=250,
        blank=True,
        verbose_name='Other technical reporting requirements')
    patent_reporting_req = models.DateField(
        null=True,
        blank=True,
        verbose_name='Patent Report Requirement')
    invention_reporting_req = models.DateField(
        null=True,
        blank=True,
        verbose_name='Invention Report Requirement')
    property_reporting_req = models.DateField(
        null=True,
        blank=True,
        verbose_name='Property Report Requirement')
    equipment_reporting_req = models.DateField(
        null=True,
        blank=True,
        verbose_name='Equipment Report Requirement')

    budget_restrictions = models.NullBooleanField(
        verbose_name='Budget Restrictions?')
    award_template = models.ForeignKey(
        AwardTemplate,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True})
    award_setup_complete = models.DateField(
        null=True,
        blank=True,
        verbose_name='Award Setup Complete')
    qa_screening_complete = models.DateField(
        null=True,
        blank=True,
        verbose_name='QA Screening Complete')
    pre_award_spending_auth = models.NullBooleanField(
        verbose_name='Pre-award spending authorized?')
    record_destroy_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Record Retention Destroy Date')
    ready_for_eas_setup = models.CharField(
        choices=EAS_SETUP_CHOICES,
        max_length=3,
        blank=True,
        verbose_name='Ready for EAS Setup?')
    modification_completion_date = models.DateTimeField(blank=True, null=True, verbose_name='Completion Date')

    wait_for = models.TextField(blank=True)

    def __unicode__(self):
        return u'Award Modification %s' % (self.id)

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object"""

        return reverse('edit_award_setup', kwargs={'award_pk': self.award.pk})


class PTANumber(FieldIteratorMixin, models.Model):
    """Model for the PTANumber data"""

    EAS_AWARD_CHOICES = (
        ('C', 'Contract'),
        ('G', 'Grant'),
        ('I', 'Internal Funding'),
        ('PP', 'Per Patient'),
        ('PA', 'Pharmaceutical')
    )

    SP_TYPE_CHOICES = (
        ('SP1', 'SP1 - Research and Development'),
        ('SP2', 'SP2 - Training'),
        ('SP3', 'SP3 - Other'),
        ('SP4', 'SP4 - Clearing and Suspense'),
        ('SP5', 'SP5 - Program Income'),
        ('SP7', 'SP7 - Symposium/Conference/Seminar'),
    )

    EAS_SETUP_CHOICES = (
        ('Y', 'Yes'),
        ('N', 'No'),
        ('M', 'Manual'),
    )

    EAS_STATUS_CHOICES = (
        ('A', 'Active'),
        ('OH', 'On hold'),
        ('AR', 'At risk'),
        ('C', 'Closed')
    )

    HIDDEN_FIELDS = ['award']

    HIDDEN_TABLE_FIELDS = []

    HIDDEN_SEARCH_FIELDS = AwardSection.HIDDEN_SEARCH_FIELDS + [
        'parent_banner_number',
        'banner_number',
        'cs_banner_number',
        'allowed_cost_schedule',
        'award_template',
        'preaward_date',
        'federal_negotiated_rate',
        'indirect_cost_schedule',
        'sponsor_banner_number',
        'ready_for_eas_setup']

    award = models.ForeignKey(Award)

    project_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Project #')
    task_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Task #')
    award_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Award #')
    award_setup_complete = models.DateField(
        null=True,
        blank=True,
        verbose_name='Award Setup Complete')
    total_pta_amount = models.DecimalField(
        decimal_places=2,
        max_digits=10,
        null=True,
        blank=True,
        verbose_name='Total PTA Amt')
    parent_banner_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Prnt Banner #')
    banner_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Banner #')
    cs_banner_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='CS Banner #')
    principal_investigator = models.ForeignKey(
        AwardManager,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True},
        verbose_name='PI*')
    agency_name = models.ForeignKey(
        FundingSource,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True},
        verbose_name='Agency Name*')
    department_name = models.ForeignKey(
            AwardOrganization,
            null=True,
            blank=True,
            limit_choices_to={
                'active': True},
            verbose_name='Department Code & Name*')
    project_title = models.CharField(max_length=256, blank=True, verbose_name='Project Title*')
    who_is_prime = models.ForeignKey(
            PrimeSponsor,
            null=True,
            blank=True,
            limit_choices_to={
                'active': True})
    allowed_cost_schedule = models.ForeignKey(
        AllowedCostSchedule,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True},
        verbose_name='Allowed Cost Schedule*')
    award_template = models.ForeignKey(
        AwardTemplate,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True},
        verbose_name='Award Template*')
    cfda_number = models.ForeignKey(
        CFDANumber,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True},
        verbose_name='CFDA number*')
    eas_award_type = models.CharField(
        choices=EAS_AWARD_CHOICES,
        max_length=2,
        blank=True,
        verbose_name='EAS Award Type*')
    preaward_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True, verbose_name='Start Date*')
    end_date = models.DateField(null=True, blank=True, verbose_name='End Date*')
    final_reports_due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Final Reports/Final Invoice Due Date (Close Date)*')
    federal_negotiated_rate = models.ForeignKey(
        FedNegRate,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True},
        verbose_name='Federal Negotiated Rate*')
    indirect_cost_schedule = models.ForeignKey(
        IndirectCost,
        null=True,
        blank=True,
        limit_choices_to={
            'active': True},
        verbose_name='Indirect Cost Schedule*')
    sp_type = models.CharField(
        choices=SP_TYPE_CHOICES,
        max_length=3,
        blank=True,
        verbose_name='SP Type*')
    short_name = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Award Short Name*')
    agency_award_number = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name='Agency Award Number*')
    sponsor_award_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Prime Award # (if GW is subawardee)*')
    sponsor_banner_number = models.CharField(max_length=50, blank=True)
    eas_status = models.CharField(
        choices=EAS_STATUS_CHOICES,
        max_length=2,
        blank=True,
        verbose_name='EAS Status*')
    ready_for_eas_setup = models.CharField(
        choices=EAS_SETUP_CHOICES,
        max_length=3,
        blank=True,
        verbose_name='Ready for EAS Setup?')

    is_edited = models.BooleanField(default=False)
    pta_number_updated = models.DateField(
        null=True,
        blank=True)

    def __unicode__(self):
        return u'PTA #%s' % (self.project_number)

    def save(self, *args, **kwargs):
        """Overrides the parent save method.
        If this is the first PTANumber entered (either on creation or save later),
        update some fields back to the most recent Proposal.
        """

        super(PTANumber, self).save(*args, **kwargs)

        if self == self.award.get_first_pta_number():
            proposal = self.award.get_most_recent_proposal()
            if proposal and self.agency_name != proposal.agency_name:
                proposal.agency_name = self.agency_name
                proposal.save()
            if proposal and self.who_is_prime != proposal.who_is_prime:
                proposal.who_is_prime = self.who_is_prime
                proposal.save()
            if proposal and self.project_title != proposal.project_title:
                proposal.project_title = self.project_title
                proposal.save()
            if proposal and self.start_date != proposal.project_start_date:
                proposal.project_start_date = self.start_date
                proposal.save()
            if proposal and self.end_date != proposal.project_end_date:
                proposal.project_end_date = self.end_date
                proposal.save()

            award_acceptance = self.award.get_current_award_acceptance()

            if self.agency_award_number != award_acceptance.agency_award_number:
                award_acceptance.agency_award_number = self.agency_award_number
                award_acceptance.save()
            if self.sponsor_award_number != award_acceptance.sponsor_award_number:
                award_acceptance.sponsor_award_number = self.sponsor_award_number
                award_acceptance.save()
            if self.eas_status != award_acceptance.eas_status:
                award_acceptance.eas_status = self.eas_status
                award_acceptance.save()
            if self.project_title != award_acceptance.project_title:
                award_acceptance.project_title = self.project_title
                award_acceptance.save()

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object"""

        return reverse(
            'edit_pta_number',
            kwargs={
                'award_pk': self.award.pk,
                'pta_pk': self.id})

    def get_delete_url(self):
        """Gets the URL used to delete this object"""

        return reverse(
            'delete_pta_number',
            kwargs={
                'award_pk': self.award.pk,
                'pta_pk': self.id})

    def get_recent_ptanumber_revision(self):
        """Gets the most recent revision of the model, using django-reversion"""
        latest_revision = reversion.get_for_object(self)[0].revision
        if latest_revision.user:
            user = latest_revision.user.get_full_name()
        else:
            user = 'ATP'
        return (user, latest_revision.date_created)


class Subaward(AwardSection):
    """Model for the Subaward data"""

    RISK_CHOICES = (
        ('L', 'Low'),
        ('M', 'Medium'),
        ('H', 'High')
    )

    SUBRECIPIENT_TYPE_CHOICES = (
        ('F', 'Foundation'),
        ('FP', 'For-Profit'),
        ('SG', 'State Government'),
        ('LG', 'Local Government'),
        ('I', 'International'),
        ('ON', 'Other non-profit'),
        ('U', 'University')
    )

    AGREEMENT_CHOICES = (
        ('SA', 'Subaward'),
        ('SC', 'Subcontract'),
        ('IC', 'ICA'),
        ('M', 'Modification'),
        ('H', 'Honorarium'),
        ('C', 'Consultant'),
        ('CS', 'Contract Service')
    )

    SUBAWARD_STATUS_CHOICES = (
        ('R', 'Review'),
        ('G', 'Waiting for GCAS approval'),
        ('D', 'Waiting for Department'),
        ('P', 'Procurement'),
        ('S', 'Sent to recepient'),
    )

    CONTRACT_CHOICES = (
        ('FP', 'Fixed price subcontract'),
        ('CR', 'Cost-reimbursable subcontract'),
        ('FA', 'Fixed amount award'),
        ('OT', 'Other')
    )

    minimum_fields = (
        'subrecipient_type',
        'risk',
        'amount',
        'gw_number',
        'contact_information',
        'subaward_start',
        'subaward_end',
        'agreement_type',
        'debarment_check',
        'international',
        'sent',
        'ffata_reportable',
        'zip_code',
    )

    HIDDEN_SEARCH_FIELDS = AwardSection.HIDDEN_SEARCH_FIELDS + [
        'creation_date',
        'modification_number',
        'subaward_ready',
        'sent',
        'reminder',
        'fcoi_cleared',
        'citi_cleared',
        'amount',
        'contact_information',
        'zip_code',
        'subaward_start',
        'subaward_end',
        'debarment_check',
        'international',
        'cfda_number',
        'ffata_submitted',
        'tech_report_received']

    award = models.ForeignKey(Award)
    creation_date = models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name='Date Created')

    recipient = models.CharField(max_length=250, blank=True)
    agreement_type = models.CharField(
        choices=AGREEMENT_CHOICES,
        max_length=2,
        blank=True)
    modification_number = models.CharField(max_length=50, blank=True)
    subrecipient_type = models.CharField(
        choices=SUBRECIPIENT_TYPE_CHOICES,
        max_length=2,
        blank=True,
        verbose_name='Subrecipient Type')
    assist = models.CharField(max_length=100, blank=True)
    date_received = models.DateField(null=True, blank=True)
    status = models.CharField(
        choices=SUBAWARD_STATUS_CHOICES,
        max_length=2,
        blank=True)
    risk = models.CharField(choices=RISK_CHOICES, max_length=2, blank=True)
    approval_expiration = models.DateField(
        null=True,
        blank=True,
        verbose_name='Date of Expiration for Approval')
    subaward_ready = models.DateField(
        null=True,
        blank=True,
        verbose_name='Subaward ready to be initiated')
    sent = models.DateField(
        null=True,
        blank=True,
        verbose_name='Subagreement sent to recipient')
    reminder = models.NullBooleanField(
        verbose_name='Reminder sent to Subawardee?')
    received = models.DateField(
        null=True,
        blank=True,
        verbose_name='Receipt of Partially Executed Subagreement')
    fcoi_cleared = models.DateField(
        null=True,
        blank=True,
        verbose_name='Subaward Cleared FCOI Procedures')
    citi_cleared = models.DateField(
        null=True,
        blank=True,
        verbose_name='Subaward Completed CITI Training')
    date_fully_executed = models.DateField(null=True, blank=True)
    amount = models.DecimalField(
        decimal_places=2,
        max_digits=10,
        null=True,
        blank=True,
        verbose_name='Subaward Total Amount')
    gw_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='GW Subaward Number')
    funding_mechanism = models.CharField(
        choices=CONTRACT_CHOICES,
        max_length=2,
        blank=True,
        verbose_name='Funding mechanism')
    other_mechanism = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Other funding mechanism')
    contact_information = models.TextField(
        blank=True,
        verbose_name='Subawardee contact information')
    zip_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='ZIP code')
    subaward_start = models.DateField(
        null=True,
        blank=True,
        verbose_name='Subaward Performance Period Start')
    subaward_end = models.DateField(
        null=True,
        blank=True,
        verbose_name='Subaward Performance Period End')
    debarment_check = models.NullBooleanField(
        verbose_name='Debarment or suspension check?')
    international = models.NullBooleanField(verbose_name='International?')
    cfda_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='CFDA number')
    fain = models.CharField(max_length=50, blank=True, verbose_name='FAIN')
    ein = models.CharField(max_length=50, blank=True, verbose_name='EIN')
    duns_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='DUNS number')
    ffata_reportable = models.NullBooleanField(
        verbose_name='FFATA Reportable?')
    ffata_submitted = models.DateField(
        null=True,
        blank=True,
        verbose_name='FFATA Report Submitted Date')
    tech_report_due = models.DateField(
        null=True,
        blank=True,
        verbose_name='Technical Report Due Date')
    tech_report_received = models.DateField(
        null=True,
        blank=True,
        verbose_name='Technical Report Received Date')
    subaward_completion_date = models.DateTimeField(blank=True, null=True, verbose_name='Completion Date')

    def __unicode__(self):
        return u'Subaward %s' % (self.gw_number)

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object"""

        return reverse(
            'edit_subaward',
            kwargs={
                'award_pk': self.award.pk,
                'subaward_pk': self.id})


class AwardManagement(AssignableAwardSection):
    """Model for the AwardManagement data"""

    minimum_fields = (

    )

    HIDDEN_SEARCH_FIELDS = AwardSection.HIDDEN_SEARCH_FIELDS + [
        'date_assigned']

    award = models.OneToOneField(Award)
    management_completion_date = models.DateTimeField(blank=True, null=True, verbose_name='Completion Date')

    def __unicode__(self):
        return u'Award Management %s' % (self.id)

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object"""

        return reverse(
            'edit_award_management',
            kwargs={
                'award_pk': self.award.pk})


class PriorApproval(FieldIteratorMixin, models.Model):
    """Model for the PriorApproval data"""

    HIDDEN_FIELDS = ['award']

    HIDDEN_TABLE_FIELDS = []

    REQUEST_CHOICES = (
        ('AB', 'Absence or Change of Key Personnel'),
        ('CF', 'Carry-forward of unexpended balances to subsequent funding periods'),
        ('CS', 'Change in Scope'),
        ('ER', 'Effort Reduction'),
        ('EN', 'Equipment not in approved budget'),
        ('FC', 'Faculty consulting compensation that exceeds base salary'),
        ('FT', 'Foreign Travel'),
        ('IN', 'Initial no-cost extension of up to 12 months (per competitive segment)'),
        ('OT', 'Other'),
        ('RA', 'Rebudgeting among budget categories'),
        ('RB', 'Rebudgeting between direct and F&A costs'),
        ('RF', 'Rebudgeting of funds allotted for training (direct payment to trainees) to other categories of expense'),
        ('SN', 'Subsequent no-cost extension or extention of more than 12 months'),
    )

    PRIOR_APPROVAL_STATUS_CHOICES = (
        ('PN', 'Pending'),
        ('AP', 'Approved'),
        ('NA', 'Not Approved'),
    )

    award = models.ForeignKey(Award)

    request = models.CharField(
        choices=REQUEST_CHOICES,
        max_length=2,
        blank=True)
    date_submitted = models.DateField(null=True, blank=True)
    status = models.CharField(
        choices=PRIOR_APPROVAL_STATUS_CHOICES,
        max_length=2,
        blank=True)
    date_approved = models.DateField(null=True, blank=True)

    def __unicode__(self):
        return u'Prior Approval #%s' % (self.id)

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object."""

        return reverse(
            'edit_prior_approval',
            kwargs={
                'award_pk': self.award.pk,
                'prior_approval_pk': self.id})

    def get_delete_url(self):
        """Gets the URL used to delete this object"""

        return reverse(
            'delete_prior_approval',
            kwargs={
                'award_pk': self.award.pk,
                'prior_approval_pk': self.id})


class ReportSubmission(FieldIteratorMixin, models.Model):
    """Model for the ReportSubmission data"""

    HIDDEN_FIELDS = ['award']

    HIDDEN_TABLE_FIELDS = []

    REPORT_CHOICES = (
        ('TA', 'Technical Annual'),
        ('TS', 'Technical Semiannual'),
        ('TQ', 'Technical Quarterly'),
        ('IP', 'Interim Progress Report (Non-Competing Continuations)'),
        ('DL', 'Deliverables'),
        ('IP', 'Invention/Patent Annual'),
        ('PA', 'Property Annual'),
        ('EA', 'Equipment Annual')
    )

    award = models.ForeignKey(Award)

    report = models.CharField(choices=REPORT_CHOICES, max_length=2, blank=True)
    due_date = models.DateField(null=True, blank=True)
    submitted_date = models.DateField(null=True, blank=True)

    def __unicode__(self):
        return u'Report Submission #%s' % (self.id)

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object"""

        return reverse(
            'edit_report_submission',
            kwargs={
                'award_pk': self.award.pk,
                'report_submission_pk': self.id})

    def get_delete_url(self):
        """Gets the URL used to delete this object"""

        return reverse(
            'delete_report_submission',
            kwargs={
                'award_pk': self.award.pk,
                'report_submission_pk': self.id})


class AwardCloseout(AssignableAwardSection):
    """Model for the AwardCloseout data"""

    minimum_fields = (

    )

    HIDDEN_SEARCH_FIELDS = AwardSection.HIDDEN_SEARCH_FIELDS + [
        'date_assigned']

    award = models.OneToOneField(Award)
    closeout_completion_date = models.DateTimeField(blank=True, null=True, verbose_name='Completion Date')

    def __unicode__(self):
        return u'Award Closeout %s' % (self.id)

    def get_absolute_url(self):
        """Gets the URL used to navigate to this object"""

        return reverse(
            'edit_award_closeout',
            kwargs={
                'award_pk': self.award.pk})


class FinalReport(FieldIteratorMixin, models.Model):
    """Model for the FinalReport data"""

    HIDDEN_FIELDS = ['award']

    HIDDEN_TABLE_FIELDS = []

    FINAL_REPORT_CHOICES = (
        ('FT', 'Final Technical'),
        ('FP', 'Final Progress Report'),
        ('FD', 'Final Deliverable(s)'),
        ('IP', 'Final Invention/Patent'),
        ('FI', 'Final Invention'),
        ('FP', 'Final Property'),
        ('FE', 'Final Equipment'),
    )

    award = models.ForeignKey(Award)

    report = models.CharField(
        choices=FINAL_REPORT_CHOICES,
        max_length=2,
        blank=True)
    due_date = models.DateField(null=True, blank=True)
    submitted_date = models.DateField(null=True, blank=True)

    def __unicode__(self):
        return u'Final Report #%s' % (self.id)

    def get_absolute_url(self):
        """ Gets the URL used to navigate to this object"""

        return reverse(
            'edit_final_report',
            kwargs={
                'award_pk': self.award.pk,
                'final_report_pk': self.id})

    def get_delete_url(self):
        """Gets the URL used to delete this object"""

        return reverse(
            'delete_final_report',
            kwargs={
                'award_pk': self.award.pk,
                'final_report_pk': self.id})
