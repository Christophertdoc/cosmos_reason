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
    const resultOverlay = document.getElementById("resultOverlay");
    const closeResult = document.getElementById("closeResult");
    const answerText = document.getElementById("answerText");
    const latencyDisplay = document.getElementById("latencyDisplay");

    let selectedFile = null;
    let autoScrollId = null;

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
            resultOverlay.hidden = true;
        }
    }

    // --- Close result ---

    closeResult.addEventListener("click", function () {
        stopAutoScroll();
        resultOverlay.hidden = true;
    });

    // --- Stop auto-scroll on manual interaction ---

    resultOverlay.addEventListener("wheel", function () {
        stopAutoScroll();
    });

    resultOverlay.addEventListener("touchmove", function () {
        stopAutoScroll();
    });

    // --- Auto-scroll ---

    function startAutoScroll() {
        stopAutoScroll();
        var PIXELS_PER_SECOND = 80;
        var lastTime = null;

        function step(timestamp) {
            if (lastTime === null) lastTime = timestamp;
            var delta = (timestamp - lastTime) / 1000;
            lastTime = timestamp;

            var maxScroll = resultOverlay.scrollHeight - resultOverlay.clientHeight;
            if (maxScroll > 0 && resultOverlay.scrollTop < maxScroll) {
                resultOverlay.scrollTop += PIXELS_PER_SECOND * delta;
                autoScrollId = requestAnimationFrame(step);
            } else {
                autoScrollId = null;
            }
        }

        autoScrollId = requestAnimationFrame(step);
    }

    function stopAutoScroll() {
        if (autoScrollId !== null) {
            cancelAnimationFrame(autoScrollId);
            autoScrollId = null;
        }
    }

    // --- Submit ---

    promptInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            analyzeBtn.click();
        }
    });

    analyzeBtn.addEventListener("click", async function () {
        if (!validateInputs()) return;

        stopAutoScroll();
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
                answerText.classList.remove("animate-in");
                latencyDisplay.classList.remove("animate-in");
                answerText.textContent = data.answer;
                latencyDisplay.textContent = "Inference time: " + data.latency_ms + " ms";
                resultOverlay.hidden = false;
                // Force reflow then trigger animation
                void answerText.offsetWidth;
                answerText.classList.add("animate-in");
                latencyDisplay.classList.add("animate-in");
                // Start auto-scroll after entrance animation
                stopAutoScroll();
                resultOverlay.scrollTop = 0;
                setTimeout(startAutoScroll, 3000);
            } else {
                showError(promptError, data.error || "An unexpected error occurred");
                resultOverlay.hidden = true;
            }
        } catch (err) {
            showError(promptError, "Service temporarily unavailable");
            resultOverlay.hidden = true;
        } finally {
            setLoading(false);
        }
    });
})();
