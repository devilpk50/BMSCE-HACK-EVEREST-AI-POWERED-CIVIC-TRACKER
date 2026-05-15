function getSavedUser() {
    try {
        return JSON.parse(localStorage.getItem("civicUser") || "null");
    } catch (error) {
        localStorage.removeItem("civicUser");
        return null;
    }
}

function applySessionState() {
    const token = localStorage.getItem("civicAuthToken");
    const user = getSavedUser();
    const isLoggedIn = Boolean(token && user);
    const protectedPage = document.body.dataset.protected === "true";
    const authPage = document.body.dataset.authPage === "true";

    document.querySelectorAll("[data-auth-only]").forEach((element) => {
        element.hidden = !isLoggedIn;
    });

    document.querySelectorAll("[data-guest-only]").forEach((element) => {
        element.hidden = isLoggedIn;
    });

    document.querySelectorAll("[data-user-name]").forEach((element) => {
        element.textContent = user ? user.name : "Citizen";
    });

    if (protectedPage && !isLoggedIn) {
        window.location.replace("login.html");
        return;
    }

    if (authPage && isLoggedIn) {
        window.location.replace("user.html");
    }
}

function logoutUser(event) {
    if (event) {
        event.preventDefault();
    }

    localStorage.removeItem("civicAuthToken");
    localStorage.removeItem("civicUser");
    applySessionState();
    window.location.replace("login.html");
}

function initSession() {
    applySessionState();

    document.querySelectorAll("[data-logout]").forEach((button) => {
        button.addEventListener("click", logoutUser);
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSession);
} else {
    initSession();
}
