from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


def home_redirect(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/dashboard/')
    return HttpResponseRedirect('/accounts/login/')


urlpatterns = [
    path('', home_redirect, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', include('requests.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
