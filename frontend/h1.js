// submission_form.js

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("submissionForm");
    const submitBtn = form.querySelector("button[type='submit']");
    const token = localStorage.getItem("civicAuthToken");

    if (!token) {
        alert("Please login before submitting a report.");
        window.location.href = "login.html";
        return;
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        // 1. UI Feedback
        submitBtn.disabled = true;
        submitBtn.innerText = "Analyzing with AI...";

        const name = document.getElementById("name").value.trim();
        const description = document.getElementById("description").value.trim();
        const imageInput = document.getElementById("image");

        if (name.length < 2) {
            alert("Name must be at least 2 characters.");
            resetButton();
            return;
        }

        if (description.length < 10) {
            alert("Description must be at least 10 characters.");
            resetButton();
            return;
        }

        if (imageInput.files.length === 0) {
            alert("Please select an image.");
            resetButton();
            return;
        }

        const imageFile = imageInput.files[0];

        if (!imageFile.type.startsWith("image/")) {
            alert("Please upload a valid image file.");
            resetButton();
            return;
        }

        if (imageFile.size > 5 * 1024 * 1024) {
            alert("Image must be smaller than 5 MB.");
            resetButton();
            return;
        }

        if (!navigator.geolocation) {
            alert("Geolocation is not supported.");
            resetButton();
            return;
        }

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const formData = new FormData();
                formData.append("name", name);
                formData.append("description", description);
                formData.append("latitude", position.coords.latitude);
                formData.append("longitude", position.coords.longitude);
                formData.append("image", imageFile);

                try {
                    const response = await fetch("http://127.0.0.1:8010/upload", {
                        method: "POST",
                        headers: {
                            Authorization: `Bearer ${token}`
                        },
                        body: formData
                    });

                    const result = await response.json();

                    if (response.ok) {
                        alert(`Success: ${result.message}\nCategory: ${result.category}`);
                        form.reset();
                    } else {
                        // Display the specific AI rejection reason from the backend
                        alert(`Issue: ${result.detail || "Upload failed."}`);
                    }
                } catch (error) {
                    console.error("Error:", error);
                    alert("Backend server is offline.");
                } finally {
                    resetButton();
                }
            },
            (error) => {
                alert("Location access denied.");
                resetButton();
            }
        );
    });

    function resetButton() {
        submitBtn.disabled = false;
        submitBtn.innerText = "Submit Report";
    }
});
