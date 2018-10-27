# Custom django-admin command for importing data from Lotus Notes.
#
# Reads a CSV file exported from Lotus and inputs the data.  Was used when
# first going live with the project.
#
# See Django documentation at https://docs.djangoproject.com/en/1.6/howto/custom-management-commands/

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from datetime import datetime, timedelta
from os.path import join

from awards.models import Award, Proposal, AwardAcceptance

import csv

AP_LOG_FILENAME = 'AP-Log.csv'
AP_SPECS_FILENAME = 'AP-SPECS.csv'
COMPLYTRAK_FILENAME = 'COMPLYTRAK.csv'

LOTUS_FIELD_MAPPING = {
    'G_OR_C,C,20': {'model': 'Proposal', 'field': 'proposal_type', 'field_type': 'char'},
    'TITLE_LONG,C,254': {'model': 'Proposal', 'field': 'project_title', 'field_type': 'char'},
    'DEPT_CODE,C,15': {'model': 'Proposal', 'field': 'lotus_department_code', 'field_type': 'char'},
    'SPONSOR,C,50': {'model': 'Proposal', 'field': 'lotus_agency_name', 'field_type': 'char'},
    'PER_START,D': {'model': 'Proposal', 'field': 'project_start_date', 'field_type': 'date'},
    'PER_END,D': {'model': 'Proposal', 'field': 'project_end_date', 'field_type': 'date'},
    'SUBMITTED,D': {'model': 'Proposal', 'field': 'sponsor_deadline', 'field_type': 'date'},
    'SPON_TYPE,C,10': {'model': 'Proposal', 'field': 'agency_type', 'field_type': 'char'},
    'AP_TYPE,C,10': {'model': 'Proposal', 'field': 'application_type_code', 'field_type': 'char'},
    'PROJ_TYPE,C,25': {'model': 'Proposal', 'field': 'project_type', 'field_type': 'char'},
    'IRBNO,C,10': {'model': 'Proposal', 'field': 'irb_protocol_number', 'field_type': 'char'},
    'PER_START,D': {'model': 'Proposal', 'field': 'budget_first_per_start_date', 'field_type': 'date'},
    'PER_END,D': {'model': 'Proposal', 'field': 'budget_first_per_end_date', 'field_type': 'date'},
    'DC_PROJ,N,13,2': {'model': 'Proposal', 'field': 'total_direct_costs', 'field_type': 'decimal'},
    'DC_PERIOD,N,13,2': {'model': 'Proposal', 'field': 'total_direct_costs_y1', 'field_type': 'decimal'},
    'IDC_PROJ,N,13,2': {'model': 'Proposal', 'field': 'total_indirect_costs', 'field_type': 'decimal'},
    'IDC_PERIOD,N,13,2': {'model': 'Proposal', 'field': 'total_indirect_costs_y1', 'field_type': 'decimal'},
    'COMMENTS,C,215': {'model': 'Proposal', 'field': 'comments', 'field_type': 'char'},
    'GWID,C,20': {'model': 'Proposal', 'field': 'employee_id', 'field_type': 'char'},
    'AP_ID,C,15': {'model': 'Proposal', 'field': 'lotus_id', 'field_type': 'char'},
}

class Command(BaseCommand):
    args = '[export directory]'
    help = 'Imports Lotus Notes data into ATP'

    def process_file(self, directory, filename):
        """Read the given CSV file and pull out only the data we need"""

        f = open(join(directory, filename), 'rb')
        reader = csv.reader(f)

        header = reader.next()

        tracker = {}

        for row in reader:
            entry = dict(zip(header, row))
            if entry['AP_ID,C,15']:
                tracker[entry['AP_ID,C,15']] = entry

        f.close()

        return tracker

    def handle(self, *args, **options):
        """The 'main' method of this command.  Gets called by default when running the command."""

        csv_directory = args[0]
        
        ap_log = self.process_file(csv_directory, AP_LOG_FILENAME)
        ap_specs = self.process_file(csv_directory, AP_SPECS_FILENAME)
        complytrak = self.process_file(csv_directory, COMPLYTRAK_FILENAME)

        # Combine them
        for key in ap_log.keys():
            if key in ap_specs:
                ap_log[key].update(ap_specs[key])
            if key in complytrak:
                ap_log[key].update(complytrak[key])

        import_counter = 0
        for key in ap_log.keys():
            # Skip if this proposal has been imported already
            try:
                Proposal.objects.get(lotus_id=key)
                self.stdout.write('Skipping import for %s' % key)
                continue
            except Proposal.DoesNotExist:
                pass

            record = ap_log[key]

            # Don't import records that aren't proposals or awards
            if record['OUTCOME,C,10'] not in ('P', 'A'):
                continue

            # Don't import records from earlier than June 2009
            if 'OUT_DATE,D' in record:
                if record['OUT_DATE,D'] == '':
                    continue
                elif datetime.strptime(record['OUT_DATE,D'], "%m/%d/%y") < datetime(2009, 06, 01, 00, 00):
                    continue

            proposal_values = {}

            for import_field in LOTUS_FIELD_MAPPING.keys():
                mapping_entry = LOTUS_FIELD_MAPPING[import_field]
                if import_field in record:
                    field_data = record[import_field]
                    if mapping_entry['field_type'] in ['date', 'decimal'] and not field_data:
                        field_data = None
                    elif mapping_entry['field_type'] == 'date':
                        field_data = datetime.strptime(field_data, "%m/%d/%y")

                    if mapping_entry['model'] == 'Proposal':
                        proposal_values[mapping_entry['field']] = field_data

            proposal = Proposal(**proposal_values)
            proposal.lotus_id = key
            proposal.save()

            self.stdout.write('Successfully created "%s"' % proposal)
            import_counter+=1

        self.stdout.write('Import complete. %s proposals imported.' % import_counter)
