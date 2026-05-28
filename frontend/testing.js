// ── Screen management ─────────────────────────────────────────────────────
// We have 4 screens: status, stage1, stage2, result
// Only one is visible at a time
// showScreen() hides all then shows the one we want

const screens = ["status-screen", "stage1-screen", "stage2-screen", "result-screen"];

function showScreen(id) {
    screens.forEach(s => document.getElementById(s).classList.add("hidden"));
    document.getElementById(id).classList.remove("hidden");
}

// ── Load test status ───────────────────────────────────────────────────────
// On page load, fetch the user's current test progress from the backend
// This tells us which stages they've already passed and what's left

async function loadStatus() {
    const res = await fetchWithAuth("/api/test/status");
    const data = await res.json();

    const statusEl = document.getElementById("test-status");
    const buttonsEl = document.getElementById("stage-buttons");

    if (!data.unlocked) {
        // Testing is locked — show the unlock message from the backend
        statusEl.innerHTML = `<p class="test-locked">${data.message}</p>`;
        buttonsEl.innerHTML = "";
        return;
    }

    // Show which stages are done and their scores
    // data.stages looks like: { 1: {score: 85, passed: true}, 2: {score: 60, passed: false} }
    let statusHTML = `<p><strong>Level:</strong> ${data.level}</p>`;
    data.required_stages.forEach(stage => {
        const result = data.stages[stage];
        if (result) {
            const icon = result.passed ? "Pass" : "Fail";
            statusHTML += `<p>Stage ${stage}: ${icon} (${result.score}/100)</p>`;
        } else {
            statusHTML += `<p>Stage ${stage}: Not attempted</p>`;
        }
    });

    if (data.all_passed) {
        statusHTML += `<p class="test-passed">All stages passed! You are ready for the next level.</p>`;
    }

    statusEl.innerHTML = statusHTML;

    // Show a button for each required stage
    // Each button starts that stage's test
    buttonsEl.innerHTML = "";
    data.required_stages.forEach(stage => {
        const result = data.stages[stage];
        const btn = document.createElement("button");
        btn.className = "stage-btn";
        btn.textContent = result?.passed
            ? `Retake Stage ${stage}`
            : `Start Stage ${stage}`;
        btn.onclick = () => startStage(stage);
        buttonsEl.appendChild(btn);
    });
}

// ── Start a stage ──────────────────────────────────────────────────────────
// Fetch questions for the chosen stage from the backend
// Then render the appropriate screen

async function startStage(stage) {
    const res = await fetchWithAuth(`/api/test?stage=${stage}`);
    const data = await res.json();

    if (!data.unlocked) {
        alert(data.message);
        return;
    }

    if (stage === 1) {
        renderStage1(data.questions);
        showScreen("stage1-screen");
    } else if (stage === 2) {
        renderStage2(data.questions);
        showScreen("stage2-screen");
    }
}

// ── Stage 1: Multiple choice ───────────────────────────────────────────────
// For each question, show the English word and 4 radio button options
// The user picks one per question
// We store the correct answer in a data attribute so we can self-grade

function renderStage1(questions) {
    const container = document.getElementById("stage1-questions");
    container.innerHTML = "";

    questions.forEach((q, i) => {
        const div = document.createElement("div");
        div.className = "test-question";
        div.innerHTML = `<p><strong>${i + 1}. ${q.english}</strong></p>`;

        // Render 4 radio button options
        q.options.forEach(option => {
            const label = document.createElement("label");
            label.className = "test-option";
            label.innerHTML = `
                <input type="radio" name="q${i}" value="${option}"
                    data-correct="${q.correct}"
                    data-vocab-id="${q.vocabulary_id}">
                ${option}
            `;
            div.appendChild(label);
        });

        container.appendChild(div);
    });
}

// When user submits stage 1, collect their answers and send to backend
document.getElementById("stage1-submit").addEventListener("click", async () => {
    const radios = document.querySelectorAll("#stage1-questions input[type=radio]:checked");

    if (radios.length === 0) {
        alert("Please answer at least one question.");
        return;
    }

    // Build the answers array from the selected radio buttons
    const answers = Array.from(radios).map(radio => ({
        vocabulary_id: parseInt(radio.dataset.vocabId),
        selected: radio.value,
    }));

    await submitStage(1, answers);
});

// ── Stage 2: Translation ───────────────────────────────────────────────────
// For each question, show the English word and a text input
// The user types their French translation

function renderStage2(questions) {
    const container = document.getElementById("stage2-questions");
    container.innerHTML = "";

    questions.forEach((q, i) => {
        const div = document.createElement("div");
        div.className = "test-question";
        // Show the example sentence as a hint — helps them remember context
        div.innerHTML = `
            <p><strong>${i + 1}. ${q.english}</strong></p>
            <p class="test-hint">Hint: ${q.example_sentence}</p>
            <input type="text"
                class="test-input"
                placeholder="Type in French..."
                data-vocab-id="${q.vocabulary_id}">
        `;
        container.appendChild(div);
    });
}

document.getElementById("stage2-submit").addEventListener("click", async () => {
    const inputs = document.querySelectorAll("#stage2-questions .test-input");

    const answers = Array.from(inputs).map(input => ({
        vocabulary_id: parseInt(input.dataset.vocabId),
        typed: input.value.trim(),
    }));

    await submitStage(2, answers);
});

// ── Submit answers to backend ──────────────────────────────────────────────
// Both stages use this same function — only the answers format differs
// The backend knows which stage by the `stage` parameter

async function submitStage(stage, answers) {
    // Show loading state while backend grades
    showScreen("result-screen");
    document.getElementById("result-content").innerHTML = "<p>Grading...</p>";

    const formData = new FormData();
    formData.append("stage", stage);
    formData.append("answers", JSON.stringify(answers));

    const res = await fetchWithAuth("/api/test/submit", {
        method: "POST",
        body: formData,
    });
    const data = await res.json();

    // Show the result
    const resultEl = document.getElementById("result-content");
    const passText = data.passed ? "PASSED" : "FAILED";
    resultEl.innerHTML = `
        <p class="result-score">${data.score} / 100</p>
        <p class="result-verdict ${data.passed ? 'passed' : 'failed'}">${passText}</p>
        <p>Pass threshold: ${data.pass_threshold}</p>
        ${data.passed
            ? "<p>Well done! Move on to the next stage or check your overall progress.</p>"
            : "<p>Keep practicing in Lessons, then try again.</p>"
        }
    `;
}

// ── Back button ────────────────────────────────────────────────────────────

document.getElementById("back-to-status").addEventListener("click", () => {
    showScreen("status-screen");
    loadStatus();   // refresh status in case a stage was just passed
});

// ── Start ─────────────────────────────────────────────────────────────────

loadStatus();
