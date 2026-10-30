(() => {
  const mode = document.body.dataset.page;
  if (mode !== "reality" && mode !== "digital") return;

  const $ = selector => document.querySelector(selector);
  const api = window.PSApi;
  const toast = message => window.PS.toast(message);
  const input = $(".image-input");
  const drop = $(".upload-dropzone");
  const placeholder = $(".upload-placeholder");
  const previewBox = $(".preview-container");
  const previewImage = $(".image-preview");
  const previewName = $(".preview-name");
  const generateButton = $(".generate-btn");
  const analyzeButton = $(".analyze-image-btn");
  const output = $(".results-output");
  const empty = $(".results-empty");
  const loading = $(".loading-state");
  const errorBox = $(".error-state");
  const resultText = $(".result-text");
  let selectedFile = null;
  let previewUrl = null;
  let currentContent = "";
  let conversationId = null;
  let retryAction = null;

  function showError(message) {
    loading.classList.add("hidden");
    output.classList.add("hidden");
    empty.classList.add("hidden");
    errorBox.classList.remove("hidden");
    $(".error-message").textContent = message;
  }

  function resetOutput() {
    empty.classList.remove("hidden");
    loading.classList.add("hidden");
    errorBox.classList.add("hidden");
    output.classList.add("hidden");
    currentContent = "";
    conversationId = null;
  }

  function selectFile(file) {
    if (!file) return;
    const valid = ["image/jpeg", "image/png", "image/webp"];
    if (!valid.includes(file.type)) return toast("Choose a JPG, PNG or WEBP image.");
    if (file.size > 10 * 1024 * 1024) return toast("Image must be smaller than 10 MB.");
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    selectedFile = file;
    previewUrl = URL.createObjectURL(file);
    previewImage.src = previewUrl;
    previewName.textContent = file.name;
    placeholder.classList.add("hidden");
    previewBox.classList.remove("hidden");
    generateButton.disabled = false;
    if (analyzeButton) analyzeButton.disabled = false;
    resetOutput();
  }

  drop.addEventListener("click", event => {
    if (!event.target.closest(".remove-image")) input.click();
  });
  drop.addEventListener("keydown", event => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      input.click();
    }
  });
  input.addEventListener("change", event => selectFile(event.target.files[0]));
  ["dragenter", "dragover"].forEach(type => drop.addEventListener(type, event => {
    event.preventDefault();
    drop.classList.add("dragover");
  }));
  ["dragleave", "drop"].forEach(type => drop.addEventListener(type, event => {
    event.preventDefault();
    drop.classList.remove("dragover");
  }));
  drop.addEventListener("drop", event => selectFile(event.dataTransfer.files[0]));
  $(".remove-image")?.addEventListener("click", event => {
    event.stopPropagation();
    selectedFile = null;
    input.value = "";
    previewImage.removeAttribute("src");
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    placeholder.classList.remove("hidden");
    previewBox.classList.add("hidden");
    generateButton.disabled = true;
    if (analyzeButton) analyzeButton.disabled = true;
    resetOutput();
  });

  function buildFormData() {
    const data = new FormData();
    data.append("image", selectedFile);
    if (mode === "reality") {
      const typeMap = {
        "Formal letter": "letter",
        "Application": "application",
        "Complaint": "complaint",
        "Detailed report": "report"
      };
      data.append("document_type", typeMap[$("#documentType").value] || "report");
      data.append("author_name", $("#authorName").value.trim());
      data.append("location", $("#reportLocation").value.trim());
      data.append("authority", $("#recipient").value.trim());
      data.append("additional_points", $("#additionalPoints").value.trim());
    } else {
      data.append("description", $("#digitalRequirements").value.trim());
    }
    return data;
  }

  function showResult(content, id, analysis = "") {
    currentContent = content;
    conversationId = id ?? conversationId;
    resultText.textContent = content;
    let analysisBox = $(".generated-analysis");
    if (analysis) {
      if (!analysisBox) {
        analysisBox = document.createElement("details");
        analysisBox.className = "generated-analysis";
        const summary = document.createElement("summary");
        summary.textContent = "View image analysis";
        const body = document.createElement("div");
        body.className = "analysis-content";
        analysisBox.append(summary, body);
        resultText.before(analysisBox);
      }
      analysisBox.querySelector(".analysis-content").textContent = analysis;
      analysisBox.classList.remove("hidden");
    } else if (analysisBox) {
      analysisBox.classList.add("hidden");
    }
    empty.classList.add("hidden");
    loading.classList.add("hidden");
    errorBox.classList.add("hidden");
    output.classList.remove("hidden");
  }

  // On narrower screens the results panel sits below the form; bring it into view.
  function revealResults() {
    $(".results-panel")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  async function generate() {
    if (!selectedFile) return toast("Upload your own image first.");
    const endpoint = mode === "reality" ? "/reality/generate" : "/digital/generate";
    const buttonLabel = $(".generate-label");
    generateButton.disabled = true;
    buttonLabel.textContent = "Working…";
    empty.classList.add("hidden");
    output.classList.add("hidden");
    errorBox.classList.add("hidden");
    loading.classList.remove("hidden");
    revealResults();
    $(".loading-message").textContent = mode === "reality"
      ? "Gemma is analyzing your image and preparing your document…"
      : "Gemma is studying the visual design and writing your prompt…";
    retryAction = generate;

    try {
      const response = await api.form(endpoint, buildFormData());
      const content = mode === "reality" ? response.document : response.generated_prompt;
      if (typeof content !== "string" || !content.trim()) {
        throw new Error("The backend response did not include the expected generated content.");
      }
      conversationId = response.conversation_id ?? null;
      showResult(content, conversationId, response.analysis || "");
      window.PS.refreshHistory?.();
      toast(mode === "reality" ? "Report generated." : "Design prompt generated.");
    } catch (requestError) {
      showError(requestError.message || "The request could not be completed.");
      toast("Could not complete the request.");
    } finally {
      generateButton.disabled = !selectedFile;
      buttonLabel.textContent = mode === "reality" ? "Generate report" : "Generate prompt";
    }
  }


  async function analyzeImage() {
    if (!selectedFile) return toast("Upload your own image first.");
    const data = new FormData();
    data.append("image", selectedFile);
    analyzeButton.disabled = true;
    const oldLabel = analyzeButton.textContent;
    analyzeButton.textContent = "Analyzing…";
    try {
      const response = await api.form(`/${mode}/analyze`, data);
      if (typeof response.analysis !== "string" || !response.analysis.trim()) {
        throw new Error("The backend response did not include image analysis.");
      }
      let panel = $(".standalone-analysis");
      if (!panel) {
        panel = document.createElement("section");
        panel.className = "standalone-analysis";
        panel.innerHTML = "<strong>Image analysis</strong><p></p>";
        $(".results-panel .panel-heading").after(panel);
      }
      panel.querySelector("p").textContent = response.analysis;
      toast("Image analysis complete.");
    } catch (requestError) {
      toast(requestError.message || "Image analysis failed.");
    } finally {
      analyzeButton.disabled = !selectedFile;
      analyzeButton.textContent = oldLabel;
    }
  }
  analyzeButton?.addEventListener("click", analyzeImage);

  generateButton.addEventListener("click", generate);
  $(".retry-btn")?.addEventListener("click", () => retryAction?.());

  $(".copy-output")?.addEventListener("click", async () => {
    if (!currentContent) return;
    try {
      await navigator.clipboard.writeText(currentContent);
      toast("Copied to clipboard.");
    } catch {
      toast("Clipboard access was blocked by the browser.");
    }
  });

  $(".download-output")?.addEventListener("click", () => {
    if (!currentContent) return;
    const url = URL.createObjectURL(new Blob([currentContent], { type: "text/plain;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `prismshift-${mode}-${Date.now()}.txt`;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  });

  document.querySelectorAll(".export-output").forEach(button => {
    button.addEventListener("click", async () => {
      if (mode !== "reality" || !currentContent) return;
      const format = button.dataset.format;
      const data = new FormData();
      data.append("content", currentContent);
      data.append("file_format", format);
      button.disabled = true;
      try {
        await api.download("/reality/export", data, `PrismShift_Reality_Report.${format}`);
        toast(`${format.toUpperCase()} downloaded.`);
      } catch (requestError) {
        toast(requestError.message || "Export failed.");
      } finally {
        button.disabled = false;
      }
    });
  });

  $(".send-edit")?.addEventListener("click", async () => {
    const instruction = $(".edit-message").value.trim();
    if (!instruction || !currentContent) return toast("Write an editing instruction first.");
    const button = $(".send-edit");
    const data = new FormData();
    data.append("instruction", instruction);
    data.append("content", currentContent);
    if (conversationId !== null && conversationId !== undefined) {
      data.append("conversation_id", String(conversationId));
    }
    button.disabled = true;
    button.textContent = "Refining…";
    try {
      const response = await api.form(`/${mode}/edit`, data);
      const revised = mode === "reality" ? response.revised_document : response.revised_prompt;
      if (typeof revised !== "string" || !revised.trim()) {
        throw new Error("The backend did not return the revised content.");
      }
      conversationId = response.conversation_id ?? conversationId;
      showResult(revised, conversationId);
      window.PS.refreshHistory?.();
      $(".edit-message").value = "";
      toast("Your content has been refined.");
    } catch (requestError) {
      toast(requestError.message || "Could not refine the content.");
    } finally {
      button.disabled = false;
      button.textContent = "Send ↗";
    }
  });

  function restoreConversation() {
    let saved = null;
    try {
      saved = JSON.parse(sessionStorage.getItem("prismshift_open_conversation") || "null");
    } catch { /* Ignore invalid session cache. */ }
    if (!saved || saved.mode !== mode) return;
    sessionStorage.removeItem("prismshift_open_conversation");
    const messages = Array.isArray(saved.messages) ? saved.messages : [];
    const lastAssistant = [...messages].reverse().find(message => message.role === "assistant");
    if (lastAssistant?.content) {
      conversationId = saved.id;
      showResult(lastAssistant.content, saved.id);
      toast("Conversation reopened from history.");
    }
  }
  restoreConversation();
})();
