# Utility functions common to the project.

from django.conf import settings

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import ssl
import xml.etree.ElementTree as ET

class OracleAdapter(HTTPAdapter):
    """Very annoying custom adapter required to talk to EAS"""

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=ssl.PROTOCOL_TLSv1)

def make_eas_request(endpoint, parameters):
    """Generic function to send a SOAP request to EAS.  Contacts the provided endpoint
    and sends it the given parameters.
    """

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

    # Create a new requests Session with our custom adapter
    s = requests.Session()
    s.mount('https://', OracleAdapter())

    if settings.DEBUG:
        # Disable SSL verification if we're using SSH tunneling locally
        response = s.post(
            settings.EAS_URL,
            headers={
                'Content-Type': 'text/xml'},
            data=REQUEST_XML %
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
            data=REQUEST_XML %
            (endpoint,
             settings.EAS_PASSWORD,
             settings.EAS_NONCE,
             parameters))

    return ET.fromstring(response.content)