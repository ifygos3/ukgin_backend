from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from ukgin_config import settings


urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),

    # path('lga/', include('rivers_lga.urls')),
    # path('africa/', include('africa_countries.urls')),
    # path('ecommerce/', include('ecommerce_model.urls')),
   
]
if settings.DEBUG:
   urlpatterns+=static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

