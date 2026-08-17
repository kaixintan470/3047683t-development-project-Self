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
    const optionalFields = new Set(["medical_history", "allergies", "medications"]);
    let currentField = "chief_complaint";
    let patientState = {};
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

    function resetToLiveMode() {
        demoMode = null;
        demoStage = null;
        currentField = "chief_complaint";
        patientState = {};
        demoLabel.textContent = "No demonstration case loaded.";
        demoNotice.hidden = true;
        stage.textContent = "INTERVIEW";
        question.textContent = "What is the main health problem you would like help with?";
        setAnswerVisible(true);
        answer.value = "";
        answer.required = true;
        action.disabled = false;
        action.textContent = "Continue";
        clearClinicalOutput();
        renderPatient({});
        message.textContent = "Live assessment mode. Submissions use the canonical clinical pipeline.";
    }

    document.querySelectorAll(".demo-button[data-demo-id]").forEach(function (button) {
        button.addEventListener("click", function () {
            loadDemo(button.dataset.demoId);
        });
    });

    document.querySelector("#live-mode-button").addEventListener("click", resetToLiveMode);

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

        message.textContent = "Sending confirmed facts to the real local pipeline...";
        const payload = {field: currentField, answer: answer.value, patient: patientState};
        if (currentField === "pipeline_follow_up") {
            payload.follow_up_answer = answer.value;
        }
        try {
            const response = await fetch("/api/pipeline/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value,
                },
                body: JSON.stringify(payload),
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
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialisePortal);
} else {
    initialisePortal();
}
