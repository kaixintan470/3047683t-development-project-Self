from django.urls import path

from . import concept_views, view_views, views


urlpatterns = [
    path("", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("app/", views.app_home, name="app"),
    path("view/", view_views.view_home, name="view_home"),
    path("app/concept-demo/", concept_views.concept_demo_home, name="concept_demo"),
    path("app/history/", views.assessment_history, name="assessment_history"),
    path(
        "app/history/<int:record_id>/",
        views.assessment_history_detail,
        name="assessment_history_detail",
    ),
    path("logout/", views.logout_view, name="logout"),
    path("api/pipeline/", views.pipeline_api, name="pipeline_api"),
    path("api/view/state/", view_views.view_state_api, name="view_state_api"),
    path("api/view/reset/", view_views.view_reset_api, name="view_reset_api"),
    path("api/view/answer/", view_views.view_answer_api, name="view_answer_api"),
    path("api/view/confirm/", view_views.view_confirm_api, name="view_confirm_api"),
    path("api/view/reject/", view_views.view_reject_api, name="view_reject_api"),
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
