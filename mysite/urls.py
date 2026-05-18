from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from blog.views import dashboard_index, dashboard_users,dashboard_posts, dashboard_jobs
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('myapp.urls')),
    path('accounts/', include('allauth.urls')),  
    path('api/blog/', include('blog.urls')),  
    path('api/job/', include('jobs.urls')),  
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('dashboard/',        dashboard_index, name='dashboard'),
    path('dashboard/users/',  dashboard_users, name='dashboard-users'),
    path('dashboard/posts/',  dashboard_posts, name='dashboard-posts'),
    path('dashboard/jobs/',   dashboard_jobs,  name='dashboard-jobs'),
]
