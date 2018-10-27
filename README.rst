================================
OVPR Award Tracking Portal (ATP)
================================

This README is intended to orient new developers to the ATP project. It includes a brief functional overview of ATP, a description of ATP's technical architecture, and some practical advice for performing certain enhancements to ATP.

This is a `Django <https://www.djangoproject.com/>`_ application that was developed by Andrew Baker. It was influenced significantly by the best practices outlined in `Two Scoops of Django <http://www.amazon.com/Two-Scoops-Django-Best-Practices/dp/098146730X>`_. 

It makes heavy use of Django's class-based views - you should read the `official documentation <https://docs.djangoproject.com/en/1.5/topics/class-based-views/intro/>`_ about class based views before working on ATP's views. You should also reference classy `Classy Class-Based Views <http://ccbv.co.uk/projects/Django/1.6/>`_ liberally.

Functional Overview
-------------------

ATP was built to help GW's Office of the Vice President of Research (OVPR) administer research grants that the university has been awarded. ATP is essentially a workflow tool, helping administrators manage their workload and keeping all information related to an award in a central tool.

The main object in ATP is an **award**. An award has many sections, each of which is assigned to a user and completed in sequence until the award is complete. This is a slow process - it is not uncommon for awards to be active for many years.

The award sections are as follows:

- **Proposal Intake:** This section is actually completed before a proposal is submitted for a research project (long before an award is made). 
    - OVPR uses it to plan their proposal work. If a Proposal Intake section eventually turns into an award, users can create an award from the Proposal Intake object and reference it in the award detail screen. 
    - An award has zero or one Proposal Intake entries.
- **Proposal:** This section represents the proposal that was submitted for (and won) the award. 
    - It is either imported from Cayuse (a third party tool), GW's legacy Lotus Notes data, or manually via a blank record.
    - An award can have zero or many proposals associated with it. Additional proposals are called "supplemental proposals.""
- **Award Intake (/ Award Acceptance):** This section is the first section users fill out when OVPR receives an award.
    - It has an assigned user, selected at award creation
    - It is called "Award Intake" on the front-end, but "Award Acceptance" on the backend. This is the result of a UI change requested late in development.
    - An award can have one or many Award Intake sections. Additional Award Intake sections are created when an award receives a modification - ATP copies and freezes the original Award Intake section.
- **Award Negotiation:** This is the second section users complete.
    - It has an assigned user, selected at award creation
    - An award can have zero Award Negotiation sections. "Expedited" awards skip Award Negotiation, which users indicate by not assigning a user to the Award Negotiation step during award creation.
    - When awards receive modifications, the Award Negotiation section is copied and frozen the same way the Award Intake section is.
- **Award Setup:** Users use this section to help them prepare GW's accounting system (EAS) for the award.
    - It has an assigned user, selected at award creation
    - An award always has exactly one Award Setup section
    - The Award Setup section has one subsection, PTA #s. An Award can have zero or many PTA #s.
    - This section also includes a special view which displays an award summary report to help Award Setup users quickly find the information they need to add to EAS.
- **Subawards:** This section is used to manage any subcontractors GW uses during the award
    - It has an assigned user, selected at award creation
    - Like Award Negotiation, "expedited" awards skip the Subawards section.
    - An award can have zero or many subawards.
    - This section and the Award Management section are worked on simultaneously. The award does not move to Award Closeout until both are complete.
- **Award Management:** This section helps OVPR manage their compliance work while the award is in progress
    - It has an assigned user, selected at award creation
    - An award always has exactly one Award Management section
    - There are two subsections in Award Management - Prior Approval / NCE and Report Submissions. An award can have zero or many of each.
    - This section and the Subawards section are worked on simultaneously. The award does not move to Award Closeout until both are complete.
- **Award Closeout:** The last section
    - It has an assigned user, selected at award creation
    - An award always has exactly one Award Closeout section
    - There is one subsection in Award Closeout, Final Reports. An award can have zero or many final reports.
    - When users click "Save and send to next step" in this section, the award's status is set to "Complete" (though users can still edit any data on the award)

Technical overview
------------------

This section provides technical explanations for ATP's core architecture and more complex features.

Data Architecture
~~~~~~~~~~~~~~~~~

Good Django projects have "fat models and thin views," keeping business logic as close to the models as possible. This project adhered to that philosophy as much as possible.

In ATP, a central **Award** model tracks each award's workflow status and user assignments. Different models exist for each section on the award (Proposal, AwardAcceptance, AwardNegotiation, etc.) and each has a foreign key to an Award object. Subsections (PTA #s, Final Reports, etc.) also have foreign keys directly to an award, though they are rendered with a specific section in the front-end.

FieldIteratorMixin
~~~~~~~~~~~~~~~~~~

Most models inherit from the ``FieldIteratorMixin`` class, which adds helper methods to each model which help render an object's data in the templates. This mixin (and ATP's use of ModelForms) means that when new fields are added to a model, they will automatically be rendered in all front-end screens without needed to alter any template code.

This mixin also contains methods to group fields under headings and in tables, as specified by certain properties on each model itself.

View mixins
~~~~~~~~~~~

Many of ATP's views require similar logic: checking if a user has permissions to edit that section, adding the full award object to the view's context, or moving an award to the next step in the workflow.

Class-based views allow us to share that logic across views with mixins. These mixins each override specific methods in the view classes.

Forms
~~~~~

ATP relies heavily on `django-crispy-forms <http://django-crispy-forms.readthedocs.org/en/latest/>`_. Django-crispy-forms simplifies form layout, especially when using the Bootstrap template pack (ATP uses `Bootstrap v3.1.0 <http://getbootstrap.com/>`_).

ATP has one important form mixin, ``AutoFormMixin``, which includes additional logic to lay out forms in a Bootstrap-compatible two column layout. It also adds extra CSS classes to certain input types to trigger some JavaScript form helpers (datepicker, select2).

All section forms inherit from ``AwardSectionForm``, which adds a ``move_to_next_step`` field to forms in views where it should be enabled.

Cayuse interface
~~~~~~~~~~~~~~~~

Cayuse is the third-party tool that GW uses to submit federal proposals. ATP imports that data through Cayuse SDS - Cayuse's API.

The Cayuse API is a standard HTTP API that uses basic HTTP authentication. The only weird things about it are that it uses a non-standard port and that Cayuse's firewalls are restricted to only respond to requests from GW's test and production servers. You cannot access the API locally without using SSH tunneling (described below).

The Cayuse endpoint at deployment was https://sds-or.cayuse424.com:8444/561/gwu/reports/. ATP consumes this interface using the `requests <http://docs.python-requests.org/en/latest/>`_ library in the ``awards/utils`` module.

EAS interface
~~~~~~~~~~~~~

GW's Enterprise Accounting System (EAS) is the official financial system for the university. The end goal for ATP's integration with EAS is that EAS will be able to import data from ATP and use it to automatically set up financial records associated with awards.

For phase one of this project, that process is still manual - but we decided to get a head start by importing a handful of drop-down values into ATP so that ATP users could work with valid EAS data for fields like funding sources, principal investigators (Award Managers) and other EAS-specific fields.

This data is exposed to ATP via a XML-based SOAP interface. EAS is an ancient Oracle database at heart, so this is the best GW could offer us.

Some Python libraries exist for consuming SOAP interfaces, but none are actively maintained and I couldn't successfully use any of them. Instead, I used `Soap UI <http://www.soapui.org/>`_ to figure out the details of a valid SOAP request, and then used the `requests <http://docs.python-requests.org/en/latest/>`_ library to implement the actual interface in ATP.

The interface is implemented in a management command, found in ``core/management/commands/import_eas_data.py``. EAS data changes regularly, so this command is run by a cron job on the server nightly. The AwardManager field is especially large, so instead of consuming all entries nightly, ATP instead requests only those records that have changed in the past week.

ATP uses the primary key values EAS provides so that EAS data and ATP's copy of it is tightly synced.

ATP also reconciles incoming data from Cayuse or Lotus Notes to make all Proposal data EAS-compatible. When a proposal is imported, ATP references existing EASMapping objects to see if it knows what EAS value to use for a given Cayuse/Lotus value. If it doesn't, the user is prompted to reconcile the values manually. ATP will remember the association for future imports.

Active Directory Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ATP uses GW's Active Directory to authenticate users. This is largely accomplished with the ``django-auth-ldap <https://pythonhosted.org/django-auth-ldap/>`_ library.

The one tricky thing here is that django-auth-ldap, by default, allows any user who passes AD authentication to log in to ATP. OVPR wanted to restrict access to only those users who are already in the Django admin. 

This is achieved by overriding the ``get_or_create_user`` method in the ``LDAPBackend`` class. You can see the code in ``core/backends.py``.

Revision tracking
~~~~~~~~~~~~~~~~~

ATP uses ``django-reversion <http://django-reversion.readthedocs.org/en/latest/>`_ to keep a history of every change made to each object in ATP. Users can view an object's previous versions by finding it in the admin interface.

Django-reversion is pretty foolproof, except when you create new objects outside of a web request. When that happens, reversion won't create an initial revision for that object, which could cause ATP to blow up when it attempts to display the last revision date on the front-end.

To correct this, simply run ``python manage.py createinitialrevisions`` and django-revision will create initial revisions for any object in the database that doesn't have them.

Reporting
~~~~~~~~~

ATP uses `django-report-builder <https://github.com/burke-software/django-report-builder>`_ to provide reporting capabilities to end-users. Django-report-builder provides a GUI for users to build their own reports.

When ATP was first launched, it used a management command called ``set_up_reports`` to automatically populate an example report that included every field on an award. Now that ATP is in production, however, you probably won't need to use it again unless the client asks for the sample reports to be refreshed after some field updates have been deployed.

Only one report in ATP, the Proposal Statistics Report, is not generated by django-report-builder. That's because this report queries all submitted proposals in Cayuse, and ATP only imports proposals from Cayuse when a user is ready to associate a proposal to a specific award.

Email notifications
~~~~~~~~~~~~~~~~~~~

ATP sends email noticiations to users when an award becomes assigned to them. This logic is mostly handled via helper methods on the Award model.

Emails in test and production are sent via GW's open SMTP sever. In local development, they will appear in your runserver console.

Datatables
~~~~~~~~~~

ATP makes heavy use of `jQuery DataTables <http://www.datatables.net/>`_. It powers almost all tables in ATP.

A few views with particularly large data sets use DataTable's AJAX loading to improve render time. For these views, a separate functional view provides the table's body via a JSON response.

Autosaving and refreshing
~~~~~~~~~~~~~~~~~~~~~~~~~

ATP's users will work in ATP all day long, so OVPR requested an autosave feature. ATP includes simple autosave functionality based on jQuery that is implemented mainly in ``static/js/ovpr-atp.js`` and ``static/js/section-form.js``. In short, every time a user changes a form field, ATP starts a four minute timer. Once that timer expires, ATP submits the form using AJAX and replaces the form's HTML with the response.

OVPR also requested that ATP auto-refresh periodically. The auto-refresh interval is five minutes, as set in the ``base.html`` template.

Developing for ATP
------------------

Setting up your local environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ATP is a largely standard Django project and is easy to run in development.  There are two methods for setting up your local envrionment. To use Vagrant, use the following steps:

#. If not already installed, install `Vagrant <https://www.vagrantup.com>`_ and `VirtualBox <https://www.virtualbox.org>`_
#. Clone the repository
#. From the repository's root directory, issue the ``vagrant up`` command
#. Once the provisioning is complete, start an SSH session into the VM: ``vagrant ssh``
#. You'll be prompted by autoenv to source the contents of an environment file, say yes
#. Issue the ``runserver`` command
#. Go to http://localhost:8888 on your host machine and login as ``admin`` with password ``password``

There are some important convenience aliases baked into the Vagrant setup.  The first is the ``manage`` alias, which can be used in place of ``python manage.py``.  The second is ``runserver``, as you saw above.  This one is very important, as that's how you need to run the django development webserver from within Vagrant.  It's an alias of ``python manage.py runserver 0.0.0.0:8000``.  The IP address portion of that command is important because that's what allows Vagrant's port forwarding to work.  The default command runs the server on ``127.0.0.1``, which is a loopback and can't be accessed via your host machine.

If you prefer not to use Vagrant, then use the following steps to get started:

ATP is a largely standard Django project and is easy to run in development. Use the following steps to get started:

#. Clone the repository (you may wish to fork first)
#. Create a virtualenv
#. Install the development requirements: ``pip install -r requirements/local.txt``
#. Create a ``.env`` file to store local environment variables. Here is a sample::

    # Environment variables for the ovpr-hub project
    export DJANGO_SETTINGS_MODULE='settings.local'
    export SECRET_KEY='foooooooo'
    export MYSQL_PASSWORD='ovpr_atp' # Password to your local MySQL database
    export CAYUSE_PASSWORD='fooo'
    export LDAP_PASSWORD='fooo'

    # EAS Settings
    export EAS_PASSWORD='fooooo'
    export EAS_NONCE='fooooooo'
    
#. Source the ``.env`` file in your terminal session: ``source .env`` (consider using `autoenv <https://github.com/kennethreitz/autoenv>`_)
#. Start a local MySQL database and create a schema called ``ovpr_atp``
#. Sync and migrate the database (no need to create a superuser): ``python manage.py syncdb --migrate``
#. Create the test data with the django shell:
    #. ``python manage.py shell``
    #. ``from core.setup import setup_project``
    #. ``setup_project()``
    #. ``quit()``
#. Create initial revisions of the test data: ``python manage.py createinitialrevisions``
#. Start the server: ``python manage.py runserver``
#. Go to http://localhost:8000 and login as ``admin`` with password ``password``.

If you wish, you can skip steps 8 and 9 if you have a JSON export of data from the test or production environments instead.

Running the tests
~~~~~~~~~~~~~~~~~

To run ATP's automated test suite, run this command:

```
coverage run --source=awards,core --omit='*migrations*' manage.py test
```

Get the coverage results with ``coverage report``, and get detailed HTML files of the coverage with ``coverage html``, which will output to a directory called ``htmlcov``.

Working on the interfaces
~~~~~~~~~~~~~~~~~~~~~~~~~

Unfortunately, working with ATP's EAS or Cayuse interfaces is tricky. Both have security limitations in place that only accept requests from GW's test and production servers. You can get around this in local development if you have a GW VPN account and SSH access to those servers:

After connecting to the GW VPN, run this command to pipe all requests to http://localhost:8003 to Cayuse:

``ssh -i ~/.ssh/id_gwu -f andrewbaker@awdtstapp1.es.gwu.edu -L 8003:sds-or.cayuse424.com:8444 -N``

And this command to connect to the EAS production server:

``ssh -i ~/.ssh/id_gwu -f andrewbaker@awdprdapp1.es.gwu.edu -L 8011:easupg.es.gwu.edu:8009 -N``

The ``-i`` flag merely specifies a specific SSH key to use. You will also need to supply your own username in place of ``andrewbaker``.

Deploying to test and production
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Deploying to GW's servers is a little tricky because their systems administrators decided to use RedHat and its Software Collections to install us Python 2.7 (RedHat comes with 2.6 by default).

To run any Python code on the servers, you must follow these steps:

#. SSH into the server
#. Move to the web application directory: ``cd /var/www/``
#. Activate Python 2.7 for this terminal session: ``scl enable python27 bash``
#. Activate the virtual environment: ``source env/bin/activate``
#. Move to the django directory: ``cd django``
#. Source the local environment variables: ``source .env``

To pull down updates from Excella's GitHub, follow these steps:

#. Start SSH on the server: ``eval `ssh-agent```
#. Add the repository's SSH key: ``ssh-add ~/id_foo`` (you will need to generate a new key, add it on GitHub, and then copy it to the server for the first deployment - previously I used a personal key)
#. Fetch changes from origin: ``git fetch origin``
#. Merge those changes to the master branch: ``git merge origin/master``

Once you have the new code in place, there are just a few more commands:

#. Apply any migrations: ``python manage.py migrate``
#. Run collectstatic to catch any static asset updates: ``python manage.py collectstatic``
#. Restart Apache ``sudo /sbin/service httpd restart`` (if you get access denied, then GW's sysadmins need to grant you this permission)

Modifying and enhancing ATP
---------------------------

This section describes my best recommendations for how to perform certain likely updates to ATP.

Adding, changing, deleting fields
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is the change that ATP was built for - we know that OVPR will have many small requests like this over the next few years.

These changes are very simple to accommodate. Simply add / change / delete the field in the appropriate model, generate a new migration with ``python manage.py schemamigration --auto awards``, apply it with ``python manage.py migrate``, and you're done.

If this field is a user-facing field, then be sure to make it ``blank=True`` and/or ``null=True``. CharFields need only ``blank=True`` - most other types of fields need both. Almost all user-facing fields in ATP are nullable because ATP enforces "required" fields when users attempt to move an award to the next step.

If this field is not a user-facing field, then be sure to add it to the ``HIDDEN_FIELDS`` list on its model so that it is not automatically displayed in user-facing forms and detail views.

If OVPR wants this new field to appear in the EAS Award Setup report, then add its name to the model's ``EAS_REPORT_FIELDS`` list.

Displaying fields in groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~

One likely modification in future ATP work is grouping fields together in the detail views so that they're easier to read. This feature has already been implemented for the Proposal section, and should be easy to implement for other sections.

To group fields together under a subheading, add an entry in the ``FIELDSETS`` list of the model with the name of the subheading and which fields should appear in it. Reference the ``FIELDSETS`` list in the Proposal model to see the correct format.

ATP can also display similar fields in a table instead of displaying them individually. Reference the ``DISPLAY_TABLES`` list in the Proposal model for an example.

Adding subsections
~~~~~~~~~~~~~~~~~~

OVPR may want to add new subsections to ATP. If that happens, you will need to create a new model, new form, new views, and new URLs, but it should be pretty straightforward.

Use the FinalReport model as an example. You will want to create a new model which defines all the same methods and properties (with different fields of course).

For forms and views, you can safely copy the definitions for the FinalReport form and views, replacing all references to FinalReport with a reference to your new model. You can use the same approach to create new URLs for your new views.

To get your new subsection to appear in templates, reference the ``finalreport_form.html`` template and the ``finalreport_confirm_delete.html`` template. The ``award_base.html`` template is the main template for ATP - find references to "Final Reports" in there to see how to create template code for your new model.




