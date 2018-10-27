# Registers models within the Django Admin functionality
#
# See related Django documentation at https://docs.djangoproject.com/en/1.6/ref/contrib/admin/
from django.contrib import admin, messages
from .models import ProposalIntake, Proposal, KeyPersonnel, PerformanceSite, Award, AwardAcceptance, AwardNegotiation, \
    AwardSetup,Subaward, PTANumber, AwardManagement, PriorApproval, ReportSubmission, AwardCloseout, FinalReport, \
    PrimeSponsor, AllowedCostSchedule, AwardManager, AwardOrganization, AwardTemplate, \
    CFDANumber, FedNegRate, FundingSource, IndirectCost, EASMapping, NegotiationStatus

import reversion


# NOTE: These admins inherit from reversion.VersionAdmin to register these models
# with django-reversion

class AwardAdmin(reversion.VersionAdmin):
    """Special admin class for Awards"""

    list_display = ('__str__',
                    'status',
                    'proposalintake_admin',
                    'proposal_admin',
                    'awardacceptance_admin',
                    'awardnegotiation_admin',
                    'awardsetup_admin',
                    'subaward_admin',
                    'awardmanagement_admin',
                    'awardcloseout_admin',
                    )

    def save_model(self, request, obj, form, change):
        try:
            old_object = Award.objects.get(id=obj.id)
        except:
            old_object = None
        if old_object:
            if obj.send_to_modification != old_object.send_to_modification:
                if old_object.send_to_modification == True and obj.send_to_modification == False:
                    messages.warning(request, "send_to_modification flag 'Un Checked' for the Award #%d, "
                                              "do you need this change?" %obj.id)
                if old_object.send_to_modification == False and obj.send_to_modification == True:
                    messages.warning(request, "send_to_modification flag 'Checked' for the Award #%d, "
                                              "do you need this change?" % obj.id)
                obj.save()
            if obj.status != old_object.status:
                obj.save()
                obj.send_email_update()
            elif obj.status == 1 and obj.award_acceptance_user != old_object.award_acceptance_user:
                obj.save()
                obj.send_email_update()
            elif obj.status == 2 and obj.award_negotiation_user != old_object.award_negotiation_user:
                obj.save()
                obj.send_email_update()
            elif obj.status == 4 and obj.award_management_user != old_object.award_management_user:
                obj.save()
                obj.send_email_update()
            elif obj.status == 5 and obj.award_closeout_user != old_object.award_closeout_user:
                obj.save()
                obj.send_email_update()

            if obj.status == 3 and obj.send_to_modification:
                if obj.award_setup_user != old_object.award_setup_user:
                    obj.save()
                elif obj.award_modification_user != old_object.award_modification_user:
                    obj.save()
                    obj.send_email_update(modification_flag=True)
            else:
                if obj.award_setup_user != old_object.award_setup_user:
                    obj.save()
                    obj.send_email_update()
                elif obj.award_modification_user != old_object.award_modification_user:
                    obj.save()
        else:
            super(AwardAdmin, self).save_model(request, obj, form, change)

class SectionAdmin(reversion.VersionAdmin):
    """Main admin class for sections"""
    raw_id_fields = ('award',)


class AwardForeignKeyAdmin(SectionAdmin):
    """Generic admin class for award sections that contain a foreign key
    to Award, rather than a 1-1 relationship
    """
    pass


class GenericAdmin(reversion.VersionAdmin):
    """Generic admin class for versioned models"""
    pass

admin.site.register(Award, AwardAdmin)

admin.site.register(ProposalIntake, SectionAdmin)

admin.site.register(Proposal, AwardForeignKeyAdmin)
admin.site.register(KeyPersonnel, GenericAdmin)
admin.site.register(PerformanceSite, GenericAdmin)

admin.site.register(AwardAcceptance, AwardForeignKeyAdmin)
admin.site.register(AwardNegotiation, AwardForeignKeyAdmin)
admin.site.register(AwardSetup, SectionAdmin)
admin.site.register(PTANumber, SectionAdmin)
admin.site.register(Subaward, AwardForeignKeyAdmin)
admin.site.register(AwardManagement, SectionAdmin)
admin.site.register(PriorApproval, SectionAdmin)
admin.site.register(ReportSubmission, SectionAdmin)
admin.site.register(AwardCloseout, SectionAdmin)
admin.site.register(FinalReport, SectionAdmin)
admin.site.register(NegotiationStatus, AwardForeignKeyAdmin)


class NonVersionedAdmin(admin.ModelAdmin):
    """Generic admin class for non-versioned models"""
    pass


class FundingSourceAdmin(admin.ModelAdmin):
    """Special admin class for FundingSource"""
    search_fields = ['name', 'number']


class AwardManagerAdmin(admin.ModelAdmin):
    """Special admin class for AwardManager"""
    search_fields = ['gwid', 'full_name']

admin.site.register(AllowedCostSchedule, NonVersionedAdmin)
admin.site.register(AwardManager, AwardManagerAdmin)
admin.site.register(AwardOrganization, NonVersionedAdmin)
admin.site.register(AwardTemplate, NonVersionedAdmin)
admin.site.register(CFDANumber, NonVersionedAdmin)
admin.site.register(FedNegRate, NonVersionedAdmin)
admin.site.register(FundingSource, FundingSourceAdmin)
admin.site.register(IndirectCost, NonVersionedAdmin)
admin.site.register(PrimeSponsor, NonVersionedAdmin)

admin.site.register(EASMapping, NonVersionedAdmin)
