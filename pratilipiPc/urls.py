from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', TemplateView.as_view(template_name='welcome.html'), name='welcome'),
    path('admin/', admin.site.urls),

    path('api/auth/', include('authDesk.urls')),
    path('api/', include('profileDesk.urls')),
    path('api/community/', include('communityDesk.urls')),
    path('api/store/', include('storeDesk.urls')),
    path('api/home/', include('homeDesk.urls')),
    path('api/premium/', include('premiumDesk.urls')),
    path('api/search/', include('searchDesk.urls')),
    path('api/notification/', include('notificationDesk.urls')),
    path('api/coin/', include('coinManagementDesk.urls')),
    path('api/carousel/', include('carouselDesk.urls')),
    path('api/digitalcomic/', include('digitalcomicDesk.urls')),
    path('api/motioncomic/', include('motioncomicDesk.urls')),
    path('api/favourite/', include('favouriteDesk.urls')),
    path('api/creator/', include('creatorDesk.urls')),
    path("api/activity/", include("readingActivityDesk.urls")),

    # Payments
    path('api/payments/razorpay/', include('paymentsDesk.urls')),
    path('api/payments/play/', include('paymentsDesk.play_urls')),  # Google Play verify endpoint
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)