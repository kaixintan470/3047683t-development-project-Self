"""Django interface for the canonical clinical pipeline."""

from dataclasses import asdict
from functools import wraps
import json
import logging
from pathlib import Path

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from core.interview import get_next_question, update_patient_field
from core.pipeline import create_real_pipeline
from core.schemas import PatientState, PipelineStatus
from portal.forms import EmailLoginForm, RegistrationForm
from portal.models import AssessmentRecord


DEMO_CASES = {
    "GU01_UTI_COMPLETE": "demo_a",
    "GU02_UTI_INCOMPLETE": "demo_b",
}
SCRIPTED_DEMO_PATH = Path(__file__).resolve().parent.parent / "test_data" / "scripted_demo_cases.json"
LOGGER = logging.getLogger(__name__)


class FollowupRequired(Exception):
    def __init__(self, question: str) -> None:
        self.question = question


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("app")
    form = EmailLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        user = authenticate(
            request,
            username=email,
            password=form.cleaned_data["password"],
        )
        if user is not None:
            auth_login(request, user)
            return redirect("app")
        form.add_error(None, "Invalid email or password.")
    return render(request, "portal/login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("app")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        auth_login(request, user)
        return redirect("app")
    return render(request, "portal/register.html", {"form": form})


@require_POST
def logout_view(request):
    auth_logout(request)
    return redirect("login")


@login_required(login_url="login")
def app_home(request):
    return render(request, "portal/home.html")


@login_required(login_url="login")
def assessment_history(request):
    records = AssessmentRecord.objects.filter(user=request.user)
    return render(request, "portal/history.html", {"records": records})


@login_required(login_url="login")
def assessment_history_detail(request, record_id: int):
    record = get_object_or_404(
        AssessmentRecord,
        pk=record_id,
        user=request.user,
    )
    return render(request, "portal/history_detail.html", {"record": record})


def api_login_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required."}, status=401)
        return view(request, *args, **kwargs)

    return wrapped


def health(request):
    return JsonResponse({"status": "ok"})


@require_GET
@api_login_required
def demo_case_api(request, case_id: str):
    return _scripted_demo_response(case_id, "initial")


@require_GET
@api_login_required
def demo_stage_api(request, case_id: str, stage_name: str):
    return _scripted_demo_response(case_id, stage_name)


def _scripted_demo_response(case_id: str, stage_name: str) -> JsonResponse:
    if case_id not in DEMO_CASES:
        return JsonResponse({"error": "Unknown demo case"}, status=404)
    allowed_stages = {
        "GU01_UTI_COMPLETE": {"initial", "final"},
        "GU02_UTI_INCOMPLETE": {"initial", "followup", "final"},
    }
    if stage_name not in allowed_stages[case_id]:
        return JsonResponse({"error": "Unknown demo stage"}, status=404)
    try:
        fixture = json.loads(SCRIPTED_DEMO_PATH.read_text(encoding="utf-8"))
        demo = fixture[DEMO_CASES[case_id]]
        state = demo[stage_name]
    except (json.JSONDecodeError, KeyError, OSError, TypeError, ValueError):
        LOGGER.exception("Unable to load scripted demo case %s stage %s", case_id, stage_name)
        return JsonResponse({"error": "Demo case could not be loaded."}, status=500)
    return JsonResponse({
        "demo_mode": fixture["demo_mode"],
        "notice": fixture["notice"],
        "case_id": demo["case_id"],
        "label": demo["label"],
        **state,
    })


def _result_payload(result, pipeline) -> dict[str, object]:
    slm_a = result.slm_a_output
    slm_b = result.slm_b_output
    assessment_summary = None
    if result.status == PipelineStatus.APPROVED:
        diagnoses = result.candidate_diagnoses
        if diagnoses and result.reasoning_summary:
            assessment_summary = {
                "likely_condition": diagnoses[0].name,
                "summary": result.reasoning_summary,
            }
    return {
        "status": result.status.value,
        "patient": asdict(result.patient_info),
        "stage": getattr(pipeline, "current_stage", result.status.value),
        "follow_up_question": (
            result.validation_notes if result.status.value == "NEED_MORE_INFO" else ""
        ),
        "evidence": [asdict(item) for item in result.supporting_evidence],
        "slm_a": (
            {
                "model": slm_a.model,
                "status": slm_a.status.value,
                "reasoning": slm_a.reasoning,
                "sufficiency": slm_a.sufficiency.status,
            }
            if slm_a
            else None
        ),
        "slm_b": (
            {
                "model": slm_b.model,
                "status": slm_b.status.value,
                "reasoning": slm_b.reasoning,
                "sufficiency": slm_b.sufficiency.status,
            }
            if slm_b
            else None
        ),
        "kas": result.kas.score if result.kas else None,
        "lcs": result.lcs.score if result.lcs else None,
        "dcs": result.dcs.score if result.dcs else None,
        "decision": result.dcs.decision.value if result.dcs else result.status.value,
        "assessment_summary": assessment_summary,
    }


def _save_terminal_assessment(user, result, payload: dict[str, object]) -> None:
    terminal_statuses = {
        PipelineStatus.APPROVED,
        PipelineStatus.UNRESOLVED_INSUFFICIENT_INFORMATION,
    }
    if result.status not in terminal_statuses:
        return
    assessment = payload.get("assessment_summary") or {}
    AssessmentRecord.objects.create(
        user=user,
        decision=str(payload["decision"]),
        likely_condition=str(assessment.get("likely_condition", "")),
        assessment_summary=str(assessment.get("summary", "")),
        kas=payload.get("kas"),
        lcs=payload.get("lcs"),
        dcs=payload.get("dcs"),
        patient_snapshot=payload["patient"],
        result_snapshot=payload,
    )


@require_POST
@api_login_required
def pipeline_api(request):
    try:
        payload = json.loads(request.body or "{}")
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        patient_payload = payload.get("patient", {})
        if not isinstance(patient_payload, dict):
            raise ValueError("patient must be a JSON object.")
        patient = PatientState(**patient_payload)
        field_name = payload.get("field", "")
        answer = payload.get("answer", "")
        if not isinstance(field_name, str) or not isinstance(answer, str):
            raise ValueError("field and answer must be strings.")
        if field_name not in {"pipeline_follow_up", "run_loaded_case"}:
            update_patient_field(patient, field_name, answer)
        elif field_name == "pipeline_follow_up":
            payload["follow_up_answer"] = answer
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        return JsonResponse({"error": str(error)}, status=400)
    next_question = get_next_question(patient)
    if next_question:
        next_field, question = next_question
        return JsonResponse(
            {
                "status": "NEED_MORE_INFO",
                "patient": asdict(patient),
                "stage": "INTERVIEW",
                "next_field": next_field,
                "follow_up_question": question,
            }
        )

    supplied_followup = payload.get("follow_up_answer")
    answer_used = False

    def answer_followup(question: str) -> str:
        nonlocal answer_used
        if supplied_followup is None or answer_used:
            raise FollowupRequired(question)
        answer_used = True
        return str(supplied_followup)

    try:
        pipeline = create_real_pipeline(patient, answer_followup)
        result = pipeline.run()
    except FollowupRequired as required:
        return JsonResponse(
            {
                "status": "NEED_MORE_INFO",
                "patient": asdict(pipeline.patient),
                "stage": "FOLLOW_UP",
                "next_field": "pipeline_follow_up",
                "follow_up_question": required.question,
            }
        )
    except Exception:
        LOGGER.exception("Canonical clinical pipeline request failed")
        return JsonResponse(
            {"error": "The clinical pipeline could not complete this request."},
            status=500,
        )

    response_payload = _result_payload(result, pipeline)
    _save_terminal_assessment(request.user, result, response_payload)
    return JsonResponse(response_payload)
