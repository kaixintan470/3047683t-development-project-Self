function initialisePortal() {
    const form = document.querySelector("#answer-form");
    const answer = document.querySelector("#answer");
    const answerLabel = document.querySelector("#answer-label");
    const answerRow = document.querySelector("#answer-row");
    const action = document.querySelector("#pipeline-action");
    const question = document.querySelector("#question");
    const stage = document.querySelector("#stage");
    const message = document.querySelector("#message");
    const demoLabel = document.querySelector("#demo-label");
    const demoNotice = document.querySelector("#demo-notice");
    const inputGuidance = document.querySelector("#input-guidance");
    const mappingCard = document.querySelector("#mapping-card");
    const mappingOriginal = document.querySelector("#mapping-original");
    const mappingCandidates = document.querySelector("#mapping-candidates");
    const mappingConfirm = document.querySelector("#mapping-confirm");
    const mappingReject = document.querySelector("#mapping-reject");
    const optionalFields = new Set(["medical_history", "allergies", "medications"]);

    let currentField = "chief_complaint";
    let patientState = {};
    let interviewState = null;
    let demoMode = null;
    let demoStage = null;

    async function readJson(response) {
        const contentType = response.headers.get("content-type") || "";
        if (!contentType.toLowerCase().includes("application/json")) {
            await response.text();
            throw new Error(`Server returned ${response.status} without a JSON response.`);
        }
        try {
            return await response.json();
        } catch (_error) {
            throw new Error(`Server returned ${response.status} with invalid JSON.`);
        }
    }

    async function postJson(url, payload = {}) {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value,
            },
            body: JSON.stringify(payload),
        });
        const data = await readJson(response);
        if (!response.ok) throw new Error(data.error || "Request failed");
        return data;
    }

    function updateInputGuidance() {
        answer.required = !optionalFields.has(currentField);
    }

    function setAnswerVisible(visible) {
        answer.hidden = !visible;
        answerLabel.hidden = !visible;
        inputGuidance.hidden = !visible;
        answerRow.classList.toggle("demo-action-only", !visible);
        answer.disabled = !visible;
        if (!visible) answer.required = false;
    }

    function scoreText(value, decimalPlaces) {
        if (value === null || value === undefined) return "\u2014";
        const numericValue = Number(value);
        return Number.isFinite(numericValue) ? numericValue.toFixed(decimalPlaces) : "\u2014";
    }

    function renderAssessment(data) {
        const section = document.querySelector("#assessment-summary");
        const summary = data.status === "APPROVED" ? data.assessment_summary : null;
        section.hidden = !summary;
        document.querySelector("#likely-condition").textContent = summary?.likely_condition || "";
        document.querySelector("#assessment-text").textContent = summary?.summary || "";
    }

    function textValue(value) {
        if (Array.isArray(value)) return value.join(" ") || "Confirmed absent";
        if (value && typeof value === "object") return JSON.stringify(value);
        return value === null || value === "" ? "\u2014" : String(value);
    }

    function renderPatient(patient) {
        const container = document.querySelector("#patient-state");
        container.innerHTML = "";
        Object.entries(patient || {}).forEach(function ([key, value]) {
            if (key === "follow_up_answers" || key === "explicit_negations") return;
            const term = document.createElement("dt");
            const detail = document.createElement("dd");
            term.textContent = key.replaceAll("_", " ");
            detail.textContent = textValue(value);
            container.append(term, detail);
        });
    }

    function renderEvidence(items) {
        const container = document.querySelector("#evidence");
        container.innerHTML = "";
        if (!items || !items.length) {
            container.textContent = "Evidence appears after retrieval.";
            container.className = "empty";
            return;
        }
        container.className = "";
        items.forEach(function (item) {
            const row = document.createElement("div");
            row.className = "evidence-item";
            row.textContent = `${item.source}: ${item.support}`;
            container.append(row);
        });
    }

    function renderModel(selector, output) {
        const container = document.querySelector(selector);
        if (!output) {
            container.className = "empty";
            container.textContent = "Waiting for sufficient interview facts.";
            return;
        }
        container.className = "model-output";
        container.innerHTML = "";
        const statusLine = document.createElement("p");
        const reasoningLine = document.createElement("p");
        statusLine.textContent = `${output.model} \u00b7 ${output.sufficiency}`;
        reasoningLine.textContent = output.reasoning;
        container.append(statusLine, reasoningLine);
    }

    function clearClinicalOutput() {
        renderEvidence([]);
        renderModel("#slm-a", null);
        renderModel("#slm-b", null);
        document.querySelector("#kas").textContent = "\u2014";
        document.querySelector("#lcs").textContent = "\u2014";
        document.querySelector("#dcs").textContent = "\u2014";
        document.querySelector("#decision").textContent = "PENDING";
        renderAssessment({status: "PENDING", assessment_summary: null});
    }

    function renderOutput(data) {
        patientState = data.patient || patientState;
        stage.textContent = data.stage || data.status;
        renderPatient(data.patient);
        renderEvidence(data.evidence);
        renderModel("#slm-a", data.slm_a);
        renderModel("#slm-b", data.slm_b);
        renderAssessment(data);
        document.querySelector("#kas").textContent = scoreText(data.kas, 2);
        document.querySelector("#lcs").textContent = data.lcs === null || data.lcs === undefined ? "\u2014" : String(data.lcs);
        document.querySelector("#dcs").textContent = scoreText(data.dcs, 2);
        document.querySelector("#decision").textContent = data.decision || data.status;
    }

    function renderConflict(stateData) {
        interviewState = stateData;
        patientState = stateData.patient || patientState;
        renderPatient(patientState);
        stage.textContent = "CONFLICT";
        mappingCard.hidden = false;
        setAnswerVisible(false);
        mappingOriginal.textContent = `You said: “${stateData.conflict.answer}”`;
        mappingCandidates.innerHTML = "";
        stateData.conflict.candidates.forEach(function (item, index) {
            const row = document.createElement("label");
            row.className = "candidate-row";
            row.style.display = "grid";
            row.style.gridTemplateColumns = "auto 1fr auto";
            row.style.gap = "12px";
            row.style.alignItems = "center";
            row.style.padding = "12px 0";
            row.style.borderTop = "1px solid var(--line)";
            row.innerHTML = `
                <input type="checkbox" name="mapping-concept" value="${item.code}">
                <span><strong>${index + 1}. ${item.display_label}</strong><br><small>${item.canonical_term}</small></span>
                <strong>${(Number(item.score) * 100).toFixed(1)}%</strong>`;
            mappingCandidates.appendChild(row);
        });
        message.textContent = "Please confirm the medical concept before the interview continues.";
    }

    function renderInterviewState(stateData) {
        interviewState = stateData;
        patientState = stateData.patient || patientState;
        renderPatient(patientState);
        mappingCard.hidden = true;

        if (stateData.stage === "CONFLICT" && stateData.conflict) {
            renderConflict(stateData);
            return;
        }

        if (stateData.complete) {
            setAnswerVisible(false);
            stage.textContent = "INTERVIEW COMPLETE";
            question.textContent = "Interview complete. Running the clinical pipeline...";
            runPipelineFromConfirmedState();
            return;
        }

        currentField = stateData.current_field;
        question.textContent = stateData.current_question;
        stage.textContent = stateData.stage;
        setAnswerVisible(true);
        answer.value = "";
        updateInputGuidance();
        action.disabled = false;
        action.textContent = "Continue";
        answer.focus();
    }

    async function loadSharedInterviewState() {
        const response = await fetch("/api/view/state/");
        const data = await readJson(response);
        if (!response.ok) throw new Error(data.error || "Unable to load interview state.");
        renderInterviewState(data);
    }

    async function runPipelineFromConfirmedState() {
        if (!interviewState?.complete) return;
        message.textContent = "Sending the confirmed shared state to the real local pipeline...";
        try {
            const response = await fetch("/api/pipeline/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value,
                },
                body: JSON.stringify({
                    field: "run_loaded_case",
                    answer: "",
                    patient: interviewState.patient,
                }),
            });
            const data = await readJson(response);
            if (!response.ok) throw new Error(data.error || "Pipeline request failed");
            renderPipeline(data);
            message.textContent = data.status === "NEED_MORE_INFO" ? "Backend requested more information." : "Real backend result received.";
        } catch (error) {
            message.textContent = error.message;
        }
    }

    function renderPipeline(data) {
        renderOutput(data);
        if (data.status === "NEED_MORE_INFO") {
            question.textContent = data.follow_up_question;
            currentField = data.next_field;
            setAnswerVisible(true);
            answer.required = true;
            updateInputGuidance();
            answer.value = "";
            action.textContent = "Continue";
            answer.focus();
        } else {
            question.textContent = "Pipeline processing complete";
            answer.disabled = true;
            action.disabled = true;
        }
    }

    function renderScriptedState(data) {
        patientState = data.patient;
        demoStage = data.presentation_stage;
        demoLabel.textContent = data.label;
        demoNotice.textContent = data.notice;
        demoNotice.hidden = false;
        mappingCard.hidden = true;
        setAnswerVisible(false);
        renderPatient(patientState);
        clearClinicalOutput();

        if (demoStage === "initial") {
            stage.textContent = "DEMO LOADED";
            question.textContent = "Review the loaded facts, then run the scripted presentation.";
            action.textContent = data.main_action;
            action.disabled = false;
            message.textContent = "Scripted patient state loaded. No live model inference has run.";
            return;
        }

        if (demoStage === "followup") {
            stage.textContent = data.stage;
            question.textContent = data.follow_up_question;
            action.textContent = data.main_action;
            action.disabled = false;
            document.querySelector("#decision").textContent = data.status;
            message.textContent = `${data.heading}. The next click applies the fixed scripted supplemental fact; no text input is required.`;
            return;
        }

        renderOutput(data);
        question.textContent = "Scripted demonstration complete";
        action.textContent = "Scripted result displayed";
        action.disabled = true;
        message.textContent = "Fixed scripted presentation displayed. No live model inference was executed.";
    }

    async function fetchDemoState(caseId, stageName) {
        const suffix = stageName === "initial" ? "" : `stage/${stageName}/`;
        const response = await fetch(`/api/demo/${caseId}/${suffix}`);
        const data = await readJson(response);
        if (!response.ok) throw new Error(data.error || "Demo load failed");
        return data;
    }

    async function loadDemo(caseId) {
        document.querySelectorAll(".demo-button").forEach(function (button) {
            button.disabled = true;
        });
        demoMode = caseId;
        demoStage = "initial";
        message.textContent = "Loading scripted presentation...";
        try {
            const initial = await fetchDemoState(caseId, "initial");
            renderScriptedState(initial);
        } catch (error) {
            demoMode = null;
            demoStage = null;
            message.textContent = error.message;
        } finally {
            document.querySelectorAll(".demo-button").forEach(function (button) {
                button.disabled = false;
            });
        }
    }

    async function resetToLiveMode() {
        demoMode = null;
        demoStage = null;
        demoLabel.textContent = "No demonstration case loaded.";
        demoNotice.hidden = true;
        clearClinicalOutput();
        message.textContent = "Resetting shared interview state...";
        try {
            const data = await postJson("/api/view/reset/");
            renderInterviewState(data);
            message.textContent = "Live assessment mode. Main APP and /view now share this backend state.";
        } catch (error) {
            message.textContent = error.message;
        }
    }

    document.querySelectorAll(".demo-button[data-demo-id]").forEach(function (button) {
        button.addEventListener("click", function () {
            loadDemo(button.dataset.demoId);
        });
    });

    document.querySelector("#live-mode-button").addEventListener("click", resetToLiveMode);

    mappingConfirm.addEventListener("click", async function () {
        const codes = [...document.querySelectorAll('input[name="mapping-concept"]:checked')].map(el => el.value);
        if (!codes.length) {
            message.textContent = "Select at least one concept, or choose None of these.";
            return;
        }
        mappingConfirm.disabled = true;
        try {
            const data = await postJson("/api/view/confirm/", {codes});
            renderInterviewState(data);
            message.textContent = data.complete ? "Mapping confirmed. Interview complete." : "Mapping confirmed. Continuing the same backend state.";
        } catch (error) {
            message.textContent = error.message;
        } finally {
            mappingConfirm.disabled = false;
        }
    });

    mappingReject.addEventListener("click", async function () {
        try {
            const data = await postJson("/api/view/reject/");
            renderInterviewState(data);
            message.textContent = "No mapping selected. Please reword the same answer.";
        } catch (error) {
            message.textContent = error.message;
        }
    });

    form.addEventListener("submit", async function (event) {
        event.preventDefault();
        action.disabled = true;

        if (demoMode) {
            let nextStage = "final";
            if (demoMode === "GU02_UTI_INCOMPLETE" && demoStage === "initial") {
                nextStage = "followup";
            }
            try {
                const scriptedState = await fetchDemoState(demoMode, nextStage);
                renderScriptedState(scriptedState);
            } catch (error) {
                message.textContent = error.message;
            } finally {
                if (demoStage !== "final") action.disabled = false;
            }
            return;
        }

        // After the fixed interview, pipeline follow-up is still handled by the existing pipeline API.
        if (currentField === "pipeline_follow_up") {
            message.textContent = "Sending follow-up answer to the clinical pipeline...";
            try {
                const response = await fetch("/api/pipeline/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value,
                    },
                    body: JSON.stringify({
                        field: currentField,
                        answer: answer.value,
                        follow_up_answer: answer.value,
                        patient: patientState,
                    }),
                });
                const data = await readJson(response);
                if (!response.ok) throw new Error(data.error || "Pipeline request failed");
                renderPipeline(data);
                message.textContent = data.status === "NEED_MORE_INFO" ? "Backend requested more information." : "Real backend result received.";
            } catch (error) {
                message.textContent = error.message;
            } finally {
                if (!answer.disabled) action.disabled = false;
            }
            return;
        }

        message.textContent = "Updating the shared backend interview state...";
        try {
            const data = await postJson("/api/view/answer/", {answer: answer.value});
            renderInterviewState(data);
            if (data.stage === "CONFLICT") {
                message.textContent = "Top 5 candidates are shown below. Confirm before continuing.";
            } else if (!data.complete) {
                message.textContent = "Answer confirmed in shared history. Continuing to the next fixed question.";
            }
        } catch (error) {
            message.textContent = error.message;
        } finally {
            if (!answer.disabled) action.disabled = false;
        }
    });

    loadSharedInterviewState().catch(function (error) {
        message.textContent = error.message;
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialisePortal);
} else {
    initialisePortal();
}
