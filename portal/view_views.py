"""Django endpoints for the /view state-machine interview prototype."""

from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from portal.view_state import (
    confirm_conflict,
    initial_view_state,
    reject_conflict,
    submit_answer,
)


SESSION_KEY = "view_state"


def _get_state(request):
    state = request.session.get(SESSION_KEY)
    if not isinstance(state, dict):
        state = initial_view_state()
        request.session[SESSION_KEY] = state
    return state


def _save_state(request, state):
    request.session[SESSION_KEY] = state
    request.session.modified = True


@login_required(login_url="login")
def view_home(request):
    state = _get_state(request)
    return render(request, "portal/view.html", {"view_state": state})


@require_POST
@login_required(login_url="login")
def view_reset_api(request):
    state = initial_view_state()
    _save_state(request, state)
    return JsonResponse(state)


@require_POST
@login_required(login_url="login")
def view_answer_api(request):
    try:
        payload = json.loads(request.body or "{}")
        answer = str(payload.get("answer", ""))
        state = _get_state(request)
        state = submit_answer(state, answer)
        _save_state(request, state)
        return JsonResponse(state)
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        return JsonResponse({"error": str(error)}, status=400)


@require_POST
@login_required(login_url="login")
def view_confirm_api(request):
    try:
        payload = json.loads(request.body or "{}")
        codes = payload.get("codes", [])
        if not isinstance(codes, list) or not all(isinstance(code, str) for code in codes):
            raise ValueError("codes must be a list of strings.")
        state = _get_state(request)
        state = confirm_conflict(state, codes)
        _save_state(request, state)
        return JsonResponse(state)
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        return JsonResponse({"error": str(error)}, status=400)


@require_POST
@login_required(login_url="login")
def view_reject_api(request):
    try:
        state = _get_state(request)
        state = reject_conflict(state)
        _save_state(request, state)
        return JsonResponse(state)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
