
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from network_app.views import CustomLoginView

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    # ???? ??? ???? ???? ???? ???? ??????
    path('login/', CustomLoginView.as_view(), name='login'),
    path('', include('django.contrib.auth.urls')),
    path('', include('network_app.urls')),
)