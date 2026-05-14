// submission_form.js

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("submissionForm");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        // Get form values
        const name = document.getElementById("name").value;
        const description = document.getElementById("description").value;
        const imageInput = document.getElementById("image");

        // Check image selected
        if (imageInput.files.length === 0) {
            alert("Please select an image.");
            return;
        }

        const imageFile = imageInput.files[0];

        // Get Geolocation
        if (!navigator.geolocation) {
            alert("Geolocation is not supported by your browser.");
            return;
        }

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;

                // Create FormData for upload
                const formData = new FormData();

                formData.append("name", name);
                formData.append("description", description);
                formData.append("latitude", latitude);
                formData.append("longitude", longitude);
                formData.append("image", imageFile);

                console.log("Form Data Ready:");
                console.log({
                    name,
                    description,
                    latitude,
                    longitude,
                    image: imageFile.name
                });

                try {
                    // Example upload request
                    const response = await fetch("/upload", {
                        method: "POST",
                        body: formData
                    });

                    if (response.ok) {
                        alert("Submission successful!");
                    } else {
                        alert("Upload failed.");
                    }
                } catch (error) {
                    console.error("Error:", error);
                    alert("Something went wrong.");
                }
            },
            (error) => {
                console.error("Geolocation Error:", error);
                alert("Unable to fetch location.");
            }
        );
    });
});