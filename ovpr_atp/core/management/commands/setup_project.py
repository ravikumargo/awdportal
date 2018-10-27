# Custom django-admin command for setting up default data in a new environment
#
# See Django documentation at https://docs.djangoproject.com/en/1.6/howto/custom-management-commands/

from django.core.management.base import BaseCommand

from core.setup import setup_project

class Command(BaseCommand):
    help = 'Initializes a blank database with some dummy data'

    def handle(self, *args, **options):
        """The 'main' method of this command.  Gets called by default when running the command."""
        
    	setup_project()
    	self.stdout.write('Project setup complete')