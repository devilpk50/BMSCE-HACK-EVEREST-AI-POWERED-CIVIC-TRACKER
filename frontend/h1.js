// submission_form.js

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("submissionForm");
    const submitBtn = form.querySelector("button[type='submit']");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        // 1. UI Feedback
        submitBtn.disabled = true;
        submitBtn.innerText = "Analyzing with AI...";

        const name = document.getElementById("name").value;
        const description = document.getElementById("description").value;
        const imageInput = document.getElementById("image");

        if (imageInput.files.length === 0) {
            alert("Please select an image.");
            resetButton();
            return;
        }

        const imageFile = imageInput.files[0];

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
                    const response = await fetch("http://127.0.0.1:8000/upload", {
                        method: "POST",
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
