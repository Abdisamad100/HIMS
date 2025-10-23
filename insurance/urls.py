from django.urls import path
from . import views

urlpatterns = [
    # Admin routes
    path('portal/admin/register-user/', views.register_user, name='register_user'),
    path('user/<int:pk>/edit/', views.edit_user, name='edit_user'),
    path('user/<int:pk>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('edit-user/<int:pk>/', views.edit_user, name='edit_user'),
    path('filter-users/', views.filter_users, name='filter_users'),
    path('toggle-user-status/<int:pk>/', views.toggle_user_status, name='toggle_user_status'),
    path('profile/', views.profile_view, name='profile'),
    path('agent/member/<int:member_policy_id>/payment/', views.add_member_payment, name='add_member_payment'),



    # Agent routes
    path('agent/register-member/', views.register_member, name='register_member'),
    path('agent/members/', views.member_list, name='member_list'),
    path('agent/<int:pk>/edit/', views.edit_agent, name='edit_agent'),
    path('agent/<int:pk>/toggle/', views.toggle_agent_status, name='toggle_agent_status'),
    # dashboard routes
    path('', views.dashboard, name='dashboard'),
    path('portal/admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('agent/dashboard/', views.agent_dashboard, name='agent_dashboard'),
    path('claims/dashboard/', views.claim_dashboard, name='claim_dashboard'),
    path('hospital/dashboard/', views.hospital_dashboard, name='hospital_dashboard'),
    path('customer/dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('portal/admin/users/', views.user_list, name='user_list'),
   # claim  routes
    # =====================
    # CLAIM ROUTES
    # =====================
    path("claims/", views.ClaimListView.as_view(), name="claim_list"),
    path("claims/<int:pk>/", views.ClaimDetailView.as_view(), name="claim_detail"),

    # Hospital: create or edit claim
    path("claims/create/", views.hospital_create_edit_claim, name="hospital_create_claim"),
    path("claims/<int:pk>/edit/", views.hospital_create_edit_claim, name="hospital_edit_claim"),

    # Claim officer/admin actions
    path("claims/<int:pk>/<str:action>/", views.claim_officer_action, name="claim_officer_action"),
    path("claims/verify/", views.verify_member_policy, name="verify_member_policy"),
    path("claims/book/", views.hospital_book_service, name="hospital_book_service"),



    # Optional: legacy or quick-add form (e.g., from dashboard)
    path("claim/add/", views.hospital_add_claim, name="hospital_add_claim"),
    # hospital  routes
    path('hospitals/', views.hospital_list, name='hospital_list'),
    path('hospital/toggle/<int:pk>/', views.toggle_hospital_status, name='toggle_hospital_status'),
    path('edit-hospital/<int:pk>/', views.edit_hospital, name='edit_hospital'),
    path('toggle-hospital-status/<int:pk>/', views.toggle_hospital_status, name='toggle_hospital_status'),

    # reports routes
    path('export/users/', views.export_users_csv, name='export_users_csv'),
    path('export/claims/', views.export_claims_csv, name='export_claims_csv'),

    # policy routes
    path('policies/', views.policy_list, name='policy_list'),
    path('policies/create/', views.create_policy, name='create_policy'),
    path('policies/<int:policy_id>/edit/', views.edit_policy, name='edit_policy'),
    path('policies/<int:policy_id>/delete/', views.delete_policy, name='delete_policy'),
]



