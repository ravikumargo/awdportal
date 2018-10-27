# Definitions for the form classes used to display the input forms on the site.
# Makes use of crispy-forms for better layout handling.
#
# See Django documentation at https://docs.djangoproject.com/en/1.6/topics/forms/
# See crispy-forms documentation at https://django-crispy-forms.readthedocs.org/en/latest/

from django.contrib.auth.forms import AuthenticationForm

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, Submit
from crispy_forms.bootstrap import FormActions


class LoginForm(AuthenticationForm):
    """Form to allow the user to login"""

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Login',
                'username',
                Field('password', autocomplete='off'),
            ),
            FormActions(
                Submit('submit', 'Submit', css_class='button white')
            )
        )
