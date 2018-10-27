# Defines the views that handle the web request from the user and return a response.  Uses
# a combination of function-based views and class-based views.
#
# See Django documentation at https://docs.djangoproject.com/en/1.6/topics/http/views/
# and https://docs.djangoproject.com/en/1.6/topics/class-based-views/

import re
from django.shortcuts import render, redirect, get_object_or_404, resolve_url
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.core import management
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.apps import apps
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView, UpdateView, CreateView, DeleteView
from django.utils import timezone
from django.contrib.auth import (
    REDIRECT_FIELD_NAME, get_user_model, logout as auth_logout, update_session_auth_hash,
)
from django.utils.translation import LANGUAGE_SESSION_KEY
from crispy_forms.utils import render_crispy_form
import copy
import csv
from datetime import date, datetime
import json
from StringIO import StringIO
import xlwt
from dateutil.tz import tzutc, tzlocal

from .forms import AwardForm, EditAwardForm, ProposalIntakeStandaloneForm, ProposalIntakeForm, ProposalForm, \
    KeyPersonnelForm, PerformanceSiteForm, AwardAcceptanceForm, AwardNegotiationForm, AwardSetupForm, PTANumberForm, \
    SubawardListForm, SubawardForm, AwardManagementForm, PriorApprovalForm, ReportSubmissionForm, AwardCloseoutForm, \
    FinalReportForm, EASMappingForm, ProposalStatisticsReportForm, AwardREAssaignementForm
from .models import ProposalIntake, Proposal, KeyPersonnel, PerformanceSite, Award, AwardAcceptance, AwardNegotiation,\
    AwardSetup, PTANumber, Subaward, AwardManagement, PriorApproval, ReportSubmission, AwardCloseout, FinalReport, \
    EASMapping, EASMappingException, AwardModification, NegotiationStatus, ATPAuditTrail
from .utils import get_cayuse_submissions, get_cayuse_summary, get_cayuse_pi, get_key_personnel, get_performance_sites, \
    cast_lotus_value, get_proposal_statistics_report, get_cayuse_submissions_from_proposals_table
from core.utils import make_eas_request


@login_required
def audittrail_activity_history(request):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="audit_trail_history.xls"'

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('ATP')

    row_num = 0

    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    columns = ['Award', 'Modification', 'Workflow Step', 'Date Created', 'Date Completed', 'Assigned User', ]

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    font_style = xlwt.XFStyle()

    rows = ATPAuditTrail.objects.all().values_list('award', 'modification', 'workflow_step', 'date_created', 'date_completed', 'assigned_user')
    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            if type(row[col_num]) == datetime:
                ws.write(row_num, col_num, row[col_num].astimezone(tzlocal()).strftime('%m/%d/%Y %H:%M:%S'), font_style)
            else:
                ws.write(row_num, col_num, row[col_num], font_style)

    wb.save(response)
    return response

def required(wrapping_functions,patterns_rslt):
    if not hasattr(wrapping_functions,'__iter__'):
        wrapping_functions = (wrapping_functions,)

    return [
        _wrap_instance__resolve(wrapping_functions, instance)
        for instance in patterns_rslt
    ]

def _wrap_instance__resolve(wrapping_functions, instance):
    if not hasattr(instance, 'resolve'): return instance
    resolve = getattr(instance, 'resolve')

    def _wrap_func_in_returned_resolver_match(*args, **kwargs):
        rslt = resolve(*args, **kwargs)

        if not hasattr(rslt, 'func'):
            return rslt
        f = getattr(rslt, 'func')

        for _f in reversed(wrapping_functions):
            f = _f(f)

        setattr(rslt,'func',f)

        return rslt

    setattr(instance,'resolve',_wrap_func_in_returned_resolver_match)

    return instance

def logout(request, next_page=None,template_name='registration/logged_out.html',
           redirect_field_name=REDIRECT_FIELD_NAME,
           current_app=None, extra_context=None):

    auth_logout(request)

    if next_page is not None:
        next_page = resolve_url(next_page)

    if (redirect_field_name in request.POST or
            redirect_field_name in request.GET):
        next_page = request.POST.get(redirect_field_name,
                                     request.GET.get(redirect_field_name))
        if not is_safe_url(url=next_page, host=request.get_host()):
            next_page = request.path

    language = request.session.get(LANGUAGE_SESSION_KEY)
    request.session.flush()
    if language is not None:
        request.session[LANGUAGE_SESSION_KEY] = language
    if hasattr(request, 'user'):
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
    if next_page:
        # Redirect to this page until the session has been cleared.
        return HttpResponseRedirect(next_page)

    current_site = get_current_site(request)
    context = {
        'site': current_site,
        'site_name': current_site.name,
        'title': ('Logged out')
    }
    if extra_context is not None:
        context.update(extra_context)

    if current_app is not None:
        request.current_app = current_app

    return TemplateResponse(request, template_name, context)

@login_required
def home(request):
    """Renders the default view for the awards app"""
    intake_filter = Q(Q(proposal_due_to_sponsor__gte=date.today()) | Q(proposal_due_to_sponsor=None)) & \
                    Q(Q(proposal_status='PE') | Q(proposal_status='RO') | Q(proposal_status=''))
    if 'all_proposals' in request.GET:
        intake_filter = Q()
    if 'upcoming_proposals' in request.GET:
        intake_filter = intake_filter
    proposal_intakes = ProposalIntake.objects.filter(intake_filter).order_by('proposal_due_to_sponsor')
    award_setup_priorities = Award.get_priority_assignments_for_award_setup_user(request.user)
    assignments = Award.get_assignments_for_user(request.user)
    assignment_list = copy.deepcopy(assignments)
    award_setup_modification_flag = False
    user_type_flag = False
    user_groups = request.user.groups.all()
    for group in user_groups:
        if group.name == 'Award Modification':
            user_type_flag = True
    if user_type_flag:
        award_setup_modification_flag = True

    for award in assignments:
        if award in award_setup_priorities:
            assignment_list.remove(award)

    return render(request, 'awards/index.html',
                  {'proposal_intakes': proposal_intakes,
                   'assignment_list': assignment_list,
                   'award_setup_priorities': award_setup_priorities,
                   'award_setup_modification_flag': award_setup_modification_flag
                   }
                  )


class FullAwardSearchView(TemplateView):
    """Displays the full award search page"""

    template_name = 'awards/full_award_search.html'

    def get_context_data(self, **kwargs):
        context = super(FullAwardSearchView, self).get_context_data(**kwargs)

        # Add an empty instance of each section so we can get its fields' verbose_names
        context['sections'] = [
            ProposalIntake(),
            Proposal(),
            AwardAcceptance(),
            AwardNegotiation(),
            AwardSetup(),
            AwardManagement(),
            AwardCloseout()]

        context['blank_subaward'] = Subaward()
        context['blank_pta_number'] = PTANumber()
        return context


@login_required
def get_awards_ajax(request):
    """Provide homepage award data as JSON to improve render time"""

    awards = Award.objects.filter(status__lt=6)

    response = {'data': []}

    for award in awards:
        award_data = []

        proposal = award.get_first_real_proposal()

        if proposal:
            proposal_or_award_number = proposal.get_unique_identifier()
            if proposal_or_award_number == '':
                proposal_or_award_number = award.id

            award_data.append(
                '<a href="%s">%s</a>' %
                (reverse(
                    'award_detail',
                    kwargs={
                        'award_pk': award.id}),
                    proposal_or_award_number))
            award_data.append(award.get_award_numbers())
            award_data.append(str(proposal.principal_investigator))
            award_data.append(str(proposal.agency_name))
            award_data.append(proposal.project_title)
            award_data.append(award.get_date_assigned_to_current_stage())
            award_data.append(award.get_current_active_users())
        else:
            award_data.extend(
                [
                    '<a href="%s">%s</a>' %
                    (reverse(
                        'award_detail',
                        kwargs={
                            'award_pk': award.id}),
                        award),
                    award.get_award_numbers(),
                    'N/A',
                    'N/A',
                    'N/A',
                    award.get_date_assigned_to_current_stage(),
                    award.get_current_active_users()])

        award_data.append(award.get_current_award_status_for_display()
                          if all([award.award_dual_negotiation, award.award_dual_setup, award.status == 2]) or
                             all([award.award_dual_modification, award.status == 2])
                          else award.get_status_display())
        award_data.append(Award.WAIT_FOR.get(award.awardsetup.wait_for_reson)
                          if (award.status == 3)
                          else None)
        response['data'].append(award_data)

    json_data = json.dumps(response)

    return HttpResponse(json_data, content_type="application/json")


def construct_query_for_field(field, fieldValue, endDate, callingSection):
    """Builds a database query for the given field and values.  Used in the full award search."""

    temp = field.split('|')
    parent_model_name = temp[0]
    field_name_actual = temp[1]

    parent_model = globals()[parent_model_name]()
    field_object = parent_model._meta.get_field(field_name_actual)
    field_type = field_object.get_internal_type()
    parent_model_name = parent_model_name.lower()

    if callingSection != 'award':
        if callingSection != parent_model_name:
            if parent_model_name == 'award':
                parent_model_name += '__'
            else:
                parent_model_name = 'award__{0}__'.format(parent_model_name)
        else:
            parent_model_name = ''
    else:
        if parent_model_name == 'award':
            parent_model_name = ''
        else:
            parent_model_name += '__'

    if not field_type == 'DateField':
        if field_type == 'NullBooleanField':
            if fieldValue == '1':
                fieldValue = None
            else:
                fieldValue = fieldValue == '2'

            arg1 = '{0}{1}'.format(parent_model_name, field_name_actual)

        elif field_type in ['CharField', 'TextField']:
            filter_condition = ''
            if not field_object.choices:
                filter_condition = '__icontains'

            arg1 = '{0}{1}{2}'.format(parent_model_name, field_name_actual, filter_condition)

        elif field_type in ['ForeignKey', 'IntegerField', 'DecimalField']:
            arg1 = '{0}{1}'.format(parent_model_name, field_name_actual)

        args = {
            '{0}'.format(arg1) : fieldValue
        }
    else:
        arg1 = None
        arg2 = None
        args = {}

        if not fieldValue == '':
            arg1 = '{0}{1}__gte'.format(parent_model_name, field_name_actual)

        if not endDate == '':
            arg2 = '{0}{1}__lte'.format(parent_model_name, field_name_actual)
        
        if not arg1 == None:
            start_date = datetime.strptime(fieldValue, '%m/%d/%Y')
            args[arg1] = start_date

        if not arg2 == None:
            end_date = datetime.strptime(endDate, '%m/%d/%Y')
            args[arg2] = end_date

    if (parent_model_name in ['awardacceptance', 'awardnegotiation']):
        args['{0}{1}'.format(parent_model_name, 'current_modification')] = True
    elif (parent_model_name == 'proposal'):
        args['{0}{1}'.format(parent_model_name, 'dummy')] = False

    return args


def get_search_filters_query(request, callingSection):
    """Reads the request from the full award search page and constructs a query from the inputs"""

    # Apply filters here
    query = Q()

    fieldOne = request.GET.get('fieldOne', '')
    fieldOneValue = request.GET.get('fieldOneValue', "")
    fieldOneEndDate = request.GET.get('fieldOneEndDate', '')
    if not fieldOne == '' and (not fieldOneValue == '' or not fieldOneEndDate == ''):
        args = construct_query_for_field(fieldOne, fieldOneValue, fieldOneEndDate, callingSection)
        query = Q(**args)

        fieldTwo = request.GET.get('fieldTwo', '')
        fieldTwoValue = request.GET.get('fieldTwoValue', '')
        fieldTwoEndDate = request.GET.get('fieldTwoEndDate', '')
        if not fieldTwo == '' and (not fieldTwoValue == '' or not fieldTwoEndDate == ''):
            args = construct_query_for_field(fieldTwo, fieldTwoValue, fieldTwoEndDate, callingSection)

            conditionOne = request.GET.get('conditionOne', '')
            if conditionOne == 'or':
                query = query | Q(**args)
            else:
                query = query & Q(**args)

            fieldThree = request.GET.get('fieldThree', '')
            fieldThreeValue = request.GET.get('fieldThreeValue', '')
            fieldThreeEndDate = request.GET.get('fieldThreeEndDate', '')
            if not fieldThree == '' and (not fieldThreeValue == '' or not fieldThreeEndDate == ''):
                args = construct_query_for_field(fieldThree, fieldThreeValue, fieldThreeEndDate, callingSection)

                conditionTwo = request.GET.get('conditionTwo', '')
                if conditionTwo == 'or':
                    query = query | Q(**args)
                else:
                    query = query & Q(**args)

    return query

@login_required
def get_search_awards_ajax(request):
    """Provide full search award data as JSON to improve render time"""
    query = get_search_filters_query(request, 'award')

    awards = Award.objects.filter(query).distinct()

    response = {'data': []}

    for award in awards:
        award_data = []
        award_sections = []

        if hasattr(award, 'proposalintake'):
            proposal_intake = award.proposalintake
        else:
            proposal_intake = ProposalIntake()
        award_sections.append(proposal_intake)

        proposal = award.get_first_real_proposal()
        if not proposal:
            proposal = Proposal()
        award_sections.append(proposal)
        award_sections.append(award.get_current_award_acceptance(True))
        award_sections.append(award.get_current_award_negotiation())
        if hasattr(award, 'awardsetup'):
            award_sections.append(award.awardsetup)
        else:
            awardsetup = AwardSetup()
            award_sections.append(awardsetup)
        if hasattr(award, 'awardmanagement'):
            award_sections.append(award.awardmanagement)
        else:
            awardmanagement = AwardManagement()
            award_sections.append(awardmanagement)
        if hasattr(award, 'awardcloseout'):
            award_sections.append(award.awardcloseout)
        else:
            awardcloseout = AwardCloseout()
            award_sections.append(awardcloseout)

        # Include basic award data
        award_data.append(
            '<a href="%s">%s</a>' %
            (reverse(
                'award_detail',
                kwargs={
                    'award_pk': award.id}),
                award))
        award_data.append(award.id)
        award_data.append(award.get_current_award_status_for_display()
                          if (award.award_dual_negotiation and award.award_dual_setup and award.status == 2) or
                             (award.award_dual_modification and award.status == 2)
                          else award.get_status_display())

        user_fields = [
            'award_acceptance_user',
            'award_negotiation_user',
            'award_setup_user',
            'subaward_user',
            'award_management_user',
            'award_closeout_user']
        for user_field in user_fields:
            user = getattr(award, user_field)
            if user:
                award_data.append(user.get_full_name())
            else:
                award_data.append(None)

        for section in award_sections:
            [award_data.append(value.encode('utf-8') if isinstance(value, basestring) else str(value))
             for key, value, boolean, field_name in section.get_search_fields()]

        response['data'].append(award_data)

    json_data = json.dumps(response)

    return HttpResponse(json_data, content_type="application/json")

@login_required
def get_search_subawards_ajax(request):
    """Provide full search subaward data as JSON to improve render time"""
    
    query = get_search_filters_query(request, 'subaward')

    subawards = Subaward.objects.filter(query).distinct()

    response = {'data': []}

    for subaward in subawards:
        award_data = []
        award_sections = []

        award_sections.append(subaward)

        # Include basic award data
        award_data.append(
            '<a href="%s#subawards">%s</a>' %
            (reverse(
                'award_detail',
                kwargs={
                    'award_pk': subaward.award.id}),
                subaward))
        award_data.append(subaward.award.id)

        for section in award_sections:
            [award_data.append(value.encode('utf-8') if isinstance(value, basestring) else str(value))
             for key, value, boolean, field_name in section.get_search_fields()]

        response['data'].append(award_data)

    json_data = json.dumps(response)

    return HttpResponse(json_data, content_type="application/json")

@login_required
def get_search_pta_numbers_ajax(request):
    """Provide full search pta number data as JSON to improve render time"""

    query = get_search_filters_query(request, 'ptanumber')

    ptaNumbers = PTANumber.objects.filter(query).distinct()

    response = {'data': []}

    for ptaNumber in ptaNumbers:
        award_data = []
        award_sections = []

        award_sections.append(ptaNumber)

        # Include basic award data
        award_data.append(
            '<a href="%s#ptanumbers">%s</a>' %
            (reverse(
                'award_detail',
                kwargs={
                    'award_pk': ptaNumber.award.id}),
                ptaNumber))
        award_data.append(ptaNumber.award.id)

        for section in award_sections:
            [award_data.append(value.encode('utf-8') if isinstance(value, basestring) else str(value))
             for key, value, boolean, field_name in section.get_search_fields()]

        response['data'].append(award_data)

    json_data = json.dumps(response)

    return HttpResponse(json_data, content_type="application/json")

@login_required
def get_search_filter_ajax(request, field_name):
    """Provide auto-generated HTML depending on data type of filter field"""
    if field_name == '':
        return HttpResponse(unicode(''))

    temp = field_name.split('|')
    parent_model_name = temp[0]
    field_name_actual = temp[1]

    if parent_model_name == 'Award' and field_name_actual == 'status':
        status_choices = Award.STATUS_CHOICES

        result = "<select id='id_status' name='status'>"
        result += "<option value='' selected='selected'>---------</option>"
        for choice in status_choices:
            result +=   "<option value='{0}'>{1}</option>".format(choice[0], choice[1])
        result += "</select>"
    else:
        parent_model = globals()[parent_model_name]()
        field_type = parent_model._meta.get_field(field_name_actual).get_internal_type()

        if field_type == 'DateField':
            result = "Date range start: <input class='datePicker dateinput form-control' id='id_" + field_name_actual + "_start' name='" + field_name_actual +"_start' type='text' value=''> Date range end: <input class='datePicker dateinput form-control' id='id_" + field_name_actual + "_end' name='" + field_name_actual +"_end' type='text' value=''>"
        else:
            form = globals()[parent_model_name + 'Form']()
            result = form[field_name_actual]

    return HttpResponse(unicode(result))

@login_required
def get_lotus_proposals_ajax(request, award_pk):
    """Provide Lotus proposals as JSON to improve render time"""

    proposals = Proposal.objects.exclude(
        lotus_id='').values(
        'lotus_id',
        'project_title',
        'employee_id',
        'sponsor_deadline')

    response = {'data': []}
    for proposal in proposals:
        import_url = '<a href="%s">Add to award</a>' % reverse(
            'import_lotus_proposal',
            kwargs={
                'lotus_id': proposal['lotus_id'],
                'award_pk': award_pk})
        response['data'].append([import_url,
                                 proposal['lotus_id'],
                                 proposal['project_title'],
                                 proposal['employee_id'],
                                 str(proposal['sponsor_deadline'])]
                                )

    json_data = json.dumps(response)

    return HttpResponse(json_data, content_type='application/json')


@login_required
def import_eas_data(request, endpoint):
    """Manually run the import_eas_data command for a specific API endpoint"""

    content = StringIO()
    management.call_command('import_eas_data', endpoint, stdout=content)

    content.seek(0)
    response = content.read()

    return render(request, 'awards/import_eas_data.html',
                  {'response': response, }
                  )

@login_required
def get_award_number_ajax(request, award_pk, pta_pk):
    """Makes an HTTP call to EAS to get a new award number for the given PTANumber"""

    endpoint = 'get_smart_awrdno'
    PARAMETERS = '''<get:InputParameters>
         <get:P_AWARD_TEMP_ID>{award_temp_id}</get:P_AWARD_TEMP_ID>
         <get:P_AGENCY_ID>{agency_id}</get:P_AGENCY_ID>
         <get:P_ORG_ID>{org_id}</get:P_ORG_ID>
         <get:P_PRIME_SPONSOR_ID>{prime_sponsor_id}</get:P_PRIME_SPONSOR_ID>
      </get:InputParameters>'''

    if request.method == 'POST':
        award_template_id = request.POST['award_template_id']
        agency_id = request.POST['agency_id']
        org_id = request.POST['org_id']
        prime_sponsor_id = request.POST['prime_sponsor_id']
        parameters = PARAMETERS.format(award_temp_id=award_template_id, agency_id=agency_id, org_id=org_id, prime_sponsor_id=prime_sponsor_id)

        try:
            root = make_eas_request(endpoint, parameters)
            award_number = root[1][0][0].text
            error_message = root[1][0][1].text
        except:
            award_number = None
            error_message = 'Error communicating with EAS'

        if error_message:
            award_number = None

        if award_number:
            pta_number = PTANumber.objects.get(pk=pta_pk)
            pta_number.award_number = award_number
            pta_number.save()

        response = {'award_number': award_number, 'error': error_message}

        json_data = json.dumps(response)

        return HttpResponse(json_data, content_type='application/json')
    else:
        raise Http404('Method does not support a GET request.')

@login_required
def pick_proposal(request, award_pk, lotus=False):
    """Renders the proposal selection screen"""

    data = {}
    data['award'] = get_object_or_404(Award, pk=award_pk)

    if lotus:
        data['proposals'] = Proposal.objects.exclude(lotus_id='')
        template = 'awards/lotus_proposal_list.html'
    else:
        if 'all-proposals' in request.GET:
            # data['proposals'] = get_cayuse_submissions(True)
            data['proposals'] = get_cayuse_submissions_from_proposals_table(True)
            data['all_proposals'] = True
        else:
            # data['proposals'] = get_cayuse_submissions()
            data['proposals'] = get_cayuse_submissions_from_proposals_table()
        template = 'awards/proposal_list.html'

    return render(request, template, data)


@login_required
def get_cayuse_proposals(request):
    proposals = get_cayuse_submissions()
    for proposal in proposals:
        prop = Proposal(**proposal)
        prop.save()
    return render(request, 'awards/import_cayuse_proposals.html', {})


@login_required
@transaction.atomic # Atomic transaction so we rollback on failure
def import_proposal(request, proposal_id, award_pk):
    """Imports the selected proposal, if it hasn't been imported already"""

    award = get_object_or_404(Award, pk=award_pk)

    try:
        existing_proposal = Proposal.objects.get(proposal_id=proposal_id)
    except Proposal.DoesNotExist:
        existing_proposal = None

    # Check if this proposal has already been associated to another award
    if existing_proposal:
        if existing_proposal.award:
            messages.error(request, "%s is already tied to this award. If you \
                need to associate it with another award, contact an administrator." % existing_proposal)
            return redirect(existing_proposal.award)
        else:
            existing_proposal.delete()

    # Import the proposal from Cayuse
    try:
        cayuse_data = get_cayuse_summary(proposal_id)
        pi = get_cayuse_pi(
            cayuse_data['principal_investigator'],
            cayuse_data['proposal']['employee_id'])

    # Ask the user to manually reconcile data to an EAS-approved value if ATP 
    # doesn't know how to already
    except EASMappingException as e:
        eas_mapping_url = reverse(
            'create_eas_mapping',
            kwargs={
                'interface': e.interface,
                'field': e.field,
                'incoming_value': e.incoming_value,
                'atp_model': e.atp_model.__name__})
        request.session['import_url'] = request.path
        return HttpResponseRedirect(eas_mapping_url)

    # Create the proposal
    proposal = Proposal.objects.create(
        principal_investigator=pi,
        award=award,
        **cayuse_data['proposal'])

    # Update fields on the AwardManager (PI)
    [setattr(pi, key, value) for key, value in cayuse_data['principal_investigator'].items()]
    pi.save()

    # Fetch and create KeyPersonnel
    key_personnel = get_key_personnel(proposal_id)
    [KeyPersonnel.objects.create(proposal=proposal, **person) for person in key_personnel]

    # Fetch and create PerformanceSites
    performance_sites = get_performance_sites(proposal_id)
    [PerformanceSite.objects.create(proposal=proposal, **site) for site in performance_sites]

    return redirect(award)


@login_required
@transaction.atomic # Atomic transaction so we rollback on failure
def import_lotus_proposal(request, lotus_id, award_pk):
    """Imports the selected proposal from Lotus.

    NOTE: No actual import happens here, all Lotus proposals were already loaded into ATP from
    the start.  This just associates the selected proposal with the given award.
    """
    award = get_object_or_404(Award, pk=award_pk)

    # Get the Lotus Notes proposal (loaded into ATP at go-live)
    proposal = Proposal.objects.get(lotus_id=lotus_id)

    if proposal.award:
        messages.error(request, "%s is already tied to this award. If you \
            need to associate it with another award, contact an administrator." % proposal)
        return redirect(proposal.award)

    # Associate Lotus Notes values to EAS-approved values (similar to process above)
    for lotus_field, fk_field_name in Proposal.LOTUS_FK_LOOKUPS.items():
        fk_field = Proposal._meta.get_field(fk_field_name)
        lotus_value = getattr(proposal, lotus_field)

        if not lotus_value:
            continue

        try:
            eas_value = cast_lotus_value(fk_field, lotus_value)
            setattr(proposal, fk_field_name, eas_value)
        except EASMappingException as e:
            eas_mapping_url = reverse(
                'create_eas_mapping',
                kwargs={
                    'interface': e.interface,
                    'field': e.field,
                    'incoming_value': e.incoming_value,
                    'atp_model': e.atp_model.__name__})
            request.session['award_url'] = award.get_absolute_url()
            request.session['import_url'] = request.path
            return HttpResponseRedirect(eas_mapping_url)

    proposal.award = award
    proposal.save()

    return redirect(award)


@login_required
def create_eas_mapping(request, interface, field, incoming_value, atp_model):
    """Renders the page that allows users to create a mapping between data that came
    from EAS and the existing data in ATP.
    """

    atp_model = apps.get_model('awards', atp_model)

    if request.method == 'POST':
        # Create a new EAS mapping and re-try the import
        form = EASMappingForm(atp_model, request.POST)
        if form.is_valid():
            mapping = EASMapping(
                interface=interface,
                field=field,
                incoming_value=incoming_value,
                atp_model=atp_model.__name__)
            mapping.atp_pk = form.cleaned_data['atp_value'].pk
            mapping.save()

            import_url = request.session.pop('import_url')
            return HttpResponseRedirect(import_url)
    else:
        # First check to make sure the mapping doesn't already exist
        # (if the user clicked the back button mid-import)
        try:
            mapping = EASMapping.objects.get(
                interface=interface,
                field=field,
                incoming_value=incoming_value,
                atp_model=atp_model.__name__)
            if mapping:
                return HttpResponseRedirect(request.session['import_url'])
        except EASMapping.DoesNotExist:
            pass

        form = EASMappingForm(atp_model)

    return render(request, 'awards/create_eas_mapping.html', {
        'form': form,
        'field': Proposal._meta.get_field(field).verbose_name,
        'incoming_value': incoming_value,
        'award_url': request.session.get('award_url', None)
    })


@login_required
def create_modification(request, award_pk):
    """Renders the page to create an award modification"""

    award = get_object_or_404(Award, pk=award_pk)

    if request.method == 'GET':
        # Display the warning screen, explaining to the user what ATP will do
        return render(request,
                      'awards/confirm_modification.html', {'award': award,
                                                           'editable_sections': award.get_editable_sections()})
    elif request.method == 'POST' and request.POST.get('_method'):
        return render(request,
                      'awards/rename_modification_award.html', {'award': award,
                                                                'editable_sections': award.get_editable_sections(),
                                                                })
    else:
        with transaction.atomic():
            # Duplicate the AwardAcceptance and AwardNegotiation objects
            award_type = request.POST.get('award_type')
            for current_section in [award.get_current_award_acceptance(), award.get_current_award_negotiation()]:
                new_section = current_section

                current_section.current_modification = False

                if hasattr(current_section, 'phs_funded'):
                    if current_section.phs_funded:
                        award.send_phs_funded_notification_with_modification()

                current_section.save()
                if award_type == 'Modification':
                    modification_list = []
                    award_acceptance = AwardAcceptance.objects.filter(award_id=award.id)
                    for accept in award_acceptance:
                        if accept.award_text and '#' in accept.award_text:
                            modification_list.append(int(re.search(r'\d+', accept.award_text).group()))
                    if modification_list:
                        award_type = 'Modification #%d' % (max(modification_list)+1)
                    else:
                        award_type = 'Modification #1'
                new_section.pk = None
                new_section.date_assigned = None
                new_section.current_modification = True
                new_section.award_text = award_type
                if hasattr(new_section, 'acceptance_completion_date'):
                    new_section.acceptance_completion_date = None
                if hasattr(new_section, 'negotiation_completion_date'):
                    new_section.negotiation_completion_date = None
                if hasattr(new_section, 'fcoi_cleared_date'):
                    new_section.fcoi_cleared_date = None
                if hasattr(new_section, 'new_funding'):
                    new_section.new_funding = None
                if hasattr(new_section, 'award_issue_date'):
                    new_section.award_issue_date = None
                if hasattr(new_section, 'award_acceptance_date'):
                    new_section.award_acceptance_date = None
                if hasattr(new_section, 'negotiation_status'):
                    new_section.negotiation_status = 'IQ'
                    if hasattr(new_section, 'comments'):
                        new_section.comments = ''
                if hasattr(new_section, 'negotiation_notes'):
                    new_section.negotiation_notes = ''

                new_section.save()

        # Reset the award's status to Award Intake
        try:
            setup_object = AwardSetup.objects.get(award=award)
        except AwardSetup.DoesNotExist:
            setup_object = None
        if setup_object:
            setup_object.wait_for_reson = None
            setup_object.save()
        existing_modification = AwardModification.objects.all().filter(award_id=award.id).order_by('-id')
        if existing_modification:
            modification_object = existing_modification[0]
            modification_object.is_edited = True
            modification_object.save()

        modification = AwardModification.objects.create(award=award)
        modification.save()
        award.status = award.AWARD_ACCEPTANCE_STATUS
        award.award_dual_setup = False
        award.award_dual_negotiation=False
        award.subaward_done = False
        award.award_management_done = False
        award.send_to_modification = False
        award.award_dual_modification = False
        award.common_modification = False

        award.save(check_status=False)
        award.send_email_update()

        messages.info(request, 'A new modification has been added to this award. \
            It has been reset to the Award Intake status and %s has been sent \
            an email notification.' % ' and '.join([user.get_full_name() for user in award.get_users_for_active_sections()])
                      )
        try:
            not_complted = ATPAuditTrail.objects.filter(award=award.id, date_completed=None).exclude(workflow_step='AwardAcceptance')
            for audit in not_complted:
                audit.date_completed = datetime.now()
                audit.save()
        except:
            pass

        try:
            complted = ATPAuditTrail.objects.filter(
                award=award.id, date_completed=None, workflow_step='AwardAcceptance').order_by('-id')
            for audit in complted[1:]:
                audit.date_completed = datetime.now()
                audit.save()
        except:
            pass
        return redirect(reverse('edit_award_acceptance', kwargs={'award_pk': award.id}))


class CreateAwardView(CreateView):
    """Create an award from a ProposalIntake"""

    model = Award
    form_class = AwardForm

    def dispatch(self, request, *args, **kwargs):
        self.proposal_intake = ProposalIntake.objects.get(
            pk=self.kwargs['proposalintake_pk'])
        if self.proposal_intake.award:
            messages.info(self.request, '%s is already associated with this award. \
                If you need to change that, contact an ATP administrator.' % self.proposal_intake)
            return redirect(self.proposal_intake.award)

        return super(CreateAwardView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        redirect = super(CreateAwardView, self).form_valid(form)
        self.proposal_intake.award = self.object
        self.proposal_intake.save()
        self.object.move_to_next_step()
        return redirect


def get_award_type_value(request, award_id):
    return render(request, 'awards/rename_original_award.html', {'award_pk': award_id})


def redirect_to_award_details(request, award_pk):
    """
    This method is going to move award to next stage and then redirect to the award details page
    :param request: request object
    :param award_pk: award id
    :return: HttpResponse will redirect the award details page
    """
    award = Award.objects.get(id=award_pk)
    award.move_to_next_step()
    award_text = request.POST.get('award_text')
    award.award_text = award_text
    award.save()
    return HttpResponseRedirect(award.get_absolute_url())


class CreateAwardStandaloneView(CreateView):
    """Create an award from the homepage"""

    model = Award
    form_class = AwardForm

    def form_valid(self, form):
        #redirect = super(CreateAwardStandaloneView, self).form_valid(form)
        super(CreateAwardStandaloneView, self).form_valid(form)
        #self.object.move_to_next_step()
        #return redirect
        return get_award_type_value(self.request, self.object.id)



class EditAwardView(UpdateView):
    """Edit an existing award"""

    model = Award
    form_class = EditAwardForm
    pk_url_kwarg = 'award_pk'


class AwardDetailView(DetailView):
    """Read-only view of all data for an individual award"""

    model = Award
    pk_url_kwarg = 'award_pk'
    template_name = 'awards/award_base.html'

    def get_context_data(self, **kwargs):
        context = super(AwardDetailView, self).get_context_data(**kwargs)
        context['editable_sections'] = context['award'].get_editable_sections()
        award = context['award']
        award_modification_flag = False
        if award.send_to_modification or award.common_modification:
            award_modification_flag = True
        section_object = AwardModification.objects.all().filter(award=award).order_by('-id')
        if section_object:
            section_object = section_object[0]
        context['modification_obj'] = section_object
        context['award_modification_flag'] = award_modification_flag

        pta_instance = PTANumber.objects.all().filter(award_id=context['award'].id, is_edited=True).order_by('pta_number_updated')
        if pta_instance:
            pta_instance = pta_instance[0]
        context['pta_nuber_instance'] = pta_instance
        return context


class CheckEditPermissionsMixin(object):
    """Checks to make sure the current user can edit the requested section"""

    def dispatch(self, request, *args, **kwargs):
        award = get_object_or_404(Award, pk=self.kwargs['award_pk'])
        redirect_url = HttpResponseRedirect(award.get_absolute_url())

        # Make sure that the requested PTA # is associated with this award
        if 'pta_pk' in self.kwargs:
            pta = get_object_or_404(PTANumber, pk=self.kwargs['pta_pk'])
            if pta.award != award:
                messages.error(self.request, '%s is not associated with %s. If you \
                believe this is an error, contact the ATP administrator.' % (pta, award))
                return redirect_url

        # Get the assigned user if the section isn't ProposalIntake (which has no assigned user)
        setup_flow_flag = False
        if (self.model.__name__ == 'AwardSetup' or self.model.__name__ == 'PTANumber') and award.award_dual_setup:
            setup_flow_flag = True

        if (self.model.__name__ == 'AwardSetup' or self.model.__name__ == 'PTANumber') and award.award_dual_modification:
            setup_flow_flag = True

        if self.model.__name__ != 'ProposalIntake':
            assigned_user = award.get_user_for_section(self.model.__name__)

            if not assigned_user:
                messages.info(
                    self.request,
                    '%s does not have this section. To add it, assign a user to this section in the administrator interface.' %
                    award)
                return redirect_url
            elif award.get_edit_status_for_section(self.model.__name__, setup_flow_flag) > award.status:
                messages.info(
                    self.request,
                    'You cannot edit that section yet. The %s section needs to be completed first.' %
                    award.get_status_display())
                return redirect_url

        return super(
            CheckEditPermissionsMixin,
            self).dispatch(
            request,
            *args,
            **kwargs)


class AwardContextMixin(object):
    """Adds extra context data to a response"""

    def get_context_data(self, **kwargs):
        context = super(AwardContextMixin, self).get_context_data(**kwargs)
        award = Award.objects.get(pk=self.kwargs['award_pk'])
        context['award'] = award
        context['editable_sections'] = award.get_editable_sections()

        if hasattr(self, 'disable_autosave'):
            context['disable_autosave'] = self.disable_autosave

        if 'proposal_pk' in self.kwargs:
            context['proposal'] = Proposal.objects.get(
                pk=self.kwargs['proposal_pk'])

        return context


class MoveToNextStepMixin(object):
    """Handles moving a section to the next step"""

    def form_valid(self, form):
        super(MoveToNextStepMixin, self).form_valid(form)

        award = Award.objects.get(pk=self.kwargs['award_pk'])
        count_value = AwardAcceptance.objects.filter(award=award).count()
        modification = 'Modification #%s' % (count_value - 1)
        origional_text = 'Original Award'
        setup_workflow = 'AwardSetup'
        modification_workflow = 'AwardModification'
        if form.cleaned_data.get('do_not_send_to_next_step'):
            messages.info(self.request, 'Award Setup for this award has been marked as complete. This award '
                                        'will not move to the next step until Award Negotiation is also completed.')
            if all([award.award_dual_negotiation, award.award_dual_setup, not award.send_to_modification]):
                try:
                    setup_object = AwardSetup.objects.get(award=self.award)
                    setup_object.setup_completion_date = timezone.localtime(timezone.now())
                    setup_object.save()
                    if count_value < 2:
                        award.record_current_state_to_atptrail(origional_text, setup_workflow)
                    else:
                        award.record_current_state_to_atptrail(modification, setup_workflow)
                except:
                    pass
            if all([award.award_dual_modification, award.common_modification]):
                try:
                    modification_object = AwardModification.objects.all().filter(award=self.award, is_edited=True).\
                        order_by('-id')
                    if modification_object:
                        modification_obj = modification_object[0]
                        modification_obj.modification_completion_date = timezone.localtime(timezone.now())
                        modification_obj.save()
                        award.record_current_state_to_atptrail(modification, modification_workflow)
                except:
                    pass
            return HttpResponseRedirect(award.get_absolute_url())

        if form.cleaned_data.get('pta_modification') and form.cleaned_data.get('move_to_multiple_steps'):
            dual_modification = True
            award.move_award_to_negotiation_and_modification(dual_modification)
            if award.award_negotiation_user:
                messages.info(
                    self.request,
                    'This award has been moved to the %s and Modification phase. \
                    It is now assigned to %s.' %
                    (award.get_status_display(),
                     ' and '.join(
                         [
                             user.get_full_name() for user in
                             award.get_users_for_negotiation_and_moidification_sections()])))
            else:
                messages.info(
                    self.request,
                    'This award has been moved to the Modification phase. It is now assigned to %s.' %
                    (' and '.join(
                         [
                             user.get_full_name() for user in
                             award.get_users_for_negotiation_and_moidification_sections()])))
            return HttpResponseRedirect(award.get_absolute_url())

        if form.cleaned_data.get('move_to_next_step') or form.cleaned_data.get('move_to_multiple_steps'):
            dual_mode = False
            if form.cleaned_data.get('pta_modification') and form.cleaned_data.get('move_to_next_step'):
                award.move_setup_or_modification_step(modification_flag=True)
                messages.info(
                    self.request,
                    'This award has been moved to the %s phase. \
                    It is now assigned to %s.' %
                    (award.get_status_display(),
                     ' and '.join(
                         [
                             user.get_full_name() for user in award.get_users_for_active_sections()])))
                return HttpResponseRedirect(award.get_absolute_url())
            elif self.model.__name__ == 'AwardAcceptance':
                atp_query = AwardAcceptance.objects.filter(award_id=self.award.id)
                if not form.cleaned_data.get('pta_modification') and not form.cleaned_data.get('move_to_multiple_steps')\
                        and atp_query.count() > 1:
                    award.move_setup_or_modification_step(setup_flag=True)
                    messages.info(
                        self.request,
                        'This award has been moved to the %s phase. \
                        It is now assigned to %s.' %
                        (award.get_status_display(),
                         ' and '.join(
                             [
                                 user.get_full_name() for user in award.get_users_for_active_sections()])))
                    return HttpResponseRedirect(award.get_absolute_url())

            if form.cleaned_data.get('move_to_multiple_steps'):
                dual_mode = True
                award_moved = award.move_award_to_multiple_steps(dual_mode)
            else:
                award_moved = award.move_to_next_step(self.model.__name__)

            if award_moved:
                if award.status == award.END_STATUS:
                    messages.info(
                        self.request,
                        'This award has been completed.')

                elif dual_mode:
                    if award.award_negotiation_user:
                        messages.info(
                            self.request,
                            'This award has been moved to the %s and Award Setup phase. \
                            It is now assigned to %s.' %
                            (award.get_status_display(),
                             ' and '.join(
                                [
                                    user.get_full_name() for user in award.get_users_for_dual_active_sections()])))
                    else:
                        messages.info(
                            self.request,
                            'This award has been moved to the %s phase. It is now assigned to %s.' %
                            (award.get_status_display(),
                             ' and '.join(
                                [
                                    user.get_full_name() for user in award.get_users_for_dual_active_sections()])))
                else:
                    messages.info(
                        self.request,
                        'This award has been moved to the %s phase. \
                        It is now assigned to %s.' %
                        (award.get_status_display(),
                         ' and '.join(
                            [
                                user.get_full_name() for user in award.get_users_for_active_sections()])))
            else:
                messages.info(self.request, 'Your section of the award has been marked as \
                    complete. This award will not move to the next step until all other \
                    sections in this phase are completed.')
            return HttpResponseRedirect(award.get_absolute_url())

        else:
            return HttpResponseRedirect(self.get_success_url())


class AutosaveFormMixin(object):
    """Handles AJAX responses for autosave requests"""

    def render_to_ajax_response(self, context, **response_kwargs):
        form_html = render_crispy_form(context['form'], context=context)
        return HttpResponse(form_html)

    def render_to_response(self, context, **response_kwargs):
        if self.request.is_ajax():
            return self.render_to_ajax_response(context, **response_kwargs)
        else:
            return super(
                AutosaveFormMixin,
                self).render_to_response(
                context,
                **response_kwargs)


class ProposalIntakeMixin(object):
    """Provides common functionality for all ProposalIntake class views"""

    model = ProposalIntake
    form_class = ProposalIntakeStandaloneForm

    def dispatch(self, request, *args, **kwargs):
        """Overrides the parent dispatch method.
        If the ProposalIntake exists and has and award, redirect to the main
        ProposalIntake view.
        """

        if 'proposalintake_pk' in self.kwargs:
            proposal_intake = ProposalIntake.objects.get(
                pk=self.kwargs['proposalintake_pk'])
            if proposal_intake.award:
                return redirect(proposal_intake)

        return super(
            ProposalIntakeMixin,
            self).dispatch(
            request,
            *args,
            **kwargs)

    def form_valid(self, form):
        super(ProposalIntakeMixin, self).form_valid(form)

        if form.cleaned_data['save_and_add']:
            messages.info(self.request, 'Your Proposal Intake has been added.')
            return HttpResponseRedirect(reverse('create_proposal_intake'))

        if form.cleaned_data['save_and_continue']:
            messages.info(self.request, 'Your Proposal Intake has been saved.')
            return HttpResponseRedirect(reverse('edit_standalone_proposal_intake', kwargs={'proposalintake_pk': form.instance.id}))

        return HttpResponseRedirect(reverse('home'))


class CreateProposalIntakeView(ProposalIntakeMixin, CreateView):
    """Create a new ProposalIntake"""

    template_name = 'awards/proposalintake_standalone_form.html'
    success_url = reverse_lazy('home')

    def get_context_data(self, **kwargs):
        context = super(
            CreateProposalIntakeView,
            self).get_context_data(
            **kwargs)
        context['disable_autosave'] = True
        return context


class EditProposalIntakeView(
        AutosaveFormMixin,
        ProposalIntakeMixin,
        UpdateView):
    """Edit an existing ProposalIntake"""

    pk_url_kwarg = 'proposalintake_pk'
    template_name = 'awards/proposalintake_standalone_form.html'


class DeleteProposalIntakeView(ProposalIntakeMixin, DeleteView):
    """Delete a ProposalIntake"""

    pk_url_kwarg = 'proposalintake_pk'


class EditSectionView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        AutosaveFormMixin,
        MoveToNextStepMixin,
        UpdateView):
    """Main class for section edit views"""

    pk_url_kwarg = 'award_pk'

    def get_object(self):

        pk = self.kwargs.get(self.pk_url_kwarg, None)
        try:
            award = Award.objects.get(pk=pk)
            if self.model in [AwardAcceptance, AwardNegotiation]:
                section_object = self.model.objects.get(
                    award=award,
                    current_modification=True)
            elif self.model == AwardSetup and award.common_modification or award.send_to_modification:
                section_object = AwardModification.objects.all().filter(award=award).order_by('-id')
                if section_object:
                    section_object = section_object[0]
                else:
                    section_object = self.model.objects.get(award=award)
            else:
                section_object = self.model.objects.get(award=award)
        except self.model.DoesNotExist:
            raise Http404(("No %(verbose_name)s found matching the query") %
                          {'verbose_name': self.model})

        self.award = award
        return section_object

    def get_form_kwargs(self):
        """Overrides parent get_form_kwargs function.
        If the current view is an active section, enable the move to next step functionality.
        """
        kwargs = super(EditSectionView, self).get_form_kwargs()
        dual_mode = False
        if self.award.status == 2 and self.model.__name__ == 'AwardSetup':
            dual_mode = True
        active_sections = self.award.get_active_sections(dual_mode)
        atp_query = AwardAcceptance.objects.filter(award_id=self.award.id)
        if self.model.__name__ in active_sections:
            kwargs['enable_send_to_next_step'] = True
        if self.model.__name__ == 'AwardAcceptance' and atp_query.count() > 1:
            kwargs['pta_modification_enable'] = True
        if self.model.__name__ == 'AwardAcceptance' and self.award.status == 1:
            kwargs['send_award_to_multiple_steps_steps'] = True
        if self.award.status == 2 and self.model.__name__ == 'AwardSetup' and self.award.award_dual_negotiation:
            kwargs['do_not_send_to_next_step'] = True
        if self.award.status == 2 and self.model.__name__ == 'AwardSetup' and self.award.award_dual_modification:
            kwargs['do_not_send_to_next_step'] = True
        if self.model.__name__ == 'AwardSetup' or self.model.__name__ == 'AwardModification':
            instance = kwargs.get('instance')
            data = kwargs.get('data')
            if data and instance:
                if instance.wait_for_reson == data.get('wait_for_reson'):
                    pass
                else:
                    self.award.record_wait_for_reason(instance.wait_for_reson, data.get('wait_for_reson'),
                                                      self.model.__name__)
                    instance.date_wait_for_updated = timezone.localtime(timezone.now())
                    instance.save()

        return kwargs

    def get_context_data(self, **kwargs):
        """Overrides parent get_context_data function.
        Adds the current view's associated model's name to the page context
        """

        context = super(EditSectionView, self).get_context_data(**kwargs)
        context['section'] = type(self.object).__name__
        return context


class ChildSectionMixin(object):
    """Main class for subsection (child section) views"""

    def get_success_url(self):
        """Get the URL to redirect to upon successful save"""

        return self.object.get_absolute_url()

    def get_parent_url(self):
        """Get the URL of this section's parent page"""

        if 'proposal_pk' in self.kwargs:
            return reverse(
                self.parent_edit_url,
                kwargs={
                    'award_pk': self.kwargs['award_pk'],
                    'proposal_pk': self.kwargs['proposal_pk']})
        else:
            return reverse(
                self.parent_edit_url,
                kwargs={
                    'award_pk': self.kwargs['award_pk']})

    def delete(self, request, *args, **kwargs):
        """Overrides parent delete function.
        Deletes the view's associated model object and redirects to the parent.
        """
        self.object = self.get_object()
        success_url = self.get_parent_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)

    def form_valid(self, form):
        """Provides custom validation on the associated form.
        Sets the associated Award or Proposal value, depending on which is appropriate.
        """
        child_object = form.save(commit=False)

        if 'proposal_pk' in self.kwargs:
            child_object.proposal = Proposal.objects.get(
                pk=self.kwargs['proposal_pk'])
        else:
            child_object.award = Award.objects.get(pk=self.kwargs['award_pk'])
            if self.form_class == PTANumberForm:
                child_object.is_edited=True
                child_object.pta_number_updated = datetime.now()
        child_object.save()

        self.object = child_object

        if form.cleaned_data['return_to_parent']:
            return HttpResponseRedirect(self.get_parent_url())
        else:
            return HttpResponseRedirect(self.get_success_url())


class ProposalIntakeView(EditSectionView):
    """Edit ProposalIntake"""

    model = ProposalIntake
    form_class = ProposalIntakeForm


class ProposalMixin(object):
    """Provides common functionality for all Proposal views"""

    model = Proposal
    form_class = ProposalForm

    def get_success_url(self):
        """Get the URL to redirect to upon successful save"""

        if self.request.is_ajax():
            return self.object.get_absolute_url()
        else:
            return reverse(
                'award_detail',
                kwargs={
                    'award_pk': self.kwargs['award_pk']})

    def form_valid(self, form):
        """Provides custom validation on the associated form."""

        # We exclude the award field from Proposal forms, but we need to set it
        # to do a valid save, so we set it manually after form validation
        proposal = form.save(commit=False)
        proposal.award = Award.objects.get(pk=self.kwargs['award_pk'])
        proposal.save()
        self.object = proposal

        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        """Overrides the parent get_context_data function to add extra data to the page context"""
        context = super(ProposalMixin, self).get_context_data(**kwargs)
        award = Award.objects.get(pk=self.kwargs['award_pk'])
        context['award'] = award
        context['editable_sections'] = award.get_editable_sections()
        context['section'] = Proposal.__name__

        if hasattr(self, 'disable_autosave'):
            context['disable_autosave'] = self.disable_autosave

        return context


class CreateProposalView(
        AutosaveFormMixin,
        AwardContextMixin,
        ProposalMixin,
        CreateView):
    """Create a new Proposal"""

    disable_autosave = True


class EditProposalView(
        AutosaveFormMixin,
        AwardContextMixin,
        ProposalMixin,
        UpdateView):
    """Edit an existing Proposal"""

    pk_url_kwarg = 'proposal_pk'


class DeleteProposalView(AwardContextMixin, ProposalMixin, DeleteView):
    """Delete a Proposal"""

    pk_url_kwarg = 'proposal_pk'


class CreateKeyPersonnelView(AwardContextMixin, ChildSectionMixin, CreateView):
    """Create new KeyPersonnel"""

    model = KeyPersonnel
    form_class = KeyPersonnelForm
    parent_edit_url = 'edit_proposal'
    disable_autosave = True


class EditKeyPersonnelView(
        AwardContextMixin,
        AutosaveFormMixin,
        ChildSectionMixin,
        UpdateView):
    """Edit existing KeyPersonnel"""

    model = KeyPersonnel
    form_class = KeyPersonnelForm
    parent_edit_url = 'edit_proposal'
    pk_url_kwarg = 'key_personnel_pk'


class DeleteKeyPersonnelView(AwardContextMixin, ChildSectionMixin, DeleteView):
    """Delete KeyPersonnel"""

    model = KeyPersonnel
    form_class = KeyPersonnelForm
    parent_edit_url = 'edit_proposal'
    pk_url_kwarg = 'key_personnel_pk'


class CreatePerformanceSiteView(
        AwardContextMixin,
        ChildSectionMixin,
        CreateView):
    """Create a new PerformanceSite"""

    model = PerformanceSite
    form_class = PerformanceSiteForm
    parent_edit_url = 'edit_proposal'
    disable_autosave = True


class EditPerformanceSiteView(
        AwardContextMixin,
        AutosaveFormMixin,
        ChildSectionMixin,
        UpdateView):
    """Edit an existing PerformanceSite"""

    model = PerformanceSite
    form_class = PerformanceSiteForm
    parent_edit_url = 'edit_proposal'
    pk_url_kwarg = 'performance_site_pk'


class DeletePerformanceSiteView(
        AwardContextMixin,
        ChildSectionMixin,
        DeleteView):
    """Delete a PerformanceSite"""

    model = PerformanceSite
    form_class = PerformanceSiteForm
    parent_edit_url = 'edit_proposal'
    pk_url_kwarg = 'performance_site_pk'


class AwardAcceptanceView(EditSectionView):
    """Edit AwardAcceptance"""

    model = AwardAcceptance
    form_class = AwardAcceptanceForm


class AwardNegotiationView(EditSectionView):
    """Edit AwardNegotiation"""

    model = AwardNegotiation
    form_class = AwardNegotiationForm

    def form_valid(self, form):
        """Provides custom validation for the associated form"""

        super(AwardNegotiationView, self).form_valid(form)

        # Mark the award as completed if the user chose that option
        award = Award.objects.get(pk=self.kwargs['award_pk'])

        if award and form.cleaned_data:
            negotiation_status = form.cleaned_data['negotiation_status']
            negotiation_status_user = self.request.user.get_full_name()
            negotiation_notes = form.cleaned_data['negotiation_notes']
            existing_negotiation_object = NegotiationStatus.objects.filter(award=award).order_by('-id')
            status_dict = NegotiationStatus.NEGOTIATION_CHOICES_DICT
            if negotiation_status:
                if not existing_negotiation_object:
                    if negotiation_status in status_dict:
                        negotiation_status = str(status_dict[negotiation_status])
                    negotiation_object = NegotiationStatus.objects.create(negotiation_status=negotiation_status,
                                                                          negotiation_notes=negotiation_notes,
                                                                          award=award,
                                                                          negotiation_status_changed_user=negotiation_status_user,
                                                                          negotiation_status_date=timezone.localtime(timezone.now()))
                    negotiation_object.save()
                elif existing_negotiation_object:
                    if existing_negotiation_object[0].negotiation_status != status_dict[negotiation_status]:
                        if negotiation_status in status_dict:
                            negotiation_status = str(status_dict[negotiation_status])
                        negotiation_object = NegotiationStatus.objects.create(negotiation_status=negotiation_status,
                                                                              negotiation_notes=negotiation_notes,
                                                                              award=award,
                                                                              negotiation_status_changed_user=negotiation_status_user,
                                                                              negotiation_status_date=timezone.localtime(
                                                                                  timezone.now()))
                        negotiation_object.save()

        if form.cleaned_data['close_award']:
            award.status = award.END_STATUS
            award.save()
            messages.info(
                    self.request,
                    'This award has been completed.')
            audit_trail = ATPAuditTrail.objects.filter(award=award.id,
                                                       workflow_step='AwardNegotiation').order_by('-id')
            if audit_trail:
                trail = audit_trail[0]
                trail.date_completed = timezone.localtime(timezone.now())
                trail.save()
            try:
                negotiation_object = AwardNegotiation.objects.get(award=award.id, current_modification=True)
                negotiation_object.negotiation_completion_date = timezone.localtime(timezone.now())
                negotiation_object.save()
            except AwardNegotiation.DoesNotExist:
                pass
        return HttpResponseRedirect(award.get_absolute_url())


class AwardSetupView(EditSectionView):
    """Edit AwardSetup"""

    model = AwardSetup
    form_class = AwardSetupForm


class CreatePTANumberView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        ChildSectionMixin,
        CreateView):
    """Create a new PTANumber"""

    model = PTANumber
    form_class = PTANumberForm
    parent_edit_url = 'edit_award_setup'
    disable_autosave = True

    def get_initial(self):
        """Gets the initial data used to populate some of the form fields"""

        award = Award.objects.get(pk=self.kwargs['award_pk'])
        proposal = award.get_most_recent_proposal()
        award_acceptance = award.get_current_award_acceptance()
        pta_number = award.get_first_pta_number()

        if not pta_number:
            pta_number = PTANumber()

        if not proposal:
            proposal = Proposal()

        return {'sponsor_award_number': award_acceptance.sponsor_award_number, 'eas_status': award_acceptance.eas_status,
                'agency_award_number': award_acceptance.agency_award_number, 'project_title': award_acceptance.project_title,
                'start_date': proposal.project_start_date, 'end_date': proposal.project_end_date,
                'department_name': proposal.department_name, 'principal_investigator': proposal.principal_investigator,
                'who_is_prime': proposal.who_is_prime, 'agency_name': proposal.agency_name,
                'preaward_date': pta_number.preaward_date, 'federal_negotiated_rate': pta_number.federal_negotiated_rate,
                'project_number': pta_number.project_number, 'parent_banner_number': pta_number.parent_banner_number,
                'sp_type': pta_number.sp_type, 'short_name': pta_number.short_name,
                'final_reports_due_date': pta_number.final_reports_due_date, 'allowed_cost_schedule': pta_number.allowed_cost_schedule
                }


class EditPTANumberView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        AutosaveFormMixin,
        ChildSectionMixin,
        UpdateView):
    """Edit an existing PTANumber"""

    model = PTANumber
    form_class = PTANumberForm
    parent_edit_url = 'edit_award_setup'
    pk_url_kwarg = 'pta_pk'


class DeletePTANumberView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        ChildSectionMixin,
        DeleteView):
    """Delete a PTANumber"""

    model = PTANumber
    form_class = PTANumberForm
    parent_edit_url = 'edit_award_setup'
    pk_url_kwarg = 'pta_pk'


class AwardSetupReportView(AwardContextMixin, TemplateView):
    """Display the award setup report"""

    template_name = 'awards/award_setup_report.html'


class SubawardView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        MoveToNextStepMixin,
        FormView):
    """Renders the list of Subawards"""

    # Not actually used by this view, but used by CheckEditPermissionsMixin
    model = Subaward
    template_name = 'awards/subaward_list.html'
    form_class = SubawardListForm

    def get_success_url(self):
        """Gets the URL to redirect to upon successful save"""

        return reverse(
            'edit_subawards',
            kwargs={
                'award_pk': self.kwargs['award_pk']})

    def get_form_kwargs(self):
        """Overrides the parent get_form_kwargs function.
        Adds the current Award object to the keyword arguments dictionary
        """

        kwargs = super(SubawardView, self).get_form_kwargs()
        kwargs['award'] = Award.objects.get(pk=self.kwargs['award_pk'])
        return kwargs

    def get_context_data(self, **kwargs):
        """Overrides the parent get_context_data function.
        Adds a value to tell the template we're in the Subaward section
        """

        context = super(SubawardView, self).get_context_data(**kwargs)
        context['section'] = 'Subaward'
        return context


class SubawardMixin(object):
    """Provides common functionality for all Subaward views"""

    model = Subaward
    form_class = SubawardForm

    def get_success_url(self):
        """Gets the URL to redirect to upon successful save"""

        if self.request.is_ajax():
            return self.object.get_absolute_url()
        else:
            return reverse(
                'edit_subawards',
                kwargs={
                    'award_pk': self.kwargs['award_pk']})

    def form_valid(self, form):
        """If the submitted form is valid, save the Subaward and then set its 
        award reference to be the Award that corresponds to the ID passed in
        from the page URL.
        """

        subaward = form.save(commit=False)
        subaward.award = Award.objects.get(pk=self.kwargs['award_pk'])
        subaward.save()
        self.object = subaward

        return HttpResponseRedirect(self.get_success_url())


class CreateSubawardView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        SubawardMixin,
        CreateView):
    """Create a new Subaward"""

    disable_autosave = True


class EditSubawardView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        AutosaveFormMixin,
        SubawardMixin,
        UpdateView):
    """Edit an existing Subaward"""

    pk_url_kwarg = 'subaward_pk'


class DeleteSubawardView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        SubawardMixin,
        DeleteView):
    """Delete a Subaward"""

    pk_url_kwarg = 'subaward_pk'


class AwardManagementView(EditSectionView):
    """Edit an existing AwardManagement"""

    model = AwardManagement
    form_class = AwardManagementForm


class CreatePriorApprovalView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        ChildSectionMixin,
        CreateView):
    """Create a new PriorApproval"""

    model = PriorApproval
    form_class = PriorApprovalForm
    parent_edit_url = 'edit_award_management'
    disable_autosave = True


class EditPriorApprovalView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        AutosaveFormMixin,
        ChildSectionMixin,
        UpdateView):
    """Edit an existing PriorApproval"""

    model = PriorApproval
    form_class = PriorApprovalForm
    parent_edit_url = 'edit_award_management'
    pk_url_kwarg = 'prior_approval_pk'


class DeletePriorApprovalView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        ChildSectionMixin,
        DeleteView):
    """Delete a PriorApproval"""

    model = PriorApproval
    form_class = PriorApprovalForm
    parent_edit_url = 'edit_award_management'
    pk_url_kwarg = 'prior_approval_pk'


class CreateReportSubmissionView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        ChildSectionMixin,
        CreateView):
    """Create a new ReportSubmission"""

    model = ReportSubmission
    form_class = ReportSubmissionForm
    parent_edit_url = 'edit_award_management'
    disable_autosave = True


class EditReportSubmissionView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        AutosaveFormMixin,
        ChildSectionMixin,
        UpdateView):
    """Edit an existing ReportSubmission"""

    model = ReportSubmission
    form_class = ReportSubmissionForm
    parent_edit_url = 'edit_award_management'
    pk_url_kwarg = 'report_submission_pk'


class DeleteReportSubmissionView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        ChildSectionMixin,
        DeleteView):
    """Delete a ReportSubmission"""

    model = ReportSubmission
    form_class = ReportSubmissionForm
    parent_edit_url = 'edit_award_management'
    pk_url_kwarg = 'report_submission_pk'


class AwardCloseoutView(EditSectionView):
    """Edit an existing AwardCloseout"""

    model = AwardCloseout
    form_class = AwardCloseoutForm


class CreateFinalReportView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        ChildSectionMixin,
        CreateView):
    """Create a new FinalReport"""

    model = FinalReport
    form_class = FinalReportForm
    parent_edit_url = 'edit_award_closeout'
    disable_autosave = True


class EditFinalReportView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        AutosaveFormMixin,
        ChildSectionMixin,
        UpdateView):
    """Edit an existing FinalReport"""

    model = FinalReport
    form_class = FinalReportForm
    parent_edit_url = 'edit_award_closeout'
    pk_url_kwarg = 'final_report_pk'


class DeleteFinalReportView(
        CheckEditPermissionsMixin,
        AwardContextMixin,
        ChildSectionMixin,
        DeleteView):
    """Delete a FinalReport"""

    model = FinalReport
    form_class = FinalReportForm
    parent_edit_url = 'edit_award_closeout'
    pk_url_kwarg = 'final_report_pk'


class ProposalStatisticsReportView(FormView):
    """Grabs data from Cayuse and returns a CSV file"""

    form_class = ProposalStatisticsReportForm
    template_name = 'awards/proposal_statistics_report.html'

    def form_valid(self, form):
        """If the submitted form is valid, generate the Proposal Statistics Report
        and add it to the response content as a CSV file.
        """

        from_date = form.cleaned_data['from_date']
        to_date = form.cleaned_data['to_date']
        all_fields = form.cleaned_data['show_all_fields']
        print all_fields

        header, proposals = get_proposal_statistics_report(from_date, to_date, all_fields)

        response = HttpResponse(content_type='text/csv')
        response[
            'Content-Disposition'] = 'attachment; filename="proposal_statistics_report_%s-%s.csv"' % (from_date, to_date)

        writer = csv.writer(response)
        writer.writerow(header)
        [writer.writerow(proposal) for proposal in proposals]

        return response


class AwardREAssaignmentView(FormView):
    """Grab all the awards from the atp awards table and re-assign to a selected user"""

    form_class = AwardREAssaignementForm
    template_name = 'awards/award_reassignment.html'

    def get_success_url(self):
        return reverse('award_re_assignment')

    def get_department_verified(self, awards, user_dept):
        assigns = []
        for assignment in awards:
            if assignment.proposal_set.get_queryset():
                propsal = assignment.proposal_set.get_queryset()[0]
                try:
                    if propsal.department_name == None:
                        assigns.append(assignment)
                    elif propsal.department_name.name == user_dept:
                        assigns.append(assignment)
                except:
                    pass

        return assigns

    def form_valid(self, form):
        atp_user = form.cleaned_data.get('atp_user')
        assignment_user = form.cleaned_data.get('assignment_user')
        user_department = form.cleaned_data.get('user_department')

        assignment_user = int(assignment_user)
        atp_user = int(atp_user)
        awards = Award.objects.all().filter(Q(Q(award_acceptance_user_id=atp_user) | Q(award_closeout_user_id=atp_user) |
                                             Q(award_management_user_id=atp_user) |
                                             Q(award_modification_user_id=atp_user) | Q(subaward_user_id=atp_user) |
                                             Q(award_negotiation_user_id=atp_user) | Q(award_setup_user_id=atp_user)) &
                                            Q(status__lt=6))
        if all([user_department, assignment_user, atp_user]):
            assigns = self.get_department_verified(awards, str(user_department))
        else:
            assigns = awards
        for award in assigns:
            if award.award_acceptance_user_id == atp_user:
                award.award_acceptance_user_id = assignment_user

            if award.award_closeout_user_id == atp_user:
                award.award_closeout_user_id = assignment_user

            if award.award_management_user_id == atp_user:
                award.award_management_user_id = assignment_user

            if award.award_modification_user_id == atp_user:
                award.award_modification_user_id = assignment_user

            if award.subaward_user_id == atp_user:
                award.subaward_user_id = assignment_user

            if award.award_negotiation_user_id == atp_user:
                award.award_negotiation_user_id = assignment_user

            if award.award_setup_user_id == atp_user:
                award.award_setup_user_id = assignment_user
            award.save()

        return HttpResponseRedirect(self.get_success_url())


def get_re_assignment_awards(request, atp_user):
    """This mentod is reponsible for getting all the assignments for a particular ATP user.
    It is an ajax call and atp user will come as input paramenter"""
    award_statuses = {1: 'Award Intake', 2: 'Award Negotiation', 3: 'Award Setup', 4: 'Subaward & Award Management',
                      5: 'Award Closeout'}
    if request.is_ajax() and atp_user:
        assigns = Award.objects.filter(Q(Q(award_acceptance_user_id=atp_user) | Q(award_closeout_user_id=atp_user) |
                                         Q(award_management_user_id=atp_user) |
                                         Q(award_modification_user_id=atp_user) | Q(subaward_user_id=atp_user) |
                                         Q(award_negotiation_user_id=atp_user) | Q(award_setup_user_id=atp_user)) &
                                       Q(status__lt=6))
        table_string = '<table id="award_re_assignment" class="table table-striped table-bordered">' \
                       '<thead><th>Award</th><th>Award Status</th></thead>'
        drop_string = '<option selected="selected" value="">---------</option>'
        department_names = []
        if assigns:
            for assignment in assigns:
                record = '<tr><td>%d</td><td>%s</td></tr>' % (assignment.id, award_statuses.get(assignment.status))
                table_string = table_string + record
                if assignment.proposal_set.get_queryset():
                    propsal = assignment.proposal_set.get_queryset()[0]
                    department_names.append(propsal.department_name)
            for dept in set(department_names):
                drop_string = drop_string + '<option value="%s">%s</option>' % (dept, dept)
            data = {'table_string': table_string,
                    'drop_string': drop_string}
            return HttpResponse(json.dumps(data), content_type="application/json")
        else:
            return HttpResponse('')


def get_department_awards(request, atp_user, user_dept):
    award_statuses = {1: 'Award Intake', 2: 'Award Negotiation', 3: 'Award Setup', 4: 'Subaward & Award Management',
                      5: 'Award Closeout'}

    if request.is_ajax() and atp_user and user_dept:
        assigns = Award.objects.filter(Q(Q(award_acceptance_user_id=atp_user) | Q(award_closeout_user_id=atp_user) |
                                         Q(award_management_user_id=atp_user) |
                                         Q(award_modification_user_id=atp_user) | Q(subaward_user_id=atp_user) |
                                         Q(award_negotiation_user_id=atp_user) | Q(award_setup_user_id=atp_user)) &
                                       Q(status__lt=6))
        table_string = '<table id="award_re_assignment" class="table table-striped table-bordered">' \
                       '<thead><th>Award</th><th>Award Status</th></thead>'
        if assigns:
            for assignment in assigns:
                if assignment.proposal_set.get_queryset():
                    propsal = assignment.proposal_set.get_queryset()[0]
                    try:
                        if propsal.department_name == None:
                            record = '<tr><td>%d</td><td>%s</td></tr>' % (
                                assignment.id, award_statuses.get(assignment.status))
                            table_string = table_string + record
                        elif propsal.department_name.name == user_dept:
                            record = '<tr><td>%d</td><td>%s</td></tr>' % (
                                assignment.id, award_statuses.get(assignment.status))
                            table_string = table_string + record
                    except:
                        pass

            data = {'table_string': table_string}
            return HttpResponse(json.dumps(data), content_type="application/json")
        else:
            return HttpResponse('')
