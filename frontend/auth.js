document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");
    const API_BASE = "http://127.0.0.1:8010";

    if (registerForm) {
        registerForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const user = {
                name: document.getElementById("fullName").value.trim(),
                email: document.getElementById("email").value.trim(),
                phone: document.getElementById("phone").value.trim(),
                password: document.getElementById("password").value
            };
            const confirmPassword = document.getElementById("confirmPassword").value;

            if (!validateUser(user, confirmPassword)) {
                return;
            }

            try {
                const response = await fetch(`${API_BASE}/auth/register`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(user)
                });
                const result = await response.json();

                if (!response.ok) {
                    alert(result.detail || "Registration failed.");
                    return;
                }

                alert("Registration successful. Please login now.");
                window.location.href = "login.html";
            } catch (error) {
                console.error("Registration error:", error);
                alert("Backend server is offline.");
            }
        });
    }

    if (loginForm) {
        loginForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const email = document.getElementById("email").value.trim();
            const password = document.getElementById("password").value;

            if (!isValidEmail(email) || !password) {
                alert("Enter a valid email and password.");
                return;
            }

            try {
                const response = await fetch(`${API_BASE}/auth/login`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email, password })
                });
                const result = await response.json();

                if (!response.ok) {
                    alert(result.detail || "Login failed.");
                    return;
                }

                localStorage.setItem("civicAuthToken", result.token);
                localStorage.setItem("civicUser", JSON.stringify(result.user));
                alert(`Welcome back, ${result.user.name}.`);
                window.location.href = "user.html";
            } catch (error) {
                console.error("Login error:", error);
                alert("Backend server is offline.");
            }
        });
    }

    function validateUser(user, confirmPassword) {
        if (user.name.length < 2) {
            alert("Name must be at least 2 characters.");
            return false;
        }
        if (!isValidEmail(user.email)) {
            alert("Enter a valid email address.");
            return false;
        }
        if (!/^[0-9+\-\s]{10,15}$/.test(user.phone)) {
            alert("Enter a valid phone number.");
            return false;
        }
        if (user.password.length < 6) {
            alert("Password must be at least 6 characters.");
            return false;
        }
        if (user.password !== confirmPassword) {
            alert("Passwords do not match.");
            return false;
        }
        return true;
    }

    function isValidEmail(email) {
        return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email);
    }
});
