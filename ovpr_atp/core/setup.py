# Defines functions necessary to set up a new environment.
# Called from the setup_project management command

from django.contrib.auth.models import User, Group
from awards.models import (Proposal, Award,
                           AwardNegotiation,
                           AwardSetup, Subaward,
                           AwardManagement, AwardCloseout)
from datetime import date


def create_groups():
    """Create the necessary authorization groups for rights management within the site"""

    Group.objects.get_or_create(name='Proposal Intake')
    Group.objects.get_or_create(name='Administrative')
    Group.objects.get_or_create(name='Award Acceptance')
    Group.objects.get_or_create(name='Award Negotiation')
    Group.objects.get_or_create(name='Award Setup')
    Group.objects.get_or_create(name='Award Modification')
    Group.objects.get_or_create(name='Award Management')
    Group.objects.get_or_create(name='Subaward Management')
    Group.objects.get_or_create(name='Award Closeout')


def create_dummy_proposals():
    """Create some dummy users and Proposal data for use in a new development environment"""

    # Delete all Department objects to cascade deletes via
    # ForeignKey relationship up to PI and Award objects
    User.objects.all().delete()

    user_0 = User.objects.create_user(
        username='jack.cooper',
        password='password',
        first_name='Jack',
        last_name='Cooper',
        email='fake@email.com',
    )
    user_1 = User.objects.create_user(
        username='john.young',
        password='password',
        first_name='John',
        last_name='Young',
        email='fake@email.com',
    )
    user_2 = User.objects.create_user(
        username='jill.smith',
        password='password',
        first_name='Jill',
        last_name='Smith',
        email='fake@email.com',
    )
    user_3 = User.objects.create_user(
        username='dave.garber',
        password='password',
        first_name='Dave',
        last_name='Garber',
        email='fake@email.com',
    )
    user_4 = User.objects.create_user(
        username='fiona.gallagher',
        password='password',
        first_name='Fiona',
        last_name='Gallagher',
        email='fake@email.com',
    )
    user_5 = User.objects.create_user(
        username='maxine.cogar',
        password='password',
        first_name='Maxine',
        last_name='Cogar',
        email='fake@email.com',
    )
    user_6 = User.objects.create_user(
        username='andrew.baker',
        password='password',
        first_name='Andrew',
        last_name='Baker',
        email='fake@email.com',
    )
    user_7 = User.objects.create_user(
        username='jane.doe',
        password='password',
        first_name='Jane',
        last_name='Doe',
        email='fake@email.com',
    )
    user_8 = User.objects.create_user(
        username='allison.mcgee',
        password='password',
        first_name='Allison',
        last_name='McGee',
        email='fake@email.com',
    )
    user_9 = User.objects.create_user(
        username='elizabeth.garber',
        password='password',
        first_name='Elizabeth',
        last_name='Garber',
        email='fake@email.com',
    )
    user_10 = User.objects.create_user(
        username='jesus.hernandez',
        password='password',
        first_name='Jesus',
        last_name='Hernandez',
        email='fake@email.com',
    )

    user_11 = User.objects.create_superuser(
        username='admin',
        password='password',
        first_name='ATP',
        last_name='Admin',
        email='atp_admin@email.gwu.edu',
    )

    user_12 = User.objects.create_user(
        username='paul.rk',
        password='password',
        first_name='Paul',
        last_name='Rk',
        email='fake@email.com',
    )

    group_0 = Group.objects.get(name='Proposal Intake')
    group_1 = Group.objects.get(name='Administrative')
    group_2a = Group.objects.get(name='Award Acceptance')
    group_2b = Group.objects.get(name='Award Negotiation')
    group_3a = Group.objects.get(name='Award Setup')
    group_3b = Group.objects.get(name='Award Modification')
    group_4 = Group.objects.get(name='Award Management')
    group_5 = Group.objects.get(name='Subaward Management')
    group_6 = Group.objects.get(name='Award Closeout')

    group_0.user_set.add(user_0)
    group_1.user_set.add(user_1)
    group_2a.user_set.add(user_2)
    group_3a.user_set.add(user_3)
    group_3b.user_set.add(user_12)
    group_4.user_set.add(user_4)
    group_5.user_set.add(user_5)
    group_6.user_set.add(user_6)
    group_2b.user_set.add(user_7)
    group_3a.user_set.add(user_8)
    group_4.user_set.add(user_9)
    group_5.user_set.add(user_10)

    Award.objects.create(
        status=2,
        award_acceptance_user=user_2,
        award_setup_user=user_3,
        award_management_user=user_4,
        award_closeout_user=user_6
    )

    Award.objects.create(
        status=4,
        award_acceptance_user=user_2,
        award_setup_user=user_3,
        award_management_user=user_4,
        award_closeout_user=user_6
    )


def create_production_users():
    admin = User.objects.create_superuser(
        username='admin',
        password='password',
        first_name='ATP',
        last_name='Admin',
        email='atp_admin@email.gwu.edu',
    )

    service = User.objects.create_superuser(
        username='DIT-SVC-BACMON',
        password='password',
        first_name='DIT',
        last_name='Service',
        email='reply@email.gwu.edu'
    )


def setup_project():
    """Setup dummy data for a new development environment"""

    create_groups()
    create_dummy_proposals()


def setup_production():
    """Setup initial data for the production environment"""

    create_groups()
    create_production_users()
