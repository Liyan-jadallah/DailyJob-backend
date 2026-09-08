from django.contrib import admin
from django.urls import path, re_path, include
from core.views import CustomAuthToken, index
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')), 
    path('api/login/', CustomAuthToken.as_view(), name='api-login'), 
    path('', index, name='index'),
]

# Serve media files (works in both dev and production for simple deployments)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]

dai_dir = getattr(settings, 'DAI_DIR', os.path.join(settings.BASE_DIR, 'dai') if os.path.exists(os.path.join(settings.BASE_DIR, 'dai')) else os.path.join(settings.BASE_DIR.parent, 'dai'))
if os.path.exists(dai_dir):
    urlpatterns.append(
        re_path(r'^(?!api|admin|media)(?P<path>.*)$', serve, {
            'document_root': dai_dir,
            'show_indexes': False
        })
    )
