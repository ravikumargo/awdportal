# Extra utility functions

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import DateField, DateTimeField, DecimalField, BigIntegerField, IntegerField, ForeignKey
from urlparse import urljoin
from decimal import Decimal
from .models import AwardManager, Proposal, KeyPersonnel, PerformanceSite, EASMapping, EASMappingException, AwardAcceptance

import csv
import requests
import StringIO

def _make_cayuse_request(endpoint, payload={}):
    """Makes an HTTP request to the given Cayuse endpoint, sending it the data in payload"""

    s = requests.Session()
    s.auth = (settings.CAYUSE_USERNAME, settings.CAYUSE_PASSWORD)

    if settings.DEBUG:
        # Disable SSL verification if we're using SSH tunneling to work locally
        response = s.get(
            urljoin(
                settings.CAYUSE_ENDPOINT,
                endpoint),
            params=payload,
            verify=False)
    else:
        response = s.get(
            urljoin(
                settings.CAYUSE_ENDPOINT,
                endpoint),
            params=payload)

    return response


def get_cayuse_submissions_from_proposals_table(get_all_submissions=False):
    """Used to populate the pick_proposal view
    These proposals retrieved from the local database. as the local database filled with a automatic job
    Defaults to the most recent six months of proposals, can be overriden to show all.
    """
    proposals = Proposal.objects.filter(award_id__isnull=True).order_by('-id')[:100]
    if get_all_submissions:
        proposals = Proposal.objects.filter(award_id__isnull=True)
    return proposals


def get_cayuse_submissions(get_all_submissions=False):
    """Used to populate the pick_proposal view

    Defaults to the most recent six months of proposals, can be overriden to show all.
    """

    options = {}
    if not get_all_submissions:
        six_months_ago = date.today() - relativedelta(months=6)
        options['since'] = six_months_ago

    response = _make_cayuse_request(
        'view/submissions', options)

    f = StringIO.StringIO(response.content)
    reader = csv.reader(f, delimiter=',')

    header = reader.next()

    proposals = []
    entries = ['department_name', 'first_name', 'last_name', 'middle_name', 'submit_title', 'submit_date',
               'division_code', 'submitterusername', 'department_code', 'result_code', 'duns_id']
    for row in reader:
        proposal = dict(zip(header, row))
        try:
            prop = Proposal.objects.get(proposal_id=proposal['proposal_id'])
        except:
            prop = None
        if not prop:
            try:
                cayuse_data = get_cayuse_summary(proposal['proposal_id'])
                pi = get_cayuse_pi(
                    cayuse_data['principal_investigator'],
                    cayuse_data['proposal']['employee_id'])
                proposal['principal_investigator_id'] = pi.id if pi.id else None
            except:
                pass
            if not proposal['total_indirect_costs']:
                del proposal['total_indirect_costs']
            else:
                proposal['total_indirect_costs'] = Decimal(proposal['total_indirect_costs'])
            if not proposal['total_direct_costs']:
                del proposal['total_direct_costs']
            else:
                proposal['total_direct_costs'] = Decimal(proposal['total_direct_costs'])
            proposal['proposal_number'] = '{0}-{1}'.format(proposal["submit_date"][2:4], proposal['proposal_id'])
            proposal['submission_date'] = proposal['submit_date'][0:10]
            for key in entries:
                if key in proposal:
                    del proposal[key]
            proposals.append(proposal)

    return proposals


def cast_field_value(field, value):
    """Parses Cayuse data into Python values.
    If the data doesn't exist in the ATP database, raises an EASMappingException to force
    the user to create a new mapping with that data.
    """

    if type(field) in [DecimalField, IntegerField, BigIntegerField,
                       DateField, DateTimeField, ForeignKey] and value == '':
        return None
    elif isinstance(field, DateTimeField):
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
    elif isinstance(field, DateField):
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except:
            value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
            return value.date()
    elif isinstance(field, ForeignKey):
        fk_model = field.related_field.model

        # Try to associate the Cayuse value for the ForeignKey field with the
        # appropriate EAS value
        try:
            mapping = EASMapping.objects.get(
                interface='C',
                field=field.name,
                incoming_value=value,
                atp_model=fk_model.__name__)
        except EASMapping.DoesNotExist:
            raise EASMappingException(
                message='Mapping not available',
                interface='C',
                field=field.name,
                incoming_value=value,
                atp_model=fk_model)

        return fk_model.objects.get(pk=mapping.atp_pk)

    else:
        return value


def cast_lotus_value(field, value):
    """Tries to get the local AwardManager from the info that came from Lotus.
    If it doesn't exist in the database, raises an EASMappingException to force
    the user to create a new mapping with that data.
    """

    fk_model = field.related_field.model

    # We may get lucky and the Lotus GWID matches a valid EAS employee
    if field.name == 'principal_investigator':
        try:
            award_manager = AwardManager.objects.get(gwid=value)
            return award_manager
        except AwardManager.DoesNotExist:
            pass

    try:
        mapping = EASMapping.objects.get(
            interface='L',
            field=field.name,
            incoming_value=value,
            atp_model=fk_model.__name__)
    except EASMapping.DoesNotExist:
        raise EASMappingException(
            message='Mapping not available',
            interface='L',
            field=field.name,
            incoming_value=value,
            atp_model=fk_model)

    return fk_model.objects.get(pk=mapping.atp_pk)


def get_cayuse_summary(proposal_id):
    """Get all the data about a proposal from Cayuse"""

    response = _make_cayuse_request('custom/summary?id=%s' % proposal_id)

    f = StringIO.StringIO(response.content)
    reader = csv.reader(f, delimiter=',')

    header = reader.next()
    proposal = reader.next()
    f.close()

    summary = dict(zip(header, proposal))

    pi_fields = AwardManager.CAYUSE_FIELDS
    proposal_fields = Proposal._meta.get_all_field_names()

    pi_info = {}

    for key in summary.keys():
        if key in pi_fields:
            pi_info[key] = cast_field_value(
                AwardManager._meta.get_field(key),
                summary.pop(key))
        elif key not in proposal_fields:
            del summary[key]
        else:
            summary[key] = cast_field_value(
                Proposal._meta.get_field(key),
                summary[key])

    return {'principal_investigator': pi_info, 'proposal': summary}


def get_cayuse_pi(pi_info, employee_id):
    """Tries to get the local AwardManager from the info that came from Cayuse.
    If it doesn't exist in the database, raises an EASMappingException to force
    the user to create a new mapping with that data.
    """
    try:
        award_manager = AwardManager.objects.get(gwid=employee_id)
    except AwardManager.DoesNotExist:
        try:
            full_name = '%s, %s %s' % (
                pi_info['last_name'], pi_info['first_name'], pi_info['middle_name'])
            mapping = EASMapping.objects.get(
                interface='C',
                field='principal_investigator',
                incoming_value=full_name,
                atp_model=AwardManager.__name__)
            award_manager = AwardManager.objects.get(pk=mapping.atp_pk)
        except EASMapping.DoesNotExist:
            raise EASMappingException(
                message='Mapping not available',
                interface='C',
                field='principal_investigator',
                incoming_value=full_name,
                atp_model=AwardManager)

    return award_manager


def get_key_personnel(proposal_id):
    """Gets the KeyPersonnel from Cayuse"""

    response = _make_cayuse_request('view/keypersons?id=%s' % proposal_id)

    f = StringIO.StringIO(response.content)
    reader = csv.reader(f, delimiter=',')

    header = reader.next()

    key_personnel = []

    for row in reader:
        key_personnel.append(dict(zip(header, row)))

    f.close()

    key_personnel_fields = KeyPersonnel._meta.get_all_field_names()

    for person in key_personnel:
        for key in person.keys():
            if key == 'proposal_id':
                del person[key]
            elif key in key_personnel_fields:
                person[key] = cast_field_value(
                    KeyPersonnel._meta.get_field(key),
                    person[key])
            else:
                del person[key]

    return key_personnel


def get_performance_sites(proposal_id):
    """Gets the PerformanceSites from Cayuse"""

    response = _make_cayuse_request('custom/PerformanceSites')

    f = StringIO.StringIO(response.content)
    reader = csv.reader(f, delimiter=',')

    header = reader.next()

    performance_sites = []

    for row in reader:
        site = dict(zip(header, row))
        # Unfortunately, the performance site endpoint doesn't let us filter on proposal_id
        # so we have to filter manually
        if site['Proposal_id'] == str(proposal_id):
            performance_sites.append(site)

    f.close()

    performance_site_fields = PerformanceSite._meta.get_all_field_names()

    for site in performance_sites:
        for key in site.keys():
            if key in performance_site_fields:
                site[key] = cast_field_value(
                    PerformanceSite._meta.get_field(key),
                    site[key])
            else:
                del site[key]

    return performance_sites


def get_proposal_statistics_report(from_date, to_date, all_fields=False):
    """Gets the proposal statistics report from Cayuse"""

    # List of fields we want to retrieve from Cayuse and include in the CSV
    REPORT_FIELDS = (
        'application_type_code',
        'proposal_id',
        'employee_id',
        'first_name',
        'last_name',
        'division_name',
        'department_name',
        'agency_name',
        'project_title',
        'project_start_date',
        'project_end_date',
        'submission_date',
        'department_code',
        'total_costs',
        'total_direct_costs',
        'total_indirect_costs',
        'total_direct_costs_y1',
        'total_indirect_costs_y1',
        'budget_first_per_start_date', 
        'budget_first_per_end_date', 
    )

    response = _make_cayuse_request('custom/summary')

    f = StringIO.StringIO(response.content)
    reader = csv.reader(f, delimiter=',')

    header = reader.next()

    if all_fields:
        header_fields = header
    else:
        header_fields = REPORT_FIELDS

    proposals = []

    for row in reader:
        proposal = dict(zip(header, row))

        status = proposal['award_proposal_status']

        if status == 'SUBMITTED' and proposal['submission_date']:
            submission_date = datetime.strptime(
                proposal['submission_date'],
                "%Y-%m-%d %H:%M:%S.%f").date()

            if submission_date >= from_date and submission_date <= to_date:
                entry = [proposal[field] for field in header_fields]
                proposals.append(entry)

    return header_fields, proposals