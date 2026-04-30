let mediaRecorder = null;
let audioChunks = [];
let conversationHistory = [];
let isProcessing = false;

const micBtn = document.getElementById("mic-btn");
const statusEl = document.getElementById("status");
const conversationEl = document.getElementById("conversation");
const correctionBox = document.getElementById("correction-box");
const correctionText = document.getElementById("correction-text");

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

async function sendAudio() {
    isProcessing = true;
    micBtn.disabled = true;
    micBtn.classList.remove("recording");
    statusEl.textContent = "Thinking...";

    const blob = new Blob(audioChunks, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("audio", blob, "audio.webm");
    formData.append("history", JSON.stringify(conversationHistory));

    try {
        const res = await fetch("/api/chat", { method: "POST", body: formData });
        const data = await res.json();

        conversationHistory.push({ role: "user", content: data.transcript });
        conversationHistory.push({ role: "assistant", content: data.response_fr });

        addMessage("user", data.transcript, "");
        addMessage("sophie", data.response_fr, data.response_en);

        if (data.correction) {
            correctionBox.classList.remove("hidden");
            correctionText.textContent = data.correction;
        } else {
            correctionBox.classList.add("hidden");
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

function playAudio(base64) {
    const bytes = atob(base64);
    const buffer = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) {
        buffer[i] = bytes.charCodeAt(i);
    }
    const blob = new Blob([buffer], { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play();
}
