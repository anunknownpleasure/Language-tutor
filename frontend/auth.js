/**
 * auth.js — shared auth utilities used on every page.
 *
 * What this file does and why each piece exists:
 *
 * 1. Token storage  — the JWT returned by /api/auth/login is kept in
 *    localStorage so it survives page refreshes and tab closures.
 *
 * 2. fetchWithAuth  — every protected API call needs an Authorization header.
 *    Wrapping fetch() here means individual pages never have to remember
 *    to add the header themselves.
 *
 * 3. requireAuth    — any page that requires a login calls this on load.
 *    If there is no token, the user is immediately redirected to login.html.
 *
 * 4. initNav        — updates the top navigation bar to show the user's email
 *    and a logout button once they are logged in.
 */

// ── Token helpers ──────────────────────────────────────────────────────────

function getToken() {
    return localStorage.getItem("token");
}

function getEmail() {
    return localStorage.getItem("email");
}

function setAuth(token, email) {
    localStorage.setItem("token", token);
    localStorage.setItem("email", email);
}

function removeAuth() {
    localStorage.removeItem("token");
    localStorage.removeItem("email");
}

// ── Authenticated fetch ────────────────────────────────────────────────────
// Drop-in replacement for fetch() that injects the Bearer token.
// Usage:  const res = await fetchWithAuth("/api/lessons");

async function fetchWithAuth(url, options = {}) {
    const token = getToken();
    const headers = { ...(options.headers || {}) };

    // Only add Authorization if we have a token.
    // Don't set Content-Type for FormData — the browser sets it with the boundary.
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(url, { ...options, headers });

    // If the server returns 401, the token is invalid/expired — force re-login.
    if (res.status === 401) {
        removeAuth();
        window.location.href = "/login.html";
        return res;  // unreachable in practice, but keeps the caller's try/catch happy
    }

    return res;
}

// ── Page guard ────────────────────────────────────────────────────────────
// Call requireAuth() at the top of any JS file for a protected page.
// If the user has no token, they are sent to login.html immediately.

function requireAuth() {
    if (!getToken()) {
        window.location.href = "/login.html";
    }
}

// ── Logout ────────────────────────────────────────────────────────────────

function logout() {
    removeAuth();
    window.location.href = "/login.html";
}

// ── Navigation ────────────────────────────────────────────────────────────
// Injects the user's email and a logout button into the nav bar.
// Each HTML page has a <span id="nav-user"></span> placeholder in its nav.

function initNav() {
    const userEl = document.getElementById("nav-user");
    if (!userEl) return;   // page has no nav (e.g. login/register)

    const email = getEmail();
    if (email) {
        userEl.innerHTML = `
            <span class="nav-email">${email}</span>
            <button class="nav-logout-btn" onclick="logout()">Logout</button>
        `;
    }
}
