"""
URL configuration for pratilipiPc project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView  # Import TemplateView

from pratilipiPc import settings

urlpatterns = [
    path('', TemplateView.as_view(template_name='welcome.html'), name='welcome'),  # Root URL
    path('admin/', admin.site.urls),
    path('api/', include('profileDesk.urls')),  # Include profileDesk URLs under /api/
    path('api/community/', include('communityDesk.urls')), # Include communityDesk URLs under /api/community/
    path('api/store/', include('storeDesk.urls')),  # Include storeDesk URLs under /api/store/
    path('api/home/', include('homeDesk.urls')),  # Include homeDesk URLs under /api/home/
    path('api/premium/', include('premiumDesk.urls')),  # Include premiumDesk URLs under /api/premium/
    path('api/search/', include('searchDesk.urls')),  # Include searchDesk URLs under /api/search/
    path('api/notification/', include('notificationDesk.urls')),  # Include notificationDesk URLs under /api/notification/
    path('api/coin/', include('coinManagementDesk.urls')),  # Include coinManagementDesk URLs under /api/coin/
    path('api/carousel/', include('carouselDesk.urls')),  # Include carouselDesk URLs under /api/carousel/
    path('api/digitalcomic/', include('digitalcomicDesk.urls')),  # Include digitalcomicDesk URLs under /api/digitalcomic/
    path('api/motioncomic/', include('motioncomicDesk.urls')),  # Include motioncomicDesk URLs under /api/motioncomic/
    path('api/favourite/', include('favouriteDesk.urls')),  # This line should be present
    path('api/creator/', include('creatorDesk.urls')),  # Include creatorDesk URLs under /api/creator/
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns