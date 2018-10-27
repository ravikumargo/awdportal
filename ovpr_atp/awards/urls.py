# Defines the URL routes within the /awards URL

from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from .views import (
    FullAwardSearchView,
    CreateProposalIntakeView,
    EditProposalIntakeView,
    DeleteProposalIntakeView,
    CreateKeyPersonnelView,
    EditKeyPersonnelView,
    DeleteKeyPersonnelView,
    CreatePerformanceSiteView,
    EditPerformanceSiteView,
    DeletePerformanceSiteView,
    CreateAwardView,
    CreateAwardStandaloneView,
    EditAwardView,
    ProposalIntakeView,
    AwardDetailView,
    CreateProposalView,
    EditProposalView,
    DeleteProposalView,
    AwardAcceptanceView,
    AwardNegotiationView,
    AwardSetupView,
    CreatePTANumberView,
    EditPTANumberView,
    DeletePTANumberView,
    AwardSetupReportView,
    SubawardView,
    CreateSubawardView,
    EditSubawardView,
    DeleteSubawardView,
    AwardManagementView,
    CreatePriorApprovalView,
    EditPriorApprovalView,
    DeletePriorApprovalView,
    CreateReportSubmissionView,
    EditReportSubmissionView,
    DeleteReportSubmissionView,
    AwardCloseoutView,
    CreateFinalReportView,
    EditFinalReportView,
    DeleteFinalReportView,
    ProposalStatisticsReportView,
    AwardREAssaignmentView)

urlpatterns = patterns('awards.views',
   url(r'^$', 'home', name='home'),
   url(r'^get-awards-ajax/$', 'get_awards_ajax', name='get_awards_ajax'),
   url(r'^award-redirect/(?P<award_pk>\d+)/$', 'redirect_to_award_details', name='redirect_to_award_details'),
   url(r'^award-re-assignment/$', login_required(AwardREAssaignmentView.as_view()), name='award_re_assignment'),
   url(r'^full-award-search/$', login_required(FullAwardSearchView.as_view()), name='full_award_search'),
   url(r'^get_re_assignment_awards/(?P<atp_user>\d+)/$', 'get_re_assignment_awards', name='get_re_assignment_awards'),
   url(r'^get_department_awards/(?P<atp_user>\d+)/(?P<user_dept>.*)/$', 'get_department_awards', name='get_department_awards'),
   url(r'^get-search-filter-ajax/(?P<field_name>.*)$', 'get_search_filter_ajax', name='get_search_filter_ajax'),
   url(r'^get-search-awards-ajax/$', 'get_search_awards_ajax', name='get_search_awards_ajax'),
   url(r'^get-search-subawards-ajax/$', 'get_search_subawards_ajax', name='get_search_subawards_ajax'),
   url(r'^get-search-pta-numbers-ajax/$', 'get_search_pta_numbers_ajax', name='get_search_pta_numbers_ajax'),

   url(r'^create-eas-mapping/(?P<interface>.*)/(?P<field>.*)/(?P<incoming_value>.*)/(?P<atp_model>.*)/$', 'create_eas_mapping', name='create_eas_mapping'),
   url(r'^import-eas-data/(?P<endpoint>.*)/$', 'import_eas_data', name='import_eas_data'),
   url(r'^audit-trail-activity/$', 'audittrail_activity_history', name='audittrail_activity_history'),
   url(r'^create-proposal-intake/$', login_required(CreateProposalIntakeView.as_view()), name='create_proposal_intake'),
   url(r'^edit-proposal-intake/(?P<proposalintake_pk>\d+)/$', login_required(EditProposalIntakeView.as_view()), name='edit_standalone_proposal_intake'),
   url(r'^delete-proposal-intake/(?P<proposalintake_pk>\d+)/$', login_required(DeleteProposalIntakeView.as_view()), name='delete_proposal_intake'),

   url(r'^create-award/(?P<proposalintake_pk>\d+)/$', login_required(CreateAwardView.as_view()), name='create_award'),
   url(r'^create-award/$', login_required(CreateAwardStandaloneView.as_view()), name='create_award_standalone'),
   url(r'^(?P<award_pk>\d+)/$', login_required(AwardDetailView.as_view()), name='award_detail'),
   url(r'^(?P<award_pk>\d+)/edit-award/$', login_required(EditAwardView.as_view()), name='edit_award'),

   url(r'^(?P<award_pk>\d+)/edit-proposal-intake/$', login_required(ProposalIntakeView.as_view()), name='edit_proposal_intake'),

   url(r'^(?P<award_pk>\d+)/pick-proposal/$', 'pick_proposal', name='pick_proposal'),
   url(r'^(?P<award_pk>\d+)/pick-lotus-proposal/$', 'pick_proposal', name='pick_lotus_proposal', kwargs={'lotus': True}),
   url(r'^(?P<award_pk>\d+)/get-lotus-proposals-ajax/$', 'get_lotus_proposals_ajax', name='get_lotus_proposals_ajax'),
   url(r'^(?P<award_pk>\d+)/import-proposal/(?P<proposal_id>\d+)/$', 'import_proposal', name='import_proposal'),
   url(r'^(?P<award_pk>\d+)/import-lotus-proposal/(?P<lotus_id>.*)/$', 'import_lotus_proposal', name='import_lotus_proposal'),
   url(r'^(?P<award_pk>\d+)/create-proposal/$', login_required(CreateProposalView.as_view()), name='create_proposal'),
   url(r'^(?P<award_pk>\d+)/edit-proposal/(?P<proposal_pk>\d+)/$', login_required(EditProposalView.as_view()), name='edit_proposal'),
   url(r'^(?P<award_pk>\d+)/delete-proposal/(?P<proposal_pk>\d+)/$', login_required(DeleteProposalView.as_view()), name='delete_proposal'),

   url(r'^(?P<award_pk>\d+)/add-key-personnel/(?P<proposal_pk>\d+)/$', login_required(CreateKeyPersonnelView.as_view()), name='add_key_personnel'),
   url(r'^(?P<award_pk>\d+)/edit-key-personnel/(?P<proposal_pk>\d+)/(?P<key_personnel_pk>\d+)/$', login_required(EditKeyPersonnelView.as_view()), name='edit_key_personnel'),
   url(r'^(?P<award_pk>\d+)/delete-key-personnel/(?P<proposal_pk>\d+)/(?P<key_personnel_pk>\d+)/$', login_required(DeleteKeyPersonnelView.as_view()), name='delete_key_personnel'),

   url(r'^(?P<award_pk>\d+)/add-performance-site/(?P<proposal_pk>\d+)/$', login_required(CreatePerformanceSiteView.as_view()), name='add_performance_site'),
   url(r'^(?P<award_pk>\d+)/edit-performance-site/(?P<proposal_pk>\d+)/(?P<performance_site_pk>\d+)/$', login_required(EditPerformanceSiteView.as_view()), name='edit_performance_site'),
   url(r'^(?P<award_pk>\d+)/delete-performance-site/(?P<proposal_pk>\d+)/(?P<performance_site_pk>\d+)/$', login_required(DeletePerformanceSiteView.as_view()), name='delete_performance_site'),

   url(r'^(?P<award_pk>\d+)/edit-award-intake/$', login_required(AwardAcceptanceView.as_view()), name='edit_award_acceptance'),
   url(r'^(?P<award_pk>\d+)/edit-award-negotiation/$', login_required(AwardNegotiationView.as_view()), name='edit_award_negotiation'),
   url(r'^(?P<award_pk>\d+)/create-modification/$', 'create_modification', name='create_modification'),

   url(r'^(?P<award_pk>\d+)/edit-award-setup/$', login_required(AwardSetupView.as_view()), name='edit_award_setup'),

   url(r'^(?P<award_pk>\d+)/add-pta-number/$', login_required(CreatePTANumberView.as_view()), name='add_pta_number'),
   url(r'^(?P<award_pk>\d+)/edit-pta-number/(?P<pta_pk>\d+)/$', login_required(EditPTANumberView.as_view()), name='edit_pta_number'),   
   url(r'^(?P<award_pk>\d+)/edit-pta-number/(?P<pta_pk>\d+)/get-award-number-ajax/$', 'get_award_number_ajax', name='get_award_number_ajax'),
   url(r'^(?P<award_pk>\d+)/delete-pta-number/(?P<pta_pk>\d+)/$', login_required(DeletePTANumberView.as_view()), name='delete_pta_number'),

   url(r'^(?P<award_pk>\d+)/award-setup-report/$', login_required(AwardSetupReportView.as_view()), name='award_setup_report'),

   url(r'^(?P<award_pk>\d+)/edit-subawards/$', login_required(SubawardView.as_view()), name='edit_subawards'),
   url(r'^(?P<award_pk>\d+)/add-subaward/$', login_required(CreateSubawardView.as_view()), name='add_subaward'),
   url(r'^(?P<award_pk>\d+)/edit-subaward/(?P<subaward_pk>\d+)/$', login_required(EditSubawardView.as_view()), name='edit_subaward'),
   url(r'^(?P<award_pk>\d+)/delete-subaward/(?P<subaward_pk>\d+)/$', login_required(DeleteSubawardView.as_view()), name='delete_subaward'),

   url(r'^(?P<award_pk>\d+)/edit-award-management/$', login_required(AwardManagementView.as_view()), name='edit_award_management'),

   url(r'^(?P<award_pk>\d+)/add-prior-approval/$', login_required(CreatePriorApprovalView.as_view()), name='add_prior_approval'),
   url(r'^(?P<award_pk>\d+)/edit-prior-approval/(?P<prior_approval_pk>\d+)/$', login_required(EditPriorApprovalView.as_view()), name='edit_prior_approval'),
   url(r'^(?P<award_pk>\d+)/delete-prior-approval/(?P<prior_approval_pk>\d+)/$', login_required(DeletePriorApprovalView.as_view()), name='delete_prior_approval'),

   url(r'^(?P<award_pk>\d+)/add-report-submission/$', login_required(CreateReportSubmissionView.as_view()), name='add_report_submission'),
   url(r'^(?P<award_pk>\d+)/edit-report-submission/(?P<report_submission_pk>\d+)/$', login_required(EditReportSubmissionView.as_view()), name='edit_report_submission'),
   url(r'^(?P<award_pk>\d+)/delete-report-submission/(?P<report_submission_pk>\d+)/$', login_required(DeleteReportSubmissionView.as_view()), name='delete_report_submission'),

   url(r'^(?P<award_pk>\d+)/edit-award-closeout/$', login_required(AwardCloseoutView.as_view()), name='edit_award_closeout'),

   url(r'^(?P<award_pk>\d+)/add-final-report/$', login_required(CreateFinalReportView.as_view()), name='add_final_report'),
   url(r'^(?P<award_pk>\d+)/edit-final-report/(?P<final_report_pk>\d+)/$', login_required(EditFinalReportView.as_view()), name='edit_final_report'),
   url(r'^(?P<award_pk>\d+)/delete-final-report/(?P<final_report_pk>\d+)/$', login_required(DeleteFinalReportView.as_view()), name='delete_final_report'),

   url(r'^get-proposal-statistics-report/$', login_required(ProposalStatisticsReportView.as_view()), name='get_proposal_statistics_report'),
   url(r'^get-cayuse-proposals/$', 'get_cayuse_proposals', name='get_cayuse_proposals'),

   )
