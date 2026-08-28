from django.urls import path

from . import concept_views, views


urlpatterns = [
    path("", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("app/", views.app_home, name="app"),
    path("app/concept-demo/", concept_views.concept_demo_home, name="concept_demo"),
    path("app/history/", views.assessment_history, name="assessment_history"),
    path(
        "app/history/<int:record_id>/",
        views.assessment_history_detail,
        name="assessment_history_detail",
    ),
    path("logout/", views.logout_view, name="logout"),
    path("api/pipeline/", views.pipeline_api, name="pipeline_api"),
    path("api/concept-match/", concept_views.concept_match_api, name="concept_match_api"),
    path("api/concept-confirm/", concept_views.concept_confirm_api, name="concept_confirm_api"),
    path("api/demo/<str:case_id>/", views.demo_case_api, name="demo_case_api"),
    path(
        "api/demo/<str:case_id>/stage/<str:stage_name>/",
        views.demo_stage_api,
        name="demo_stage_api",
    ),
    path("health/", views.health, name="health"),
]
