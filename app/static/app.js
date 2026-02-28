(function () {
    "use strict";

    const ALLOWED_TYPES = ["video/mp4", "video/webm", "video/quicktime"];
    const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB
    const MAX_PROMPT_LENGTH = 2000;

    const uploadZone = document.getElementById("uploadZone");
    const fileInput = document.getElementById("fileInput");
    const videoPreview = document.getElementById("videoPreview");
    const uploadPlaceholder = document.getElementById("uploadPlaceholder");
    const videoError = document.getElementById("videoError");
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
    let previewObjectUrl = null;

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
            showError(videoError, "Unsupported file type. Please use MP4, WebM, or MOV");
            selectedFile = null;
            hidePreview();
            return;
        }

        if (file.size > MAX_FILE_SIZE) {
            showError(videoError, "File size exceeds the 50 MB limit");
            selectedFile = null;
            hidePreview();
            return;
        }

        selectedFile = file;
        showPreview(file);
    }

    function showPreview(file) {
        if (previewObjectUrl) {
            URL.revokeObjectURL(previewObjectUrl);
        }
        previewObjectUrl = URL.createObjectURL(file);
        videoPreview.src = previewObjectUrl;
        videoPreview.hidden = false;
        videoPreview.play();
        uploadPlaceholder.hidden = true;
    }

    function hidePreview() {
        videoPreview.hidden = true;
        videoPreview.pause();
        videoPreview.src = "";
        if (previewObjectUrl) {
            URL.revokeObjectURL(previewObjectUrl);
            previewObjectUrl = null;
        }
        uploadPlaceholder.hidden = false;
    }

    // --- Validation ---

    function validateInputs() {
        let valid = true;
        clearErrors();

        if (!selectedFile) {
            showError(videoError, "Please upload a video");
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
        videoError.textContent = "";
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
        formData.append("video", selectedFile);
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
            // Raw buffers to accumulate text before stripping tags
            let thinkRaw = "";
            let contentRaw = "";

            function stripTags(text) {
                return text.replace(/<\/?(?:think|answer)>/g, "");
            }

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
                            thinkRaw += parsed.token;
                            thinkBlock.textContent = stripTags(thinkRaw);
                        } else {
                            ensureContentBlock();
                            contentRaw += parsed.token;
                            contentBlock.textContent = stripTags(contentRaw);
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
