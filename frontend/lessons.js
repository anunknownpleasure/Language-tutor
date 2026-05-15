let words = [];
let currentWordIndex = 0;
let history = [];
let isWaiting = false;

const chatEl = document.getElementById("lesson-chat");
const inputEl = document.getElementById("lesson-input");
const sendBtn = document.getElementById("lesson-send");
const wordLabelEl = document.getElementById("word-label");
const scoreEl = document.getElementById("word-score");
const attemptsEl = document.getElementById("word-attempts");
const progressEl = document.getElementById("lesson-progress");

// ── Boot ──────────────────────────────────────────────────────────────────

async function loadLesson() {
    const res = await fetch("/api/lessons");
    const data = await res.json();
    words = data.words;
    updateProgressBar(data.lessons_completed);
    startWord(0);
}

function startWord(index) {
    currentWordIndex = index;
    history = [];

    const word = words[index];
    updateWordHeader(word);
    chatEl.innerHTML = "";

    // Send a "start" message to trigger Sophie's introduction
    sendMessage("start");
}

// ── Sending messages ──────────────────────────────────────────────────────

async function sendMessage(userText) {
    if (isWaiting) return;

    // Don't show "start" in the chat — it's a hidden trigger
    if (userText !== "start") {
        appendMessage("You", userText);
    }

    isWaiting = true;
    sendBtn.disabled = true;
    inputEl.disabled = true;

    const word = words[currentWordIndex];

    const res = await fetch("/api/lessons/respond", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            vocabulary_id: word.id,
            message: userText,
            history: history,
        }),
    });

    const data = await res.json();

    // Update conversation history
    if (userText !== "start") {
        history.push({ role: "user", content: userText });
    }
    history.push({ role: "assistant", content: data.message });

    // Show Sophie's response
    appendMessage("Sophie", data.message);

    // Update score display if an attempt was scored
    if (data.attempt_score !== null) {
        word.score = data.new_score;
        word.attempt_count = data.attempt_count;
        updateWordHeader(word);
    }

    // Word learned — move to next word after a short pause
    if (data.word_learned) {
        appendStatus(`Learned! Moving to next word...`);
        setTimeout(() => moveToNextWord(), 2000);
    }

    // All words in lesson learned
    if (data.lesson_complete) {
        appendStatus("Lesson complete! Well done.");
        sendBtn.disabled = true;
        inputEl.disabled = true;
        return;
    }

    isWaiting = false;
    sendBtn.disabled = false;
    inputEl.disabled = false;
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

function updateProgressBar(lessonsCompleted) {
    progressEl.textContent = `Lessons completed: ${lessonsCompleted} / 10`;
}

// ── Event listeners ───────────────────────────────────────────────────────

sendBtn.addEventListener("click", () => {
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = "";
    sendMessage(text);
});

inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendBtn.click();
    }
});

// ── Start ─────────────────────────────────────────────────────────────────

loadLesson();
