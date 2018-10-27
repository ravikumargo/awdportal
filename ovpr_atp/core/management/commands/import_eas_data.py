# Custom django-admin command for getting data from EAS.
#
# Can be run manually or via a scheduled job.
#
# See Django documentation at https://docs.djangoproject.com/en/1.6/howto/custom-management-commands/

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models

from optparse import make_option
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from datetime import datetime, timedelta
import ssl
import xml.etree.ElementTree as ET

from awards.models import PrimeSponsor, AllowedCostSchedule, AwardManager, AwardOrganization, AwardTemplate, CFDANumber, FedNegRate, FundingSource, IndirectCost


class OracleAdapter(HTTPAdapter):
    """Very annoying custom adapter required to talk to EAS"""

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=ssl.PROTOCOL_TLSv1)


class Command(BaseCommand):
    help = 'Imports latest EAS data'
    option_list = BaseCommand.option_list + (
        make_option(
            '--complete',
            action='store_true',
            dest='complete',
            default=False,
            help='Queries Award Manager year-by-year to get complete dataset'),
        make_option(
            '--from',
            dest='from',
            default=None,
            help='Sets a start date to use when querying Award Manager'),
        make_option(
            '--to',
            dest='to',
            default=None,
            help='Sets an end date to use when querying Award Manager')
    )

    # The valid XML request necessary to invoke the EAS SOAP interface. 
    # Generated using SoapUI (http://www.soapui.org/)
    REQUEST_XML = '''<soapenv:Envelope xmlns:get="http://xmlns.oracle.com/apps/gms/soaprovider/plsql/gwu_gms_atp_pub/%s/" xmlns:gwu="http://xmlns.oracle.com/apps/gms/soaprovider/plsql/gwu_gms_atp_pub/" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
   <soapenv:Header>
      <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
         <wsse:UsernameToken wsu:Id="UsernameToken-13A8CEB13B8B04DC3C14058080562144">
            <wsse:Username>GWATWS</wsse:Username>
            <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">%s</wsse:Password>
            <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">%s</wsse:Nonce>
            <wsu:Created>2014-07-19T22:14:16.214Z</wsu:Created>
         </wsse:UsernameToken>
      </wsse:Security>
      <gwu:SOAHeader>
         <!--Optional:-->
         <gwu:Responsibility>GW BANNER TO EAS MAPPING</gwu:Responsibility>
         <!--Optional:-->
         <gwu:RespApplication>GWU</gwu:RespApplication>
         <!--Optional:-->
         <gwu:SecurityGroup>STANDARD</gwu:SecurityGroup>
         <!--Optional:-->
         <gwu:NLSLanguage>AMERICAN</gwu:NLSLanguage>
         <!--Optional:-->
         <gwu:Org_Id>0</gwu:Org_Id>
      </gwu:SOAHeader>
   </soapenv:Header>
   <soapenv:Body>
      %s
   </soapenv:Body>
</soapenv:Envelope>'''

    BASE_PARAMETERS = '<get:InputParameters/>'

    DATE_RANGE_PARAMETERS = '''<get:InputParameters>
         <!--Optional:-->
         <get:P_FROM_DATE>%s</get:P_FROM_DATE>
         <!--Optional:-->
         <get:P_TO_DATE>%s</get:P_TO_DATE>
      </get:InputParameters>'''

    # List of EAS endpoints
    ENDPOINTS = {
        'get_allow_schedule': AllowedCostSchedule,
        'get_award_manager': AwardManager,
        'get_award_organization': AwardOrganization,
        'get_award_template': AwardTemplate,
        'get_cfda_number': CFDANumber,
        'get_fedneg_rate': FedNegRate,
        'get_fund_sources': FundingSource,
        'get_indirect_cost': IndirectCost,
        'get_prime_sponsor': PrimeSponsor,
    }

    def _import_eas_field(self, endpoint, model, from_date=None, to_date=None):
        """Makes the call to the given EAS endpoint, parses the XML response, and saves the
        data into the appropriate models.
        """

        # AwardManager EAS requests require date ranges
        if endpoint == 'get_award_manager':
            if not from_date:
                from_date = datetime.now() - timedelta(weeks=1)

            if not to_date:
                to_date = datetime.now()

            parameters = self.DATE_RANGE_PARAMETERS % (
                from_date.strftime('%Y-%m-%d'), to_date.strftime('%Y-%m-%d'))
        else:
            parameters = self.BASE_PARAMETERS

        # Create a new requests Session with our custom adapter
        s = requests.Session()
        s.mount('https://', OracleAdapter())

        if settings.DEBUG:
            # Disable SSL verification if we're using SSH tunneling locally
            response = s.post(
                settings.EAS_URL,
                headers={
                    'Content-Type': 'text/xml'},
                data=self.REQUEST_XML %
                (endpoint,
                 settings.EAS_PASSWORD,
                 settings.EAS_NONCE,
                 parameters),
                verify=False)
        else:
            # Submit the SOAP request
            response = s.post(
                settings.EAS_URL,
                headers={
                    'Content-Type': 'text/xml'},
                data=self.REQUEST_XML %
                (endpoint,
                 settings.EAS_PASSWORD,
                 settings.EAS_NONCE,
                 parameters))

        # Parse the result
        root = ET.fromstring(response.content)

        items = root[1][0][3]

        import_counter = 0
        for item in items:
            eas_object = model()
            field_counter = 0
            # To avoid full XML parsing, we instead determine which field a value
            # corresponds to by the order it appears in the response.
            # This is set in the EAS_FIELD_ORDER property of the model itself
            for field in model.EAS_FIELD_ORDER:
                value = item[field_counter].text

                # Do some casting based on what type the ATP field is
                if isinstance(
                        model._meta.get_field(field),
                        models.BooleanField):
                    if value == 'Y':
                        value = True
                    else:
                        value = False
                elif isinstance(model._meta.get_field(field), models.DateField) and value is not None:
                    if model in (
                            AwardManager,
                            AwardOrganization,
                            CFDANumber,
                            FedNegRate,
                            FundingSource,
                            IndirectCost):
                        value = datetime.date(datetime.strptime(value.split('T')[0],'%Y-%m-%d'))
                    else:
                        value = datetime.date(datetime.strptime(value, '%d-%b-%Y'))

                setattr(
                    eas_object,
                    model.EAS_FIELD_ORDER[field_counter],
                    value)
                field_counter += 1

            eas_object.save()

            import_counter += 1
            if import_counter % 100 == 0:
                self.stdout.write('%s objects processed' % import_counter)

        return import_counter

    def _import_all_award_manager(self):
        """Special method to import a complete set of AwardManagers. Used during go-live."""

        START_DATE = datetime(
            2004,
            01,
            01,
            00,
            00)  # The oldest records in EAS seem to start in 2006
        TODAY = datetime.now()

        from_date = to_date = START_DATE
        while to_date < TODAY:
            to_date = from_date + timedelta(days=365)
            self.stdout.write(
                'Importing Award Manager updates from %s - %s' %
                (from_date, to_date))
            objects_imported = self._import_eas_field(
                'get_award_manager',
                AwardManager,
                from_date,
                to_date)
            self.stdout.write('%s objects processed' % objects_imported)
            from_date = to_date

    def handle(self, *args, **options):
        """The 'main' method of this command.  Gets called by default when running the command."""

        # If there aren't any arguments, assume all endpoints should be imported
        if len(args) == 0:
            endpoints = self.ENDPOINTS.keys()
            self.stdout.write('Importing all endpoints')
        else:
            endpoints = args

        for endpoint in endpoints:
            model = self.ENDPOINTS[endpoint]

            self.stdout.write('Beginning %s import' % model.__name__)

            if model == AwardManager and options['complete']:
                self._import_all_award_manager()
                self.stdout.write('Award Manager import complete')
            else:
                from_date = None
                if options['from']:
                    from_date = datetime.strptime(options['from'], '%Y-%m-%d')
                
                to_date = None
                if options['to']:
                    to_date = datetime.strptime(options['to'], '%Y-%m-%d')

                objects_imported = self._import_eas_field(endpoint, model, from_date, to_date)
                self.stdout.write(
                    '%s import complete - %s objects processed' %
                    (model.__name__, objects_imported))

        self.stdout.write('EAS import complete')
