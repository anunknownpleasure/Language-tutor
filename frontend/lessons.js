// ── State ─────────────────────────────────────────────────────────────────

let words = [];
let currentWordIndex = 0;
let history = [];
let isWaiting = false;

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

// ── DOM refs ──────────────────────────────────────────────────────────────

const chatEl      = document.getElementById("lesson-chat");
const inputEl     = document.getElementById("lesson-input");
const sendBtn     = document.getElementById("lesson-send");
const micBtn      = document.getElementById("lesson-mic");
const wordLabelEl = document.getElementById("word-label");
const scoreEl     = document.getElementById("word-score");
const attemptsEl  = document.getElementById("word-attempts");
const progressEl  = document.getElementById("lesson-progress");
const patternEl   = document.getElementById("lesson-pattern");
const patternFrEl = document.getElementById("pattern-fr");
const patternEnEl = document.getElementById("pattern-en");
const audioEl     = document.getElementById("sophie-audio");

// ── Boot ──────────────────────────────────────────────────────────────────

async function loadLesson() {
    const res = await fetchWithAuth("/api/lessons");
    const data = await res.json();

    words = data.words;
    updateProgress(data.lessons_completed);

    // Show the lesson's MT pattern card
    if (data.pattern) {
        patternFrEl.textContent = data.pattern.pattern_fr;
        patternEnEl.textContent = data.pattern.pattern_en;
        patternEl.classList.remove("hidden");
    }

    startWord(0);
}

function startWord(index) {
    currentWordIndex = index;
    history = [];

    const word = words[index];
    updateWordHeader(word);
    chatEl.innerHTML = "";

    // "start" is a hidden trigger — tells Sophie to give the pattern intro
    sendInput("start", null);
}

// ── Voice recording ───────────────────────────────────────────────────────
// Push-to-talk: hold the mic button, release to send.

async function startRecording() {
    if (isWaiting || isRecording) return;

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = e => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = async () => {
            // Stop all mic tracks so the browser releases the microphone
            stream.getTracks().forEach(t => t.stop());
            const blob = new Blob(audioChunks, { type: "audio/webm" });
            await sendInput(null, blob);
        };

        mediaRecorder.start();
        isRecording = true;
        micBtn.textContent = "🔴 Recording...";
        micBtn.classList.add("recording");

    } catch (err) {
        console.error("Microphone error:", err);
        appendStatus("Could not access microphone. Try typing instead.");
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        micBtn.textContent = "🎤 Hold to speak";
        micBtn.classList.remove("recording");
    }
}

// ── Core send function ────────────────────────────────────────────────────
// Handles both text and audio — the backend decides how to process each.

async function sendInput(text, audioBlob) {
    if (isWaiting) return;

    const word = words[currentWordIndex];

    // Show what the user is sending (skip the hidden "start" trigger)
    if (text && text !== "start") {
        appendMessage("You", text);
    } else if (audioBlob) {
        // Placeholder — will be updated with the transcript once the server responds
        appendMessage("You", "🎤 ...");
    }

    isWaiting = true;
    setControlsEnabled(false);

    // Build FormData — works for both text and audio
    const formData = new FormData();
    formData.append("vocabulary_id", word.id);
    formData.append("history", JSON.stringify(history));

    if (audioBlob) {
        formData.append("audio", audioBlob, "recording.webm");
    } else {
        formData.append("message", text || "");
    }

    let res;
    try {
        res = await fetchWithAuth("/api/lessons/respond", { method: "POST", body: formData });
    } catch (networkErr) {
        appendStatus("Network error — check your connection and try again.");
        isWaiting = false;
        setControlsEnabled(true);
        return;
    }

    if (!res.ok) {
        appendStatus(`Server error (${res.status}) — please try again.`);
        isWaiting = false;
        setControlsEnabled(true);
        return;
    }

    let data;
    try {
        data = await res.json();
    } catch (parseErr) {
        appendStatus("Unexpected response from server — please try again.");
        isWaiting = false;
        setControlsEnabled(true);
        return;
    }

    // Backend sent an error message (LLM/TTS failed gracefully)
    if (data.error) {
        appendStatus(`Error: ${data.error}`);
        isWaiting = false;
        setControlsEnabled(true);
        return;
    }

    // If mic was used, update the placeholder with the actual transcript
    if (data.transcribed && audioBlob) {
        const placeholders = chatEl.querySelectorAll(".lesson-message.user .lesson-content");
        const last = placeholders[placeholders.length - 1];
        if (last) last.textContent = `"${data.transcribed}"`;
    }

    // Update conversation history for the next LLM call
    const userContent = text !== "start" ? (text || data.transcribed || "") : null;
    if (userContent) history.push({ role: "user", content: userContent });
    history.push({ role: "assistant", content: data.message });

    // Show Sophie's text reply
    appendMessage("Sophie", data.message);

    // Play Sophie's spoken reply (may be null if TTS failed — degrade gracefully)
    if (data.audio_base64) {
        playAudio(data.audio_base64);
    }

    // Update score display if an attempt was scored
    if (data.attempt_score !== null) {
        word.score = data.new_score;
        word.attempt_count = data.attempt_count;
        updateWordHeader(word);
    }

    // Word learned — move to next word after a short pause
    if (data.word_learned) {
        appendStatus("Learned! Moving to next word...");
        setTimeout(() => moveToNextWord(), 2000);
        return;   // don't re-enable controls — we're transitioning
    }

    // All words in lesson learned
    if (data.lesson_complete) {
        appendStatus("Lesson complete! Well done.");
        return;   // leave controls disabled
    }

    isWaiting = false;
    setControlsEnabled(true);
    inputEl.focus();
}

function moveToNextWord() {
    const nextIndex = currentWordIndex + 1;
    if (nextIndex < words.length) {
        startWord(nextIndex);
    } else {
        chatEl.innerHTML = "";
        appendStatus("You have practiced all words in this lesson!");
    }
}

// ── Audio playback ────────────────────────────────────────────────────────

function playAudio(base64) {
    audioEl.src = `data:audio/mpeg;base64,${base64}`;
    audioEl.play().catch(err => console.warn("Audio playback blocked:", err));
}

// ── UI helpers ────────────────────────────────────────────────────────────

function appendMessage(sender, text) {
    const div = document.createElement("div");
    div.className = `lesson-message ${sender === "You" ? "user" : "sophie"}`;

    const label = document.createElement("span");
    label.className = "lesson-label";
    label.textContent = sender;

    const content = document.createElement("span");
    content.className = "lesson-content";
    content.textContent = text;

    div.appendChild(label);
    div.appendChild(content);
    chatEl.appendChild(div);
    chatEl.scrollTop = chatEl.scrollHeight;
}

function appendStatus(text) {
    const div = document.createElement("div");
    div.className = "lesson-status";
    div.textContent = text;
    chatEl.appendChild(div);
    chatEl.scrollTop = chatEl.scrollHeight;
}

function updateWordHeader(word) {
    wordLabelEl.textContent = `${word.word_fr} — ${word.word_en}`;
    scoreEl.textContent = `Score: ${Math.round(word.score)}`;
    attemptsEl.textContent = `Attempts: ${word.attempt_count}`;
}

function updateProgress(lessonsCompleted) {
    progressEl.textContent = `Lessons completed: ${lessonsCompleted} / 10`;
}

function setControlsEnabled(enabled) {
    sendBtn.disabled = !enabled;
    inputEl.disabled = !enabled;
    micBtn.disabled = !enabled;
}

// ── Event listeners ───────────────────────────────────────────────────────

// Mic: push-to-talk (mousedown/mouseup for desktop, touchstart/touchend for mobile)
micBtn.addEventListener("mousedown",  startRecording);
micBtn.addEventListener("mouseup",    stopRecording);
micBtn.addEventListener("mouseleave", stopRecording);   // release if cursor drifts off
micBtn.addEventListener("touchstart", e => { e.preventDefault(); startRecording(); });
micBtn.addEventListener("touchend",   stopRecording);

// Text send button
sendBtn.addEventListener("click", () => {
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = "";
    sendInput(text, null);
});

// Enter key in text box
inputEl.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendBtn.click();
    }
});

// ── Start ─────────────────────────────────────────────────────────────────

loadLesson();
