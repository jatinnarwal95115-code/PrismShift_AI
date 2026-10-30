(() => {
    "use strict";

    // --------------------------------------------------
    // CONFIGURATION
    // --------------------------------------------------

    // FastAPI runs separately from VS Code Live Server.
    const API_BASE_URL = "http://127.0.0.1:8000";

    const MAX_FILE_SIZE = 10 * 1024 * 1024;

    const ALLOWED_TYPES = [
        "image/jpeg",
        "image/png",
        "image/webp"
    ];

    // --------------------------------------------------
    // DOM ELEMENTS
    // --------------------------------------------------

    const $ = (id) => document.getElementById(id);

    const homeLink = $("homeLink");
    const homeScreen = $("homeScreen");
    const workspaceScreen = $("workspaceScreen");

    const breadcrumb = $("breadcrumb");

    const workspaceEyebrow = $("workspaceEyebrow");
    const workspaceTitle = $("workspaceTitle");
    const workspaceDescription = $("workspaceDescription");
    const workspaceBadge = $("workspaceBadge");
    const uploadDescription = $("uploadDescription");

    const newSessionBtn = $("newSessionBtn");
    const backHomeBtn = $("backHomeBtn");

    const imageInput = $("imageInput");
    const uploadDropzone = $("uploadDropzone");
    const uploadPlaceholder = $("uploadPlaceholder");
    const previewContainer = $("previewContainer");
    const imagePreview = $("imagePreview");
    const previewFileName = $("previewFileName");
    const removeImageBtn = $("removeImageBtn");

    const analysisContext = $("analysisContext");
    const step2Title = $("step2Title");
    const digitalFields = $("digitalFields");
    const realityFields = $("realityFields");
    const senderName = $("senderName");
    const recipientSelect = $("recipientSelect");
    const locationInput = $("locationInput");
    const reportFormat = $("reportFormat");
    const extraInfo = $("extraInfo");
    const resultImage = $("resultImage");
    const analyzeBtn = $("analyzeBtn");
    const analyzeButtonText = $("analyzeButtonText");

    const resultsEmpty = $("resultsEmpty");
    const loadingState = $("loadingState");
    const loadingMessage = $("loadingMessage");
    const resultsOutput = $("resultsOutput");
    const resultText = $("resultText");

    const errorState = $("errorState");
    const errorMessage = $("errorMessage");

    const resultTitle = $("resultTitle");
    const copyResultBtn = $("copyResultBtn");
    const downloadResultBtn = $("downloadResultBtn");
    const retryBtn = $("retryBtn");

    const sessionList = $("sessionList");
    const emptySessions = $("emptySessions");

    const toast = $("toast");

    const infoBtn = $("infoBtn");
    const infoDialog = $("infoDialog");
    const closeInfoBtn = $("closeInfoBtn");

    // --------------------------------------------------
    // APPLICATION STATE
    // --------------------------------------------------

    let currentMode = null;
    let selectedFile = null;
    let previewUrl = null;
    let isAnalyzing = false;

    let lastAnalysisText = "";
    let lastRequest = null;

    let toastTimer = null;
    let requestController = null;

    const sessions = [];

    // --------------------------------------------------
    // MODE CONFIGURATION
    // --------------------------------------------------

    const MODES = {
        digital: {
            name: "Digital",
            eyebrow: "DIGITAL INTELLIGENCE",
            title: 'Decode the <span>design.</span>',
            description:
                "Upload a website screenshot, poster, interface or digital design to uncover its visual language.",
            uploadDescription:
                "Choose a website screenshot, poster, UI design or other digital visual.",
            badge: "✦ DIGITAL MODE",
            resultTitle: "Your design recipe",
            buttonText: "Generate",
            step2Title: "Describe your changes",
            loadingText: "Gemma is studying the visual design.",
            placeholder:
                "Describe what to create or change. For example: use a dark theme, change the font, make the hero section larger.",
            defaultContext:
                "Analyze this digital design image. Describe its visual style, dominant colors, typography characteristics, layout, spacing, visual hierarchy, and major UI or graphic elements. Then create a detailed, reusable prompt that could help recreate a design with similar characteristics. Clearly distinguish visible observations from uncertain guesses. Return a structured, practical report."
        },

        reality: {
            name: "Reality",
            eyebrow: "REAL-WORLD INTELLIGENCE",
            title: 'Understand your <span>surroundings.</span>',
            description:
                "Upload a photograph of a public space, damaged infrastructure or everyday physical-world problem.",
            uploadDescription:
                "Choose a photograph of a pothole, broken streetlight, waste accumulation, damaged infrastructure or another visible issue.",
            badge: "✦ REALITY MODE",
            resultTitle: "Your observation report",
            buttonText: "Generate",
            step2Title: "Letter details",
            loadingText: "Gemma is examining the visible details.",
            placeholder:
                "Add context if useful. For example: location, what you noticed, or what you want the report to emphasize.",
            defaultContext:
                "Analyze this real-world photograph and produce a structured observation report. Describe what is visibly present, identify any potential issue supported by the image, explain its possible impact, and suggest practical next steps. Include a suggested report title and a concise summary suitable for submitting to a relevant local authority or maintenance team. Clearly state uncertainty, avoid inventing the location or facts that cannot be verified from the image, and do not claim that a report has actually been submitted. If no clear issue is visible, say so."
        }
    };

    // --------------------------------------------------
    // TOAST NOTIFICATIONS
    // --------------------------------------------------

    function showToast(message) {
        toast.textContent = message;
        toast.classList.add("show");

        clearTimeout(toastTimer);

        toastTimer = setTimeout(() => {
            toast.classList.remove("show");
        }, 3000);
    }

    // --------------------------------------------------
    // MODE-SPECIFIC FIELDS
    // --------------------------------------------------

    function resetModeFields() {
        analysisContext.value = "";
        senderName.value = "";
        locationInput.value = "";
        extraInfo.value = "";
        recipientSelect.selectedIndex = 0;
        reportFormat.selectedIndex = 0;

        const defaultFormat = document.querySelector(
            'input[name="digitalFormat"][value="image"]'
        );

        if (defaultFormat) {
            defaultFormat.checked = true;
        }
    }

    function getDigitalFormat() {
        const checked = document.querySelector(
            'input[name="digitalFormat"]:checked'
        );

        return checked ? checked.value : "image";
    }

    function buildDigitalPrompt() {
        const format = getDigitalFormat();
        const userPrompt = analysisContext.value.trim();

        const formatInstruction = format === "code"
            ? "Output format: CODE. Write complete, ready-to-use HTML and CSS (and JavaScript only if needed) that recreates this design with the requested changes applied. Return the code in fenced code blocks."
            : "Output format: IMAGE. Produce a final image of this design with the requested changes applied. If you cannot output an image directly, return one detailed, ready-to-use image-generation prompt instead.";

        return [
            "Use the uploaded digital design image as the visual reference. Study its visual style, dominant colors, typography, layout, spacing and visual hierarchy before responding.",
            `User request:\n${userPrompt || "Recreate this design as faithfully as possible."}`,
            formatInstruction
        ].join("\n\n");
    }

    function buildRealityPrompt() {
        const recipient = recipientSelect.value;
        const format = reportFormat.value;
        const name = senderName.value.trim();
        const location = locationInput.value.trim();
        const extra = extraInfo.value.trim();

        const formatInstructions = {
            letter: "Write a formal letter: a subject line, a respectful salutation to the recipient, a clear body that describes the issue and requests action, and a polite closing. Put a placeholder like [Date] for the date.",
            message: "Write a short, polite message (under 120 words) suitable for WhatsApp or SMS. Be direct and clear.",
            email: "Write a formal email with a subject line, a respectful greeting, a concise body that describes the issue and requests action, and a polite closing."
        };

        return [
            `Look at the uploaded real-world photograph and write a ${format} addressed to the ${recipient} about the issue visible in it.`,
            formatInstructions[format] || formatInstructions.letter,
            "Details:",
            `- Recipient: ${recipient}`,
            `- Location: ${location || "not provided (use the placeholder [location])"}`,
            `- Extra information: ${extra || "none"}`,
            `- Sender name: ${name}`,
            `End the ${format} with the sender name "${name}" as the signature.`,
            "Describe only what is visible in the photograph, do not invent facts, and do not claim that the message has already been sent. If no clear issue is visible, say so."
        ].join("\n");
    }

    // --------------------------------------------------
    // NAVIGATION
    // --------------------------------------------------

    function openPortal(mode) {
        if (!MODES[mode]) {
            return;
        }

        currentMode = mode;

        const config = MODES[mode];

        homeScreen.classList.add("hidden");
        workspaceScreen.classList.remove("hidden");

        workspaceEyebrow.innerHTML =
            `<span></span> ${config.eyebrow}`;

        workspaceTitle.innerHTML = config.title;
        workspaceDescription.textContent = config.description;
        uploadDescription.textContent = config.uploadDescription;

        workspaceBadge.textContent = config.badge;
        workspaceBadge.classList.toggle(
            "reality",
            mode === "reality"
        );

        resultTitle.textContent = config.resultTitle;
        analyzeButtonText.textContent = config.buttonText;

        resetModeFields();
        analysisContext.placeholder = config.placeholder;

        step2Title.textContent = config.step2Title;
        digitalFields.classList.toggle("hidden", mode === "reality");
        realityFields.classList.toggle("hidden", mode !== "reality");

        breadcrumb.textContent =
            `WORKSPACE / ${config.name.toUpperCase()} MODE`;

        resetResults();

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }

    function goHome() {
        if (isAnalyzing) {
            const shouldLeave = window.confirm(
                "An analysis is running. Leave this workspace?"
            );

            if (!shouldLeave) {
                return;
            }

            cancelAnalysis();
        }

        homeScreen.classList.remove("hidden");
        workspaceScreen.classList.add("hidden");

        breadcrumb.textContent =
            "YOUR VISUAL INTELLIGENCE WORKSPACE";

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }

    document.querySelectorAll("[data-mode]").forEach((button) => {
        button.addEventListener("click", () => {
            openPortal(button.dataset.mode);
        });
    });

    homeLink.addEventListener("click", (event) => {
        event.preventDefault();
        goHome();
    });

    backHomeBtn.addEventListener("click", goHome);

    newSessionBtn.addEventListener("click", () => {
        if (isAnalyzing) {
            showToast("Wait for the current analysis to finish.");
            return;
        }

        clearSelectedImage();
        resetResults();
        resetModeFields();

        goHome();

        showToast("Ready for a new session.");
    });

    // --------------------------------------------------
    // IMAGE UPLOAD
    // --------------------------------------------------

    function openFilePicker() {
        if (isAnalyzing) {
            showToast("Please wait for the current analysis.");
            return;
        }

        imageInput.click();
    }

    uploadDropzone.addEventListener("click", (event) => {
        if (event.target.closest("#removeImageBtn")) {
            return;
        }

        openFilePicker();
    });

    uploadDropzone.addEventListener("keydown", (event) => {
        if (
            event.key === "Enter" ||
            event.key === " "
        ) {
            event.preventDefault();
            openFilePicker();
        }
    });

    imageInput.addEventListener("change", (event) => {
        const file = event.target.files[0];

        if (file) {
            selectImage(file);
        }
    });

    function selectImage(file) {
        if (isAnalyzing) {
            showToast("Please wait for the current analysis.");
            return;
        }

        if (!ALLOWED_TYPES.includes(file.type)) {
            showToast(
                "Unsupported file. Choose a JPG, PNG or WEBP image."
            );

            imageInput.value = "";
            return;
        }

        if (file.size > MAX_FILE_SIZE) {
            showToast("Your image must be smaller than 10 MB.");

            imageInput.value = "";
            return;
        }

        if (file.size === 0) {
            showToast("This file is empty. Choose another image.");

            imageInput.value = "";
            return;
        }

        clearPreviewUrl();

        selectedFile = file;
        previewUrl = URL.createObjectURL(file);

        imagePreview.onload = () => {
            analyzeBtn.disabled = false;
        };

        imagePreview.onerror = () => {
            showToast("The image preview could not be loaded.");

            clearSelectedImage();
        };

        imagePreview.src = previewUrl;

        previewFileName.textContent = file.name;

        uploadPlaceholder.classList.add("hidden");
        previewContainer.classList.remove("hidden");

        analyzeBtn.disabled = false;

        resetResults();
    }

    function clearPreviewUrl() {
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        }
    }

    function clearSelectedImage() {
        selectedFile = null;

        imageInput.value = "";
        imagePreview.removeAttribute("src");

        clearPreviewUrl();

        uploadPlaceholder.classList.remove("hidden");
        previewContainer.classList.add("hidden");

        analyzeBtn.disabled = true;
    }

    removeImageBtn.addEventListener("click", (event) => {
        event.stopPropagation();

        if (isAnalyzing) {
            showToast("Please wait for the current analysis.");
            return;
        }

        clearSelectedImage();
        resetResults();

        showToast("Image removed.");
    });

    // --------------------------------------------------
    // DRAG AND DROP
    // --------------------------------------------------

    ["dragenter", "dragover"].forEach((eventName) => {
        uploadDropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            event.stopPropagation();

            uploadDropzone.classList.add("dragover");
        });
    });

    ["dragleave", "dragend"].forEach((eventName) => {
        uploadDropzone.addEventListener(eventName, (event) => {
            event.preventDefault();

            if (
                event.relatedTarget &&
                uploadDropzone.contains(event.relatedTarget)
            ) {
                return;
            }

            uploadDropzone.classList.remove("dragover");
        });
    });

    uploadDropzone.addEventListener("drop", (event) => {
        event.preventDefault();
        event.stopPropagation();

        uploadDropzone.classList.remove("dragover");

        if (isAnalyzing) {
            showToast("Please wait for the current analysis.");
            return;
        }

        const file = event.dataTransfer.files[0];

        if (!file) {
            return;
        }

        selectImage(file);
    });

    // --------------------------------------------------
    // RESULTS DISPLAY
    // --------------------------------------------------

    function resetResults() {
        resultsEmpty.classList.remove("hidden");
        loadingState.classList.add("hidden");
        resultsOutput.classList.add("hidden");
        errorState.classList.add("hidden");

        resultText.textContent = "";
        lastAnalysisText = "";

        resultImage.classList.add("hidden");
        resultImage.removeAttribute("src");

        lastRequest = null;
    }

    function showLoading() {
        resultsEmpty.classList.add("hidden");
        resultsOutput.classList.add("hidden");
        errorState.classList.add("hidden");

        loadingState.classList.remove("hidden");

        loadingMessage.textContent =
            MODES[currentMode].loadingText;

        analyzeBtn.disabled = true;
        analyzeButtonText.textContent = "Generating...";
    }

    function showResults(text, imageSrc) {
        loadingState.classList.add("hidden");
        resultsEmpty.classList.add("hidden");
        errorState.classList.add("hidden");

        resultsOutput.classList.remove("hidden");

        resultText.textContent = text;
        lastAnalysisText = text;

        if (imageSrc) {
            resultImage.src = imageSrc;
            resultImage.classList.remove("hidden");
        } else {
            resultImage.classList.add("hidden");
            resultImage.removeAttribute("src");
        }

        analyzeButtonText.textContent =
            MODES[currentMode].buttonText;

        analyzeBtn.disabled = !selectedFile;

        saveSession({
            mode: currentMode,
            filename: selectedFile ? selectedFile.name : "Image",
            text,
            timestamp: new Date()
        });

        $("resultsPanel").scrollIntoView({
            behavior: "smooth",
            block: "nearest"
        });
    }

    function showError(message) {
        loadingState.classList.add("hidden");
        resultsEmpty.classList.add("hidden");
        resultsOutput.classList.add("hidden");

        errorState.classList.remove("hidden");

        errorMessage.textContent = message;

        analyzeButtonText.textContent =
            MODES[currentMode].buttonText;

        analyzeBtn.disabled = !selectedFile;
    }

    // --------------------------------------------------
    // API ERROR HANDLING
    // --------------------------------------------------

    async function readApiResponse(response) {
        const rawText = await response.text();

        let data = {};

        if (rawText) {
            try {
                data = JSON.parse(rawText);
            } catch {
                if (!response.ok) {
                    throw new Error(
                        `The server returned HTTP ${response.status}. ` +
                        "Check the FastAPI terminal for details."
                    );
                }

                throw new Error(
                    "The server response was not valid JSON. " +
                    "Check your FastAPI endpoint."
                );
            }
        }

        if (!response.ok) {
            let detail = data.detail || data.error;

            if (Array.isArray(detail)) {
                detail = detail
                    .map((item) => item.msg || JSON.stringify(item))
                    .join(", ");
            }

            throw new Error(
                detail ||
                `Request failed with HTTP ${response.status}.`
            );
        }

        if (data.success === false) {
            throw new Error(
                data.error ||
                data.detail ||
                "The analysis was unsuccessful."
            );
        }

        return data;
    }

    function extractAnalysis(data) {
        // Supports several common FastAPI response formats.
        const candidates = [
            data.analysis,
            data.result,
            data.report,
            data.response,
            data.output,
            data.message
        ];

        for (const candidate of candidates) {
            if (typeof candidate === "string" && candidate.trim()) {
                return candidate.trim();
            }

            if (
                candidate &&
                typeof candidate === "object"
            ) {
                return JSON.stringify(candidate, null, 2);
            }
        }

        if (data.data && typeof data.data === "object") {
            return JSON.stringify(data.data, null, 2);
        }

        throw new Error(
            "The server responded, but no analysis text was found. " +
            "Check the response format returned by your FastAPI endpoint."
        );
    }

    function extractImage(data) {
        // Optional: backend may return a generated image.
        const source = data.image_url || data.image || data.image_base64;

        if (typeof source !== "string" || !source.trim()) {
            return null;
        }

        if (/^(https?:|data:image\/)/i.test(source)) {
            return source;
        }

        return `data:image/png;base64,${source}`;
    }

    // --------------------------------------------------
    // IMAGE ANALYSIS
    // --------------------------------------------------

    async function analyzeImage() {
        if (isAnalyzing) {
            return;
        }

        if (!currentMode) {
            showToast("Choose a portal first.");
            return;
        }

        if (!selectedFile) {
            showToast("Upload an image before analyzing.");
            return;
        }

        const config = MODES[currentMode];

        if (currentMode === "reality" && !senderName.value.trim()) {
            showToast("Enter your name for the end of the letter.");
            senderName.focus();
            return;
        }

        const prompt = currentMode === "reality"
            ? buildRealityPrompt()
            : buildDigitalPrompt();

        lastRequest = {
            mode: currentMode,
            file: selectedFile,
            prompt
        };

        isAnalyzing = true;

        showLoading();

        requestController = new AbortController();

        const timeoutId = setTimeout(() => {
            if (requestController) {
                requestController.abort("timeout");
            }
        }, 180000);

        try {
            const formData = new FormData();

            // Must match the FastAPI UploadFile parameter name.
            formData.append("file", selectedFile);

            // Your backend can read this optional field if implemented.
            formData.append("context", prompt);

            // Extra fields for backends that want them separately.
            if (currentMode === "reality") {
                formData.append("sender_name", senderName.value.trim());
                formData.append("recipient", recipientSelect.value);
                formData.append("location", locationInput.value.trim());
                formData.append("extra_info", extraInfo.value.trim());
                formData.append("output_format", reportFormat.value);
            } else {
                formData.append("user_prompt", analysisContext.value.trim());
                formData.append("output_format", getDigitalFormat());
            }

            const response = await fetch(
                `${API_BASE_URL}/analyze/${currentMode}`,
                {
                    method: "POST",
                    body: formData,
                    signal: requestController.signal
                }
            );

            const data = await readApiResponse(response);
            const imageSrc = extractImage(data);

            let analysis;

            try {
                analysis = extractAnalysis(data);
            } catch (extractError) {
                if (!imageSrc) {
                    throw extractError;
                }

                analysis = "Your generated image is ready.";
            }

            showResults(analysis, imageSrc);

            showToast("Your analysis is ready!");

        } catch (error) {
            console.error("PrismShift analysis error:", error);

            if (error.name === "AbortError") {
                const message =
                    error.message === "timeout" ||
                    error.message === "signal timed out"
                        ? "The analysis took too long. Gemma may still be loading. Try again after checking Ollama and FastAPI."
                        : "The request was cancelled.";

                showError(message);
            } else if (
                error instanceof TypeError &&
                /fetch/i.test(error.message)
            ) {
                showError(
                    "Cannot connect to FastAPI. Make sure your backend is running at " +
                    API_BASE_URL +
                    " and CORS allows your Live Server origin."
                );
            } else {
                showError(error.message || "An unexpected error occurred.");
            }

        } finally {
            clearTimeout(timeoutId);

            requestController = null;
            isAnalyzing = false;

            analyzeBtn.disabled = !selectedFile;

            if (currentMode) {
                analyzeButtonText.textContent =
                    MODES[currentMode].buttonText;
            }
        }
    }

    analyzeBtn.addEventListener("click", analyzeImage);

    retryBtn.addEventListener("click", () => {
        if (lastRequest && selectedFile) {
            analyzeImage();
        } else {
            showToast("Upload an image to start a new analysis.");
        }
    });

    function cancelAnalysis() {
        if (requestController) {
            requestController.abort();
        }
    }

    // --------------------------------------------------
    // COPY RESULTS
    // --------------------------------------------------

    copyResultBtn.addEventListener("click", async () => {
        if (!lastAnalysisText) {
            showToast("There are no results to copy.");
            return;
        }

        try {
            await navigator.clipboard.writeText(lastAnalysisText);

            showToast("Analysis copied to clipboard.");
        } catch (error) {
            console.error("Clipboard error:", error);

            // Fallback for browsers where Clipboard API is unavailable.
            const textArea = document.createElement("textarea");

            textArea.value = lastAnalysisText;
            textArea.style.position = "fixed";
            textArea.style.opacity = "0";

            document.body.appendChild(textArea);

            textArea.select();

            const successful = document.execCommand("copy");

            textArea.remove();

            showToast(
                successful
                    ? "Analysis copied to clipboard."
                    : "Copy failed. Select the text and copy it manually."
            );
        }
    });

    // --------------------------------------------------
    // DOWNLOAD REPORT
    // --------------------------------------------------

    downloadResultBtn.addEventListener("click", () => {
        if (!lastAnalysisText) {
            showToast("There are no results to download.");
            return;
        }

        const modeName = currentMode || "analysis";

        const report = [
            "PRISMSHIFT AI",
            `${MODES[modeName].name.toUpperCase()} ANALYSIS`,
            `Generated: ${new Date().toLocaleString()}`,
            `Image: ${selectedFile ? selectedFile.name : "Previously analyzed image"}`,
            "",
            "----------------------------------------",
            "",
            lastAnalysisText,
            "",
            "----------------------------------------",
            "Generated using PrismShift AI."
        ].join("\n");

        const blob = new Blob(
            [report],
            { type: "text/plain;charset=utf-8" }
        );

        const url = URL.createObjectURL(blob);

        const anchor = document.createElement("a");

        anchor.href = url;
        anchor.download = `prismshift-${modeName}-report.txt`;

        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();

        URL.revokeObjectURL(url);

        showToast("Your report has been downloaded.");
    });

    // --------------------------------------------------
    // RECENT SESSIONS
    // --------------------------------------------------

    function saveSession(session) {
        sessions.unshift(session);

        // Keep the sidebar compact.
        if (sessions.length > 8) {
            sessions.pop();
        }

        renderSessions();
    }

    function renderSessions() {
        sessionList.innerHTML = "";

        if (sessions.length === 0) {
            sessionList.appendChild(emptySessions);
            return;
        }

        sessions.forEach((session, index) => {
            const button = document.createElement("button");

            button.type = "button";
            button.className = "session-item";

            const title = document.createElement("strong");
            title.textContent = session.filename;

            const subtitle = document.createElement("small");

            subtitle.textContent =
                `${session.mode === "digital" ? "Digital" : "Reality"} · ` +
                session.timestamp.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit"
                });

            button.append(title, subtitle);

            button.addEventListener("click", () => {
                if (isAnalyzing) {
                    showToast("Wait for the current analysis to finish.");
                    return;
                }

                openPortal(session.mode);

                clearSelectedImage();

                resultTitle.textContent =
                    MODES[session.mode].resultTitle;

                showResultsFromHistory(session);
            });

            sessionList.appendChild(button);
        });
    }

    function showResultsFromHistory(session) {
        resultsEmpty.classList.add("hidden");
        loadingState.classList.add("hidden");
        errorState.classList.add("hidden");
        resultsOutput.classList.remove("hidden");

        resultText.textContent = session.text;
        lastAnalysisText = session.text;

        analyzeBtn.disabled = true;

        analyzeButtonText.textContent =
            MODES[session.mode].buttonText;

        resultTitle.textContent = "Previous analysis";
    }

    // --------------------------------------------------
    // ABOUT DIALOG
    // --------------------------------------------------

    infoBtn.addEventListener("click", () => {
        if (typeof infoDialog.showModal === "function") {
            infoDialog.showModal();
        } else {
            showToast(
                "PrismShift AI analyzes real-world photographs and digital designs."
            );
        }
    });

    closeInfoBtn.addEventListener("click", () => {
        infoDialog.close();
    });

    infoDialog.addEventListener("click", (event) => {
        if (event.target === infoDialog) {
            infoDialog.close();
        }
    });

    // --------------------------------------------------
    // CLEANUP
    // --------------------------------------------------

    window.addEventListener("beforeunload", () => {
        clearPreviewUrl();
    });

})();