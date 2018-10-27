# Custom template tags for use within the Awards templates
#
# See Django documentation at https://docs.djangoproject.com/en/1.6/howto/custom-template-tags/

from django import template
from django.forms import Textarea

register = template.Library()


@register.filter
def is_textarea(field):
    """Determines if the given field is a Textarea"""
    return isinstance(field.field.widget, Textarea)

@register.filter
def classname(class_object):
    """Returns the class name of the given object"""
    return class_object.__class__.__name__
