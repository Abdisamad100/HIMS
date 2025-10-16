from django.urls import path
from . import views

urlpatterns = [
    # Admin routes
    path('portal/admin/register-user/', views.register_user, name='register_user'),

    # Agent routes
    path('agent/register-member/', views.register_member, name='register_member'),
    path('agent/members/', views.member_list, name='member_list'),
    # dashboard routes
    path('', views.dashboard, name='dashboard'),
    path('portal/admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('agent/dashboard/', views.agent_dashboard, name='agent_dashboard'),
    path('claims/dashboard/', views.claim_dashboard, name='claim_dashboard'),
    path('hospital/dashboard/', views.hospital_dashboard, name='hospital_dashboard'),
    path('customer/dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('portal/admin/users/', views.user_list, name='user_list'),
   # claim  routes
    path("claims/", views.ClaimListView.as_view(), name="claim_list"),
    path("claims/<int:pk>/", views.ClaimDetailView.as_view(), name="claim_detail"),
    path("claims/create/", views.hospital_create_edit_claim, name="hospital_create_claim"),
    path("claims/<int:pk>/edit/", views.hospital_create_edit_claim, name="hospital_edit_claim"),
    path("claims/<int:pk>/<str:action>/", views.claim_officer_action, name="claim_officer_action"),
    path('claim/add/', views.hospital_add_claim, name='hospital_add_claim'),
]


