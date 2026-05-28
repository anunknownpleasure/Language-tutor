let mediaRecorder = null;
let audioChunks = [];
let conversationHistory = [];
let currentScenario = null;
let isProcessing = false;

const scenarioScreen = document.getElementById("scenario-screen");
const conversationScreen = document.getElementById("conversation-screen");
const scenarioCards = document.getElementById("scenario-cards");
const scenarioBanner = document.getElementById("scenario-banner");
const conversationEl = document.getElementById("conversation");
const micBtn = document.getElementById("mic-btn");
const statusEl = document.getElementById("status");

// ── Scenario selection ────────────────────────────────────────────────────

async function loadScenarios() {
    scenarioCards.innerHTML = "<p>Generating scenarios...</p>";
    const res = await fetchWithAuth("/api/conversations/scenarios");
    const data = await res.json();

    scenarioCards.innerHTML = "";
    data.scenarios.forEach((scenario, i) => {
        const card = document.createElement("div");
        card.className = "scenario-card";
        card.innerHTML = `
            <h3>${scenario.title}</h3>
            <p>${scenario.description}</p>
            <p class="scenario-goal"><strong>Your goal:</strong> ${scenario.goal}</p>
            <button onclick="selectScenario(${i})">Start this scenario</button>
        `;
        scenarioCards.appendChild(card);
        // Store scenario data on the button's parent
        card.dataset.index = i;
        card._scenario = scenario;
        window[`scenario_${i}`] = scenario;
    });
}

function selectScenario(index) {
    currentScenario = window[`scenario_${index}`];
    conversationHistory = [];

    // Show conversation screen
    scenarioScreen.classList.add("hidden");
    conversationScreen.classList.remove("hidden");

    // Show scenario banner
    scenarioBanner.innerHTML = `
        <div class="scenario-banner">
            <strong>${currentScenario.title}</strong> — ${currentScenario.description}
        </div>
    `;

    // Show Sophie's opening line
    addMessage("sophie", currentScenario.opening_line, "");
    conversationHistory.push({
        role: "assistant",
        content: currentScenario.opening_line,
    });
}

document.getElementById("refresh-scenarios").addEventListener("click", loadScenarios);

document.getElementById("end-scenario").addEventListener("click", () => {
    conversationScreen.classList.add("hidden");
    scenarioScreen.classList.remove("hidden");
    currentScenario = null;
    conversationHistory = [];
    conversationEl.innerHTML = "";
});

// ── Voice recording ───────────────────────────────────────────────────────

async function startRecording() {
    if (isProcessing) return;
    audioChunks = [];
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
    mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
    mediaRecorder.onstop = sendAudio;
    mediaRecorder.start();
    micBtn.classList.add("recording");
    statusEl.textContent = "Recording... release to send";
}

function stopRecording() {
    if (!mediaRecorder || mediaRecorder.state === "inactive") return;
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach((t) => t.stop());
}

// ── Sending audio ─────────────────────────────────────────────────────────

async function sendAudio() {
    isProcessing = true;
    micBtn.disabled = true;
    micBtn.classList.remove("recording");
    statusEl.textContent = "Thinking...";

    const blob = new Blob(audioChunks, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("audio", blob, "audio.webm");
    formData.append("history", JSON.stringify(conversationHistory));
    formData.append("scenario", JSON.stringify(currentScenario));

    try {
        const res = await fetchWithAuth("/api/conversations/chat", {
            method: "POST",
            body: formData,
        });
        const data = await res.json();

        conversationHistory.push({ role: "user", content: data.transcript });
        conversationHistory.push({ role: "assistant", content: data.response_fr });

        addMessage("user", data.transcript, "");
        addMessage("sophie", data.response_fr, data.response_en);

        if (data.correction) {
            addCorrection(data.correction);
        }

        playAudio(data.audio_base64);
        statusEl.textContent = "Press and hold the button to speak in French";
    } catch (err) {
        statusEl.textContent = "Something went wrong. Try again.";
        console.error(err);
    } finally {
        isProcessing = false;
        micBtn.disabled = false;
    }
}

// ── UI helpers ────────────────────────────────────────────────────────────

function addMessage(role, french, english) {
    const div = document.createElement("div");
    div.className = `message ${role}`;

    const label = document.createElement("span");
    label.className = "label";
    label.textContent = role === "user" ? "You" : "Sophie";

    const frenchEl = document.createElement("span");
    frenchEl.className = "french";
    frenchEl.textContent = french;

    div.appendChild(label);
    div.appendChild(frenchEl);

    if (english) {
        const englishEl = document.createElement("span");
        englishEl.className = "english";
        englishEl.textContent = english;
        div.appendChild(englishEl);
    }

    conversationEl.appendChild(div);
    conversationEl.scrollTop = conversationEl.scrollHeight;
}

function addCorrection(text) {
    const div = document.createElement("div");
    div.className = "correction-inline";
    div.textContent = "Correction: " + text;
    conversationEl.appendChild(div);
    conversationEl.scrollTop = conversationEl.scrollHeight;
}

function playAudio(base64) {
    const bytes = atob(base64);
    const buffer = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) buffer[i] = bytes.charCodeAt(i);
    const blob = new Blob([buffer], { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    new Audio(url).play();
}

// ── Start ─────────────────────────────────────────────────────────────────

loadScenarios();
