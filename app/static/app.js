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
    let activeAbortController = null;

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
        if (activeAbortController) {
            activeAbortController.abort();
            activeAbortController = null;
        }
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

        // Abort any previous stream
        if (activeAbortController) {
            activeAbortController.abort();
        }
        activeAbortController = new AbortController();

        try {
            const response = await fetch("/api/analyze/stream", {
                method: "POST",
                body: formData,
                signal: activeAbortController.signal,
            });

            if (!response.ok) {
                const data = await response.json();
                showError(promptError, data.error || "An unexpected error occurred");
                resultOverlay.hidden = true;
                setLoading(false);
                return;
            }

            // Prepare overlay for streaming
            answerText.classList.remove("animate-in");
            latencyDisplay.classList.remove("animate-in");
            answerText.innerHTML = "";
            latencyDisplay.textContent = "";
            answerText.style.opacity = "1";
            latencyDisplay.style.opacity = "";
            resultOverlay.scrollTop = 0;
            let receivedFirstToken = false;

            // Phase blocks — created on demand when that phase starts
            let thinkBlock = null;
            let contentBlock = null;

            function ensureThinkBlock() {
                if (thinkBlock) return;
                var label = document.createElement("div");
                label.className = "phase-label reasoning";
                label.textContent = "Reasoning";
                answerText.appendChild(label);
                thinkBlock = document.createElement("div");
                thinkBlock.className = "reason-block";
                answerText.appendChild(thinkBlock);
            }

            function ensureContentBlock() {
                if (contentBlock) return;
                var label = document.createElement("div");
                label.className = "phase-label concluding";
                label.textContent = "Answer";
                answerText.appendChild(label);
                contentBlock = document.createElement("div");
                contentBlock.className = "conclude-block";
                answerText.appendChild(contentBlock);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop();

                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed || !trimmed.startsWith("data:")) continue;
                    const dataStr = trimmed.slice(5).trim();
                    if (!dataStr) continue;

                    let parsed;
                    try {
                        parsed = JSON.parse(dataStr);
                    } catch {
                        continue;
                    }

                    if (parsed.error) {
                        showError(promptError, parsed.error);
                        resultOverlay.hidden = true;
                        setLoading(false);
                        return;
                    }

                    if (parsed.token) {
                        if (!receivedFirstToken) {
                            receivedFirstToken = true;
                            resultOverlay.hidden = false;
                            loadingIndicator.hidden = true;
                        }

                        if (parsed.type === "thinking") {
                            ensureThinkBlock();
                            thinkBlock.textContent += parsed.token;
                        } else {
                            // "content" type, or fallback
                            ensureContentBlock();
                            contentBlock.textContent += parsed.token;
                        }
                    }

                    if (parsed.done) {
                        latencyDisplay.textContent = "Inference time: " + parsed.latency_ms + " ms";
                        latencyDisplay.style.opacity = "1";
                        stopAutoScroll();
                        startAutoScroll();
                    }
                }
            }
        } catch (err) {
            if (err.name === "AbortError") return;
            showError(promptError, "Service temporarily unavailable");
            resultOverlay.hidden = true;
        } finally {
            activeAbortController = null;
            setLoading(false);
        }
    });
})();
