(function () {
    "use strict";

    const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
    const MAX_FILE_SIZE = 8 * 1024 * 1024; // 8 MB
    const MAX_PROMPT_LENGTH = 2000;

    const uploadZone = document.getElementById("uploadZone");
    const fileInput = document.getElementById("fileInput");
    const imagePreview = document.getElementById("imagePreview");
    const uploadPlaceholder = document.getElementById("uploadPlaceholder");
    const imageError = document.getElementById("imageError");
    const promptInput = document.getElementById("promptInput");
    const promptError = document.getElementById("promptError");
    const analyzeBtn = document.getElementById("analyzeBtn");
    const loadingIndicator = document.getElementById("loadingIndicator");
    const resultArea = document.getElementById("resultArea");
    const answerText = document.getElementById("answerText");
    const latencyDisplay = document.getElementById("latencyDisplay");
    const errorArea = document.getElementById("errorArea");
    const errorText = document.getElementById("errorText");

    let selectedFile = null;

    // --- Upload Zone: click and drag-and-drop ---

    uploadZone.addEventListener("click", function () {
        fileInput.click();
    });

    fileInput.addEventListener("change", function () {
        if (fileInput.files.length > 0) {
            handleFileSelection(fileInput.files[0]);
        }
    });

    uploadZone.addEventListener("dragover", function (e) {
        e.preventDefault();
        uploadZone.classList.add("dragover");
    });

    uploadZone.addEventListener("dragleave", function () {
        uploadZone.classList.remove("dragover");
    });

    uploadZone.addEventListener("drop", function (e) {
        e.preventDefault();
        uploadZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFileSelection(e.dataTransfer.files[0]);
        }
    });

    function handleFileSelection(file) {
        clearErrors();

        if (!ALLOWED_TYPES.includes(file.type)) {
            showError(imageError, "Unsupported file type. Please use JPEG, PNG, or WebP");
            selectedFile = null;
            hidePreview();
            return;
        }

        if (file.size > MAX_FILE_SIZE) {
            showError(imageError, "File size exceeds the 8 MB limit");
            selectedFile = null;
            hidePreview();
            return;
        }

        selectedFile = file;
        showPreview(file);
    }

    function showPreview(file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            imagePreview.src = e.target.result;
            imagePreview.hidden = false;
            uploadPlaceholder.hidden = true;
        };
        reader.readAsDataURL(file);
    }

    function hidePreview() {
        imagePreview.hidden = true;
        imagePreview.src = "";
        uploadPlaceholder.hidden = false;
    }

    // --- Validation ---

    function validateInputs() {
        let valid = true;
        clearErrors();

        if (!selectedFile) {
            showError(imageError, "Please upload an image");
            valid = false;
        }

        const prompt = promptInput.value.trim();
        if (!prompt) {
            showError(promptError, "Please enter a prompt");
            valid = false;
        } else if (prompt.length > MAX_PROMPT_LENGTH) {
            showError(promptError, "Prompt exceeds maximum length of " + MAX_PROMPT_LENGTH + " characters");
            valid = false;
        }

        return valid;
    }

    function showError(element, message) {
        element.textContent = message;
    }

    function clearErrors() {
        imageError.textContent = "";
        promptError.textContent = "";
    }

    // --- Loading State ---

    function setLoading(loading) {
        analyzeBtn.disabled = loading;
        loadingIndicator.hidden = !loading;
        if (loading) {
            resultArea.hidden = true;
            errorArea.hidden = true;
        }
    }

    // --- Submit ---

    analyzeBtn.addEventListener("click", async function () {
        if (!validateInputs()) return;

        setLoading(true);

        const formData = new FormData();
        formData.append("image", selectedFile);
        formData.append("prompt", promptInput.value.trim());

        try {
            const response = await fetch("/api/analyze", {
                method: "POST",
                body: formData,
            });

            const data = await response.json();

            if (response.ok) {
                answerText.textContent = data.answer;
                latencyDisplay.textContent = "Latency: " + data.latency_ms + " ms";
                resultArea.hidden = false;
                errorArea.hidden = true;
            } else {
                errorText.textContent = data.error || "An unexpected error occurred";
                errorArea.hidden = false;
                resultArea.hidden = true;
            }
        } catch (err) {
            errorText.textContent = "Service temporarily unavailable";
            errorArea.hidden = false;
            resultArea.hidden = true;
        } finally {
            setLoading(false);
        }
    });
})();
