# Defines the URL routes within the site. Most of these
# URL definitions pass their work off to other urls.py files.

from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings
from django.views.generic import TemplateView, RedirectView
from django.contrib.auth.decorators import login_required
from core.forms import LoginForm
from awards.views import logout, required

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', RedirectView.as_view(url='/awards'), name='base'),

    # Examples:
    url(r'^login/$', 'django.contrib.auth.views.login',
        {'template_name': 'core/login.html',
         'authentication_form': LoginForm},
        name='login'),
    url(r'^logout/$', logout, {'next_page': 'home'}, name='logout'),
    # url(r'^accounts/', include('core.urls')),
    url(r'^awards/', include('awards.urls')),
    #url(r'^report_builder/', include('report_builder.urls')),
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += required(
    login_required,
    patterns('',
             url(r'^report_builder/', include('report_builder.urls')),
    )
)

# Uncomment the next line to serve media files in dev.
# urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# if settings.DEBUG:
#     import debug_toolbar
#     urlpatterns += patterns('',
#                             url(r'^__debug__/', include(debug_toolbar.urls)),
#                             )
