from types import SimpleNamespace
from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.conf import settings
from django.utils import timezone

from dataclasses import asdict

from core.schemas import (
    DCSDecision,
    DCSResult,
    DiagnosisCandidate,
    KASResult,
    LCSResult,
    PatientState,
    PipelineResult,
    PipelineStatus,
)
from portal.models import AssessmentRecord
from portal.views import FollowupRequired


def almost_complete_patient() -> PatientState:
    return PatientState(
        chief_complaint="dysuria",
        symptoms=["frequency"],
        age=28,
        gender="female",
        explicit_negations=["medical_history", "allergies", "medications"],
    )


def approved_result(patient: PatientState):
    return SimpleNamespace(
        status=PipelineStatus.APPROVED,
        patient_info=patient,
        supporting_evidence=[],
        slm_a_output=None,
        slm_b_output=None,
        kas=KASResult(0.7123456789),
        lcs=LCSResult(3),
        dcs=DCSResult(0.7842592591, DCSDecision.APPROVED),
        candidate_diagnoses=[DiagnosisCandidate("Saved approved condition", 0.8)],
        reasoning_summary="Saved evidence-grounded assessment summary.",
        validation_notes="",
    )


class PortalIntegrationTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="portal@example.com",
            email="portal@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)

    def test_optional_input_guidance_and_assessment_container_are_present(self) -> None:
        response = self.client.get("/app/")
        script = (settings.BASE_DIR / "static/portal/app.js").read_text(encoding="utf-8")

        self.assertContains(response, 'enter “No” or “None”')
        self.assertContains(response, "Leave it blank only when")
        self.assertContains(response, "Assessment Summary")
        self.assertIn("toFixed(decimalPlaces)", script)

    def test_malformed_api_request_returns_json_error(self) -> None:
        response = self.client.post(
            "/api/pipeline/", data="{not-json", content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertIn("error", response.json())

    def test_demo_ui_marks_scripted_mode_without_evaluation_labels(self) -> None:
        response = self.client.get("/app/")

        self.assertContains(response, "Load Demo A — Complete UTI Case")
        self.assertContains(response, "Load Demo B — Incomplete UTI Case")
        self.assertContains(response, "fixed scripted outputs")
        self.assertContains(response, "Run Live Assessment")
        self.assertNotContains(response, "expected_information_state")
        self.assertNotContains(response, "target_category")

    @patch("portal.views.create_real_pipeline")
    def test_demo_a_initial_state_is_detailed_and_scripted(self, create_pipeline) -> None:
        response = self.client.get("/api/demo/GU01_UTI_COMPLETE/")
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["demo_mode"], "scripted_presentation")
        self.assertEqual(data["presentation_stage"], "initial")
        self.assertEqual(data["main_action"], "Run real pipeline")
        self.assertEqual(data["patient"]["age"], 29)
        self.assertIn("mild lower abdominal discomfort", data["patient"]["symptoms"])
        create_pipeline.assert_not_called()

    @patch("portal.views.create_real_pipeline")
    def test_demo_a_final_transition_is_fixed_and_never_live(self, create_pipeline) -> None:
        initial = self.client.get("/api/demo/GU01_UTI_COMPLETE/").json()
        final = self.client.get("/api/demo/GU01_UTI_COMPLETE/stage/final/").json()

        self.assertEqual(initial["presentation_stage"], "initial")
        self.assertEqual(final["presentation_stage"], "final")
        self.assertEqual(final["status"], "APPROVED")
        self.assertIn("assessment_summary", final)
        self.assertTrue(final["evidence"])
        self.assertIsNotNone(final["slm_a"])
        self.assertIsNotNone(final["slm_b"])
        self.assertEqual(final["lcs"], 3)
        create_pipeline.assert_not_called()

    @patch("portal.views.create_real_pipeline")
    def test_demo_b_initial_state_keeps_discriminator_unknown(self, create_pipeline) -> None:
        data = self.client.get("/api/demo/GU02_UTI_INCOMPLETE/").json()

        self.assertEqual(data["presentation_stage"], "initial")
        self.assertTrue(data["patient"]["medical_history"])
        self.assertTrue(data["patient"]["allergies"])
        self.assertTrue(data["patient"]["medications"])
        self.assertEqual(data["patient"]["vaginal_discharge"], "Unknown / not yet provided")
        self.assertEqual(data["main_action"], "Run real pipeline")
        create_pipeline.assert_not_called()

    @patch("portal.views.create_real_pipeline")
    def test_demo_b_first_transition_is_click_only_followup(self, create_pipeline) -> None:
        data = self.client.get("/api/demo/GU02_UTI_INCOMPLETE/stage/followup/").json()

        self.assertEqual(data["presentation_stage"], "followup")
        self.assertEqual(data["heading"], "Additional information required")
        self.assertEqual(data["follow_up_question"], "Do you currently have any unusual vaginal discharge?")
        self.assertEqual(data["main_action"], "Submit Additional Information")
        self.assertFalse(data["answer_required"])
        self.assertNotIn("assessment_summary", data)
        create_pipeline.assert_not_called()

    @patch("portal.views.create_real_pipeline")
    def test_demo_b_second_transition_applies_fact_and_is_fixed(self, create_pipeline) -> None:
        final = self.client.get("/api/demo/GU02_UTI_INCOMPLETE/stage/final/").json()

        self.assertEqual(final["presentation_stage"], "final")
        self.assertEqual(final["patient"]["vaginal_discharge"], "Confirmed absent")
        self.assertEqual(final["patient"]["follow_up_answers"]["vaginal_discharge"], "No unusual vaginal discharge.")
        self.assertEqual(final["status"], "APPROVED")
        self.assertIn("assessment_summary", final)
        self.assertTrue(final["evidence"])
        create_pipeline.assert_not_called()

    def test_demo_switching_uses_clean_initial_payloads(self) -> None:
        self.client.get("/api/demo/GU01_UTI_COMPLETE/stage/final/")
        demo_b_initial = self.client.get("/api/demo/GU02_UTI_INCOMPLETE/").json()
        self.client.get("/api/demo/GU02_UTI_INCOMPLETE/stage/final/")
        demo_a_initial = self.client.get("/api/demo/GU01_UTI_COMPLETE/").json()
        script = (settings.BASE_DIR / "static/portal/app.js").read_text(encoding="utf-8")

        self.assertEqual(demo_b_initial["presentation_stage"], "initial")
        self.assertEqual(demo_b_initial["patient"]["vaginal_discharge"], "Unknown / not yet provided")
        self.assertEqual(demo_a_initial["presentation_stage"], "initial")
        self.assertIn('demoStage = "initial"', script)
        self.assertIn("clearClinicalOutput()", script)

    @patch("portal.views.create_real_pipeline")
    def test_patient_answer_reaches_canonical_pipeline(self, create_pipeline) -> None:
        patient = almost_complete_patient()
        create_pipeline.return_value.current_stage = "UNRESOLVED"
        create_pipeline.return_value.run.return_value = PipelineResult(
            PipelineStatus.UNRESOLVED_INSUFFICIENT_INFORMATION,
            PatientState(**patient.__dict__),
        )

        response = self.client.post(
            "/api/pipeline/",
            data={"field": "duration", "answer": "2 days", "patient": asdict(patient)},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        passed_patient = create_pipeline.call_args.args[0]
        self.assertEqual(passed_patient.duration, "2 days")

    @patch("portal.views.create_real_pipeline")
    def test_follow_up_question_is_rendered(self, create_pipeline) -> None:
        patient = almost_complete_patient()
        create_pipeline.return_value.current_stage = "FOLLOW_UP"
        create_pipeline.return_value.run.return_value = PipelineResult(
            PipelineStatus.NEED_MORE_INFO,
            PatientState(**{**patient.__dict__, "duration": "2 days"}),
            validation_notes="Could you describe any fever?",
        )

        response = self.client.post(
            "/api/pipeline/",
            data={"field": "duration", "answer": "2 days", "patient": asdict(patient)},
            content_type="application/json",
        )

        self.assertContains(response, "Could you describe any fever?")

    @patch("portal.views.create_real_pipeline")
    def test_approved_scores_are_rendered_from_backend(self, create_pipeline) -> None:
        patient = almost_complete_patient()
        approved = SimpleNamespace(
            status=PipelineStatus.APPROVED,
            patient_info=PatientState(**{**patient.__dict__, "duration": "2 days"}),
            supporting_evidence=[],
            slm_a_output=None,
            slm_b_output=None,
            kas=KASResult(0.82),
            lcs=LCSResult(3),
            dcs=DCSResult(0.865, DCSDecision.APPROVED),
            candidate_diagnoses=[DiagnosisCandidate("Canonical approved condition", 0.82)],
            reasoning_summary="Existing evidence-grounded approved summary.",
            validation_notes="",
        )
        create_pipeline.return_value.current_stage = "APPROVED"
        create_pipeline.return_value.run.return_value = approved

        response = self.client.post(
            "/api/pipeline/",
            data={"field": "duration", "answer": "2 days", "patient": asdict(patient)},
            content_type="application/json",
        )

        self.assertJSONEqual(
            response.content,
            {**response.json(), "kas": 0.82, "lcs": 3, "dcs": 0.865, "decision": "APPROVED"},
        )
        self.assertEqual(
            response.json()["assessment_summary"],
            {
                "likely_condition": "Canonical approved condition",
                "summary": "Existing evidence-grounded approved summary.",
            },
        )

    @patch("portal.views.create_real_pipeline")
    def test_pipeline_failure_returns_json_without_fake_success(self, create_pipeline) -> None:
        patient = almost_complete_patient()
        create_pipeline.side_effect = RuntimeError("local service unavailable")

        response = self.client.post(
            "/api/pipeline/",
            data={"field": "duration", "answer": "2 days", "patient": asdict(patient)},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertIn("error", response.json())
        self.assertNotIn("assessment_summary", response.json())


class AssessmentHistoryTests(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user_a = User.objects.create_user(
            username="history-a@example.com", password="test-password"
        )
        self.user_b = User.objects.create_user(
            username="history-b@example.com", password="test-password"
        )
        self.client.force_login(self.user_a)

    @staticmethod
    def complete_patient(**changes) -> PatientState:
        values = {
            **almost_complete_patient().__dict__,
            "duration": "2 days",
            **changes,
        }
        return PatientState(**values)

    def create_record(self, user, condition: str) -> AssessmentRecord:
        return AssessmentRecord.objects.create(
            user=user,
            decision="APPROVED",
            likely_condition=condition,
            assessment_summary=f"Summary for {condition}",
            kas=0.71,
            lcs=3,
            dcs=0.78,
            patient_snapshot={"chief_complaint": "saved"},
            result_snapshot={"status": "APPROVED", "evidence": []},
        )

    def post_real_assessment(self, patient: PatientState, **extra):
        payload = {
            "field": "run_loaded_case",
            "answer": "",
            "patient": asdict(patient),
            **extra,
        }
        return self.client.post(
            "/api/pipeline/", data=payload, content_type="application/json"
        )

    def test_assessment_record_is_linked_to_user(self) -> None:
        record = self.create_record(self.user_a, "Condition A")

        self.assertEqual(record.user, self.user_a)
        self.assertEqual(list(self.user_a.assessment_records.all()), [record])
        self.assertFalse(self.user_b.assessment_records.exists())

    @patch("portal.views.create_real_pipeline")
    def test_real_terminal_assessment_creates_history_record(self, create_pipeline) -> None:
        patient = self.complete_patient()
        create_pipeline.return_value.current_stage = "APPROVED"
        create_pipeline.return_value.run.return_value = approved_result(patient)

        response = self.post_real_assessment(patient)

        self.assertEqual(response.status_code, 200)
        record = AssessmentRecord.objects.get()
        self.assertEqual(record.user, self.user_a)
        self.assertEqual(record.decision, "APPROVED")
        self.assertEqual(record.likely_condition, "Saved approved condition")
        self.assertEqual(record.assessment_summary, "Saved evidence-grounded assessment summary.")
        self.assertEqual(record.kas, 0.7123456789)
        self.assertEqual(record.lcs, 3)
        self.assertEqual(record.dcs, 0.7842592591)
        self.assertEqual(record.patient_snapshot, response.json()["patient"])
        self.assertEqual(record.result_snapshot, response.json())

    @patch("portal.views.create_real_pipeline")
    def test_terminal_unresolved_assessment_creates_history_record(self, create_pipeline) -> None:
        patient = self.complete_patient()
        create_pipeline.return_value.current_stage = "UNRESOLVED"
        create_pipeline.return_value.run.return_value = PipelineResult(
            PipelineStatus.UNRESOLVED_INSUFFICIENT_INFORMATION,
            patient,
        )

        response = self.post_real_assessment(patient)

        self.assertEqual(response.status_code, 200)
        record = AssessmentRecord.objects.get()
        self.assertEqual(record.decision, "UNRESOLVED_INSUFFICIENT_INFORMATION")
        self.assertEqual(record.likely_condition, "")
        self.assertIsNone(record.kas)

    @patch("portal.views.create_real_pipeline")
    def test_follow_up_required_does_not_create_history_record(self, create_pipeline) -> None:
        patient = self.complete_patient()
        create_pipeline.return_value.patient = patient
        create_pipeline.return_value.run.side_effect = FollowupRequired(
            "Could you provide one additional fact?"
        )

        response = self.post_real_assessment(patient)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "NEED_MORE_INFO")
        self.assertFalse(AssessmentRecord.objects.exists())

    @patch("portal.views.create_real_pipeline")
    def test_terminal_follow_up_completion_creates_one_history_record(self, create_pipeline) -> None:
        patient = self.complete_patient(
            follow_up_answers={"vaginal_discharge": "No unusual vaginal discharge."},
            explicit_negations=[
                "medical_history",
                "allergies",
                "medications",
                "vaginal_discharge",
            ],
        )
        create_pipeline.return_value.current_stage = "APPROVED"
        create_pipeline.return_value.run.return_value = approved_result(patient)

        response = self.client.post(
            "/api/pipeline/",
            data={
                "field": "pipeline_follow_up",
                "answer": "No unusual vaginal discharge.",
                "patient": asdict(self.complete_patient()),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AssessmentRecord.objects.count(), 1)
        saved = AssessmentRecord.objects.get().patient_snapshot
        self.assertEqual(
            saved["follow_up_answers"]["vaginal_discharge"],
            "No unusual vaginal discharge.",
        )
        self.assertIn("vaginal_discharge", saved["explicit_negations"])

    @patch("portal.views.create_real_pipeline")
    def test_pipeline_failure_does_not_create_history_record(self, create_pipeline) -> None:
        create_pipeline.side_effect = RuntimeError("local service unavailable")

        response = self.post_real_assessment(self.complete_patient())

        self.assertEqual(response.status_code, 500)
        self.assertFalse(AssessmentRecord.objects.exists())

    @patch("portal.views.create_real_pipeline")
    def test_scripted_demos_do_not_create_history_records(self, create_pipeline) -> None:
        paths = [
            "/api/demo/GU01_UTI_COMPLETE/",
            "/api/demo/GU01_UTI_COMPLETE/stage/final/",
            "/api/demo/GU02_UTI_INCOMPLETE/",
            "/api/demo/GU02_UTI_INCOMPLETE/stage/followup/",
            "/api/demo/GU02_UTI_INCOMPLETE/stage/final/",
        ]

        for path in paths:
            self.assertEqual(self.client.get(path).status_code, 200)

        self.assertFalse(AssessmentRecord.objects.exists())
        create_pipeline.assert_not_called()

    def test_history_requires_login(self) -> None:
        self.client.logout()

        self.assertRedirects(self.client.get("/app/history/"), "/?next=/app/history/")

    def test_history_only_shows_current_users_records(self) -> None:
        self.create_record(self.user_a, "Visible condition")
        self.create_record(self.user_b, "Other user's condition")

        response = self.client.get("/app/history/")

        self.assertContains(response, "Visible condition")
        self.assertNotContains(response, "Other user&#x27;s condition")
        self.assertNotContains(response, "Other user's condition")

    def test_user_cannot_open_another_users_history_record(self) -> None:
        other_record = self.create_record(self.user_b, "Private condition")

        response = self.client.get(f"/app/history/{other_record.id}/")

        self.assertEqual(response.status_code, 404)

    def test_history_is_newest_first(self) -> None:
        first = self.create_record(self.user_a, "First condition")
        AssessmentRecord.objects.filter(pk=first.pk).update(
            created_at=timezone.now() - timedelta(minutes=1)
        )
        first.refresh_from_db()
        second = self.create_record(self.user_a, "Second condition")

        response = self.client.get("/app/history/")

        self.assertEqual(list(response.context["records"]), [second, first])
        self.assertLess(
            response.content.index(b"Second condition"),
            response.content.index(b"First condition"),
        )

    @patch("portal.views.create_real_pipeline")
    def test_history_pages_read_saved_data_without_inference(self, create_pipeline) -> None:
        record = self.create_record(self.user_a, "Read-only condition")

        history = self.client.get("/app/history/")
        detail = self.client.get(f"/app/history/{record.id}/")

        self.assertEqual(history.status_code, 200)
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Read-only condition")
        create_pipeline.assert_not_called()


class AuthenticationTests(TestCase):
    def test_landing_page_and_protected_app(self) -> None:
        landing = self.client.get("/")
        protected = self.client.get("/app/")

        self.assertEqual(landing.status_code, 200)
        self.assertContains(landing, "Sign in")
        self.assertRedirects(protected, "/?next=/app/")

    def test_registration_creates_hashed_password_and_logs_in(self) -> None:
        response = self.client.post(
            "/register/",
            {
                "email": "new@example.com",
                "password": "local-password",
                "confirm_password": "local-password",
            },
        )

        self.assertRedirects(response, "/app/")
        user = get_user_model().objects.get(username="new@example.com")
        self.assertNotEqual(user.password, "local-password")
        self.assertTrue(user.check_password("local-password"))
        self.assertEqual(self.client.get("/app/").status_code, 200)

    def test_wrong_password_is_rejected_and_correct_password_logs_in(self) -> None:
        get_user_model().objects.create_user(
            username="login@example.com",
            email="login@example.com",
            password="correct-password",
        )

        wrong = self.client.post(
            "/", {"email": "login@example.com", "password": "wrong-password"}
        )
        self.assertEqual(wrong.status_code, 200)
        self.assertContains(wrong, "Invalid email or password")
        self.assertNotIn("_auth_user_id", self.client.session)

        correct = self.client.post(
            "/", {"email": "login@example.com", "password": "correct-password"}
        )
        self.assertRedirects(correct, "/app/")
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_ends_session(self) -> None:
        user = get_user_model().objects.create_user(
            username="logout@example.com", password="test-password"
        )
        self.client.force_login(user)

        response = self.client.post("/logout/")

        self.assertRedirects(response, "/")
        self.assertRedirects(self.client.get("/app/"), "/?next=/app/")

    def test_unauthenticated_api_returns_json(self) -> None:
        response = self.client.get("/api/demo/GU01_UTI_COMPLETE/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertEqual(response.json(), {"error": "Authentication required."})

    def test_management_command_creates_documented_test_account(self) -> None:
        call_command("ensure_test_account", verbosity=0)

        user = get_user_model().objects.get(username="admin@example.com")
        self.assertEqual(user.email, "admin@example.com")
        self.assertTrue(user.check_password("123456"))
