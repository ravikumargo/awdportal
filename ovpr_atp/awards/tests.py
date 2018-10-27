# Basic unit tests for the Awards pages
from django.test import TestCase
from django.test.client import Client
from django.http.request import QueryDict

from core.setup import setup_project
from .views import CreatePTANumberView, EditSectionView, home, AwardDetailView
from .models import *


class DatabaseTestCase(TestCase):
    def setUp(self):
        setup_project()

        self.c = Client()
        self.c.login(username='admin', password='password')

    def _create_award(self):
        self.c.post('/awards/create-award/', data={
            'award_acceptance_user': User.objects.filter(groups__name='Award Acceptance').first().id,
            'award_negotiation_user': User.objects.filter(groups__name='Award Negotiation').first().id,
            'award_setup_user': User.objects.filter(groups__name='Award Setup').first().id,
            'subaward_user': User.objects.filter(groups__name='Subaward Management').first().id,
            'award_management_user': User.objects.filter(groups__name='Award Management').first().id,
            'award_closeout_user': User.objects.filter(groups__name='Award Closeout').first().id,
        })

        return Award.objects.last()

    def test_home_page(self):
        # Act
        response = self.c.get('/', follow=True)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn('Create new award', response.content)

    def test_award_unicode(self):
        # Arrange
        award = self._create_award()

        # Assert
        self.assertEqual(str(award), 'Award #%s' % award.id)

    def test_award_detail(self):
        # Arrange
        award = self._create_award()

        # Act
        response = self.c.get(award.get_absolute_url())

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(award.id), response.content)

    def test_edit_award_section(self):
        # Arrange
        award = self._create_award()

        # Act
        response = self.c.get(award.get_current_award_acceptance().get_absolute_url())

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="section-form"', response.content)

    def test_fail_minimum_fields_check(self):
        # Arrange
        award = self._create_award()

        # Act
        response = self.c.post(award.get_current_award_acceptance().get_absolute_url(),
            data={'move_to_next_step': True})

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn('You must provide a value for Award Issue Date before you can send this award to the next step.',
            response.content)

    def test_pass_minimum_fields_check(self):
        # Arrange
        award = self._create_award()

        # Act
        response = self.c.post(award.get_current_award_acceptance().get_absolute_url(),
            data={'award_issue_date': '2014-01-01', 'move_to_next_step': True})

        # Assert
        self.assertEqual(response.status_code, 302)

        award = Award.objects.get(pk=award.id)
        self.assertEqual(award.status, 2)

    def test_modification_creation(self):
        # Arrange
        award = self._create_award()

        # Act
        response = self.c.post('/awards/%s/create-modification/' % award.id)

        # Assert
        self.assertIn(award.get_absolute_url(), response.url)

        self.assertIsInstance(award.get_current_award_acceptance(), AwardAcceptance)
        self.assertEqual(len(award.get_previous_award_acceptances()), 1)

        self.assertIsInstance(award.get_current_award_negotiation(), AwardNegotiation)
        self.assertEqual(len(award.get_previous_award_negotiations()), 1)


class CreatePTANumberViewTest(TestCase):
    def setUp(self):
        setup_project()

        self.c = Client()
        self.c.login(username='admin', password='password')

        self.kwargs = {}

    def _create_award(self):
        self.c.post('/awards/create-award/', data={
            'award_acceptance_user': User.objects.filter(groups__name='Award Acceptance').first().id,
            'award_negotiation_user': User.objects.filter(groups__name='Award Negotiation').first().id,
            'award_setup_user': User.objects.filter(groups__name='Award Setup').first().id,
            'subaward_user': User.objects.filter(groups__name='Subaward Management').first().id,
            'award_management_user': User.objects.filter(groups__name='Award Management').first().id,
            'award_closeout_user': User.objects.filter(groups__name='Award Closeout').first().id,
        })

        return Award.objects.last()

    def test_first_pta_number_with_get_initail_values(self):
        """
        This test case is to verify the get initial values form the first pta number.
        It returns dictionary of initial values which are auto populated in the 2nd, 3rd ...etc pta numbers.
        :return: returns dictionary of initial values.
        """
        award = self._create_award()
        create_pta = CreatePTANumberView()
        create_pta.kwargs = {'award_pk': award.id}
        pta_number = PTANumber.objects.create(award_id=award.id, project_number="Sample project", sp_type=1,
                                              short_name="Short award", parent_banner_number="Parent banner",
                                              preaward_date=datetime(2016, 04, 30), final_reports_due_date=datetime(2016, 04, 30))
        pta_number.save()
        response = create_pta.get_initial()
        _date = response['preaward_date']
        formater = '%Y-%m-%d'
        start_date = '%s-%s-%s' % (_date.year, _date.month, _date.day)
        preaward_date = datetime.strptime(start_date, formater)
        final_reports_due_date = datetime.strptime(start_date, formater)
        self.assertEqual(response['project_number'], pta_number.project_number)
        self.assertEqual(response['short_name'], pta_number.short_name)
        self.assertEqual(response['parent_banner_number'], pta_number.parent_banner_number)
        self.assertEqual(preaward_date, pta_number.preaward_date)
        self.assertEqual(final_reports_due_date, pta_number.final_reports_due_date)
        self.assertEqual(int(response['sp_type']), pta_number.sp_type)

    def test_first_pta_with_no_initial(self):
        """
        This test case is to verify the get initial values as empty when we create a first pta number.
        :return: returns dictionary of keys with values as empty.
        """
        expected_dict = {'who_is_prime': None, 'short_name': u'', 'project_title': u'', 'end_date': None,
                         'parent_banner_number': u'', 'principal_investigator': None, 'preaward_date': None,
                         'sp_type': u'', 'sponsor_award_number': u'', 'department_name': None,
                         'federal_negotiated_rate': None, 'agency_name': None, 'agency_award_number': u'',
                         'project_number': u'', 'eas_status': u'', 'final_reports_due_date': None, 'start_date': None,
                         'allowed_cost_schedule': None}
        award = self._create_award()
        create_pta = CreatePTANumberView()
        create_pta.kwargs = {'award_pk': award.id}
        response = create_pta.get_initial()
        self.assertDictEqual(expected_dict, response, "These two dicts must be equal")


class EditSectionViewTest(TestCase):

    def setUp(self):
        setup_project()

        self.c = Client()
        self.c.login(username='admin', password='password')

    def _create_award(self):
        self.c.post('/awards/create-award/', data={
            'award_acceptance_user': User.objects.filter(groups__name='Award Acceptance').first().id,
            'award_negotiation_user': User.objects.filter(groups__name='Award Negotiation').first().id,
            'award_setup_user': User.objects.filter(groups__name='Award Setup').first().id,
            'award_modification_user': User.objects.filter(groups__name='Award Modification').first().id,
            'subaward_user': User.objects.filter(groups__name='Subaward Management').first().id,
            'award_management_user': User.objects.filter(groups__name='Award Management').first().id,
            'award_closeout_user': User.objects.filter(groups__name='Award Closeout').first().id,
        })

        return Award.objects.last()

    def test_get_object(self):
        """ This test case is to verify the object when a award assign to modification."""
        award = self._create_award()
        _modifiction = AwardModification.objects.create(award=award, is_edited=False)
        _modifiction.save()
        self.c.user = award.award_modification_user

        section_view_object = EditSectionView()

        section_view_object.kwargs = {section_view_object.pk_url_kwarg: award.id}
        section_view_object.model = AwardSetup
        section_view_object.request = self.c
        award_modification = AwardModification.objects.get(award=award, is_edited=False)
        response = section_view_object.get_object()

        # Asserting the response with the award modification object.
        self.assertEqual(response, award_modification)

    def test_move_setup_or_modification_step(self):
        award = self._create_award()
        award.move_setup_or_modification_step(modification_flag=True)
        award_moidification = AwardModification.objects.filter(award=award)
        self.assertEqual(len(award_moidification), 1)

    def test_upcoming_proposals_filter(self):
        """ This test is for the upcoming proposal filter"""
        award = self._create_award()
        request = self.c
        dict = {'upcoming_proposals': 1}
        qdict = QueryDict('', mutable=True)
        qdict.update(dict)
        request.GET = qdict
        request.user = award.award_acceptance_user
        for i in range(2):
            intake = ProposalIntake.objects.create(proposal_due_to_sponsor=date.today())
            intake.save()
        intake = ProposalIntake.objects.create(proposal_due_to_sponsor=None)
        intake.save()
        home_obj = home(request)
        self.assertFalse('Proposal Intake 1' in home_obj.content)
        self.assertFalse('Proposal Intake 2' in home_obj.content)
        self.assertFalse('Proposal Intake 3' in home_obj.content)

    def test_all_proposals_filter(self):
        """ This test is for the all proposal filter"""
        award = self._create_award()
        request = self.c
        dict = {'all_proposals': 1}
        qdict = QueryDict('', mutable=True)
        qdict.update(dict)
        request.GET = qdict
        request.user = award.award_acceptance_user
        for i in range(2):
            intake = ProposalIntake.objects.create(proposal_due_to_sponsor=date.today())
            intake.save()
        intake = ProposalIntake.objects.create(proposal_due_to_sponsor=None)
        intake.save()
        home_obj = home(request)
        self.assertTrue('Proposal Intake 1' in home_obj.content)
        self.assertTrue('Proposal Intake 2' in home_obj.content)
        self.assertTrue('Proposal Intake 3' in home_obj.content)

    def test_editable_sections_in_dual_model(self):
        """ This is to test when multiple teams working on same award. Multiple steps must be editable. """
        award = self._create_award()
        award.award_dual_setup = True
        award.award_dual_negotiation = True
        award.status = 2
        award.save()
        response = award.get_editable_sections()
        self.assertTrue('AwardNegotiation', 'AwardSetup' in response)

    def test_get_active_sections(self):
        """ This test case is to identify the active sections when multiple teams are working parallel. """
        award = self._create_award()
        expected_response = ['AwardNegotiation', 'AwardSetup']
        dual_mode = True
        response = award.get_active_sections(dual_mode)
        self.assertEqual(expected_response, response)

    def test_get_context_data(self):
        """
         This test case is to validate the context data when mupltiple teams working on same award parallel.
        """
        award = self._create_award()
        award.status = 2
        award.award_dual_negotiation = True
        award.award_dual_setup = True
        award.save()
        expected_result = ['ProposalIntake', 'AwardNegotiation', 'AwardAcceptance', 'AwardModification', 'AwardSetup']
        view = AwardDetailView()
        view.object = award
        context_data = view.get_context_data()
        self.assertEqual(expected_result, context_data['editable_sections'])
