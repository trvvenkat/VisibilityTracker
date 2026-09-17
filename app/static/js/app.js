/**
 * Visibility Check Tracker - Frontend Client Logic
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-upload-input");
  const btnBrowseFile = document.getElementById("btn-browse-file");
  const dropPrompt = document.getElementById("drop-zone-prompt");
  const fileLoadedView = document.getElementById("file-loaded-view");
  const displayFilename = document.getElementById("display-filename");
  const displayKeywordCount = document.getElementById("display-keyword-count");
  const btnRemoveFile = document.getElementById("btn-remove-file");
  const uploadFeedback = document.getElementById("upload-feedback");

  const topNInput = document.getElementById("top-n-input");
  const btnStepperDec = document.getElementById("btn-stepper-dec");
  const btnStepperInc = document.getElementById("btn-stepper-inc");
  const previewNSlots = document.getElementById("preview-n-slots");

  const btnStartJob = document.getElementById("btn-start-job");
  const btnCancelJob = document.getElementById("btn-cancel-job");
  const btnDownloadCsv = document.getElementById("btn-download-csv");

  // History Elements
  const btnRefreshHistory = document.getElementById("btn-refresh-history");
  const btnClearHistory = document.getElementById("btn-clear-history");
  const historyTableBody = document.getElementById("history-table-body");
  const historyEmptyRow = document.getElementById("history-empty-row");
  const historyCountBadge = document.getElementById("history-count-badge");

  // Download Modal Elements
  const downloadModal = document.getElementById("download-modal");
  const customFilenameInput = document.getElementById("custom-filename-input");
  const downloadPreviewFilename = document.getElementById("download-preview-filename");
  const btnCloseDownloadModal = document.getElementById("btn-close-download-modal");
  const btnCancelDownload = document.getElementById("btn-cancel-download");
  const btnConfirmDownload = document.getElementById("btn-confirm-download");

  // Clear Confirmation Modal Elements
  const clearConfirmModal = document.getElementById("clear-confirm-modal");
  const btnCloseClearModal = document.getElementById("btn-close-clear-modal");
  const btnCancelClear = document.getElementById("btn-cancel-clear");
  const btnConfirmClear = document.getElementById("btn-confirm-clear");

  const stateIdlePlaceholder = document.getElementById("state-idle-placeholder");
  const monitorView = document.getElementById("monitor-view");
  const jobStatusBadge = document.getElementById("job-status-badge");
  const jobPlatformDisplay = document.getElementById("job-platform-display");
  const jobCompletedCount = document.getElementById("job-completed-count");
  const jobFailedCount = document.getElementById("job-failed-count");
  const jobTotalCount = document.getElementById("job-total-count");
  const progressRatio = document.getElementById("progress-ratio");
  const progressPercentage = document.getElementById("progress-percentage");
  const progressBarFill = document.getElementById("progress-bar-fill");
  const currentKeywordDisplay = document.getElementById("current-keyword-display");

  const resultsTableHead = document.getElementById("results-table-head");
  const resultsTableBody = document.getElementById("results-table-body");
  const resultsEmptyRow = document.getElementById("results-empty-row");
  const resultsCountBadge = document.getElementById("results-count-badge");
  const tableSearchFilter = document.getElementById("table-search-filter");

  const consoleLogs = document.getElementById("console-logs");
  const btnClearLogs = document.getElementById("btn-clear-logs");
  const toggleAutoscroll = document.getElementById("toggle-autoscroll");

  // State
  let currentFileId = null;
  let currentJobId = null;
  let activePlatform = "amazon";
  let eventSource = null;
  let pollingInterval = null;
  let processedResultCount = 0;
  let currentTopN = 3;

  // Download modal target state
  let downloadTargetJobId = null;
  let downloadTargetPlatform = "amazon";

  // ==========================================================================
  // Stepper Management
  // ==========================================================================
  function updateTopNPreview() {
    let n = parseInt(topNInput.value, 10);
    if (isNaN(n) || n < 1) n = 1;
    if (n > 15) n = 15;
    topNInput.value = n;
    currentTopN = n;

    const slots = [];
    for (let i = 1; i <= n; i++) {
      slots.push(`SP${i}`);
    }
    previewNSlots.textContent = slots.join(", ");
  }

  btnStepperDec.addEventListener("click", () => {
    let val = parseInt(topNInput.value, 10) || 1;
    if (val > 1) {
      topNInput.value = val - 1;
      updateTopNPreview();
    }
  });

  btnStepperInc.addEventListener("click", () => {
    let val = parseInt(topNInput.value, 10) || 1;
    if (val < 15) {
      topNInput.value = val + 1;
      updateTopNPreview();
    }
  });

  topNInput.addEventListener("change", updateTopNPreview);
  updateTopNPreview();

  // ==========================================================================
  // File Upload & Drag-and-Drop
  // ==========================================================================
  btnBrowseFile.addEventListener("click", (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  dropZone.addEventListener("click", () => {
    if (!currentFileId) {
      fileInput.click();
    }
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove("dragover");
    });
  });

  dropZone.addEventListener("drop", (e) => {
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      handleFileSelected(files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelected(files[0]);
    }
  });

  btnRemoveFile.addEventListener("click", (e) => {
    e.stopPropagation();
    resetFileUpload();
  });

  function showUploadError(msg) {
    uploadFeedback.textContent = msg;
    uploadFeedback.className = "form-feedback error";
    uploadFeedback.classList.remove("hidden");
  }

  function clearUploadError() {
    uploadFeedback.textContent = "";
    uploadFeedback.className = "form-feedback hidden";
  }

  function resetFileUpload() {
    currentFileId = null;
    fileInput.value = "";
    clearUploadError();
    dropPrompt.classList.remove("hidden");
    fileLoadedView.classList.add("hidden");
    btnStartJob.disabled = true;
  }

  async function handleFileSelected(file) {
    clearUploadError();
    const validExtensions = [".csv", ".xls", ".xlsx"];
    const ext = "." + file.name.split(".").pop().toLowerCase();

    if (!validExtensions.includes(ext)) {
      showUploadError(`Invalid file type "${ext}". Please upload a .csv, .xls, or .xlsx file.`);
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    addLogLine(`Uploading file "${file.name}" for keyword extraction...`);

    try {
      btnBrowseFile.textContent = "Validating...";
      btnBrowseFile.disabled = true;

      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "File upload and validation failed.");
      }

      currentFileId = data.file_id;
      displayFilename.textContent = data.filename;
      displayKeywordCount.textContent = `${data.keyword_count} keywords extracted`;

      dropPrompt.classList.add("hidden");
      fileLoadedView.classList.remove("hidden");
      btnStartJob.disabled = false;

      addLogLine(`File parsed successfully. Found ${data.keyword_count} valid keywords.`);
    } catch (err) {
      console.error(err);
      showUploadError(err.message || "Failed to process file.");
      resetFileUpload();
    } finally {
      btnBrowseFile.textContent = "Browse File";
      btnBrowseFile.disabled = false;
    }
  }

  // ==========================================================================
  // Job Launch & Management
  // ==========================================================================
  function getSelectedPlatform() {
    const radios = document.getElementsByName("platform");
    for (const r of radios) {
      if (r.checked) return r.value;
    }
    return "amazon";
  }

  btnStartJob.addEventListener("click", async () => {
    if (!currentFileId) return;

    const platform = getSelectedPlatform();
    const topN = parseInt(topNInput.value, 10) || 3;

    btnStartJob.disabled = true;
    addLogLine(`Initiating visibility check on ${platform.toUpperCase()} (Top N = ${topN})...`);

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_id: currentFileId,
          platform: platform,
          top_n: topN,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to start visibility check job.");
      }

      currentJobId = data.job_id;
      setupJobUI(currentJobId, platform, topN);
      startLiveStream(currentJobId);
    } catch (err) {
      console.error(err);
      alert(`Error starting job: ${err.message}`);
      btnStartJob.disabled = false;
    }
  });

  btnCancelJob.addEventListener("click", async () => {
    if (!currentJobId) return;
    if (!confirm("Are you sure you want to cancel this visibility run?")) return;

    btnCancelJob.disabled = true;
    addLogLine("Sending cancellation request...");

    try {
      await fetch(`/api/jobs/${currentJobId}/cancel`, { method: "POST" });
    } catch (err) {
      console.error("Error cancelling job:", err);
    }
  });

  function setupJobUI(jobId, platform, topN) {
    stateIdlePlaceholder.classList.add("hidden");
    monitorView.classList.remove("hidden");
    btnCancelJob.classList.remove("hidden");
    btnCancelJob.disabled = false;

    // Enable download link pointing to live output CSV
    btnDownloadCsv.href = "#";
    btnDownloadCsv.classList.remove("disabled");
    activePlatform = platform;

    // Initialize metrics
    updateStatusBadge("queued");
    jobPlatformDisplay.textContent = platform;
    jobCompletedCount.textContent = "0";
    jobFailedCount.textContent = "0";
    jobTotalCount.textContent = "-";
    progressRatio.textContent = "0 / 0 Keywords";
    progressPercentage.textContent = "0%";
    progressBarFill.style.width = "0%";
    currentKeywordDisplay.textContent = "Starting automation engine...";

    // Configure table headers dynamically based on topN
    buildTableHeaders(topN);

    // Clear previous table rows
    resultsTableBody.innerHTML = "";
    resultsTableBody.appendChild(resultsEmptyRow);
    resultsCountBadge.textContent = "0 Rows";
    processedResultCount = 0;
  }

  function buildTableHeaders(topN) {
    const tr = document.createElement("tr");
    
    const thIdx = document.createElement("th");
    thIdx.style.width = "50px";
    thIdx.textContent = "#";
    tr.appendChild(thIdx);

    const thKw = document.createElement("th");
    thKw.textContent = "Keyword";
    tr.appendChild(thKw);

    for (let i = 1; i <= topN; i++) {
      const thSp = document.createElement("th");
      thSp.textContent = `SP${i}`;
      tr.appendChild(thSp);
    }

    const thSd = document.createElement("th");
    thSd.textContent = "Sponsored Display";
    tr.appendChild(thSd);

    const thStatus = document.createElement("th");
    thStatus.style.width = "90px";
    thStatus.textContent = "Status";
    tr.appendChild(thStatus);

    resultsTableHead.innerHTML = "";
    resultsTableHead.appendChild(tr);
  }

  // ==========================================================================
  // Real-Time SSE & Polling
  // ==========================================================================
  function startLiveStream(jobId) {
    if (eventSource) {
      eventSource.close();
    }
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }

    eventSource = new EventSource(`/api/jobs/${jobId}/events`);

    eventSource.addEventListener("status", (e) => {
      try {
        const statusData = JSON.parse(e.data);
        handleStatusUpdate(statusData);
      } catch (err) {
        console.error("Error parsing status event:", err);
      }
    });

    eventSource.addEventListener("result", (e) => {
      try {
        const resultData = JSON.parse(e.data);
        appendResultRow(resultData);
      } catch (err) {
        console.error("Error parsing result event:", err);
      }
    });

    eventSource.addEventListener("log", (e) => {
      try {
        const logData = JSON.parse(e.data);
        addLogLine(logData.message);
      } catch (err) {
        console.error("Error parsing log event:", err);
      }
    });

    eventSource.onerror = () => {
      console.warn("EventSource encountered an error or closed. Fallback to polling.");
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
      startPolling(jobId);
    };
  }

  function startPolling(jobId) {
    if (pollingInterval) return;

    pollingInterval = setInterval(async () => {
      try {
        const resStatus = await fetch(`/api/jobs/${jobId}/status`);
        if (!resStatus.ok) return;
        const statusData = await resStatus.json();
        handleStatusUpdate(statusData);

        const resResults = await fetch(`/api/jobs/${jobId}/results`);
        if (!resResults.ok) return;
        const resultsData = await resResults.json();

        if (resultsData.results && resultsData.results.length > processedResultCount) {
          const newResults = resultsData.results.slice(processedResultCount);
          newResults.forEach((r) => appendResultRow(r));
        }

        if (["completed", "failed", "cancelled"].includes(statusData.status)) {
          clearInterval(pollingInterval);
          pollingInterval = null;
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 1500);
  }

  function handleStatusUpdate(data) {
    updateStatusBadge(data.status);
    jobPlatformDisplay.textContent = data.platform;
    jobCompletedCount.textContent = data.completed_count;
    jobFailedCount.textContent = data.failed_count;
    jobTotalCount.textContent = data.total_keywords;

    const total = data.total_keywords || 0;
    const processed = data.processed_keywords || 0;
    const pct = total > 0 ? Math.round((processed / total) * 100) : 0;

    progressRatio.textContent = `${processed} / ${total} Keywords`;
    progressPercentage.textContent = `${pct}%`;
    progressBarFill.style.width = `${pct}%`;

    if (data.current_keyword) {
      currentKeywordDisplay.textContent = data.current_keyword;
    } else if (data.status === "completed") {
      currentKeywordDisplay.textContent = "All keywords processed successfully.";
    } else if (data.status === "cancelled") {
      currentKeywordDisplay.textContent = "Job execution cancelled.";
    } else if (data.status === "failed") {
      currentKeywordDisplay.textContent = data.error || "Job failed with an error.";
    }

    if (["completed", "failed", "cancelled"].includes(data.status)) {
      btnCancelJob.classList.add("hidden");
      btnStartJob.disabled = false;
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
      if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
      }
      // Refresh Runs History table to include this completed run
      loadRunsHistory();
    }
  }

  function updateStatusBadge(status) {
    const s = (status || "").toLowerCase();
    jobStatusBadge.textContent = s.toUpperCase();
    jobStatusBadge.className = `badge badge-status ${s}`;
  }

  function appendResultRow(data) {
    if (resultsEmptyRow.parentNode) {
      resultsEmptyRow.remove();
    }

    processedResultCount++;
    resultsCountBadge.textContent = `${processedResultCount} Rows`;

    const tr = document.createElement("tr");
    tr.className = "fade-in";

    // # index
    const tdIdx = document.createElement("td");
    tdIdx.textContent = processedResultCount;
    tr.appendChild(tdIdx);

    // Keyword
    const tdKw = document.createElement("td");
    tdKw.className = "table-kw-cell";
    tdKw.textContent = data.keyword;
    tr.appendChild(tdKw);

    // SP columns (from data.sp_list)
    const spList = data.sp_list || [];
    for (let i = 0; i < currentTopN; i++) {
      const tdSp = document.createElement("td");
      tdSp.className = "product-cell";
      const val = spList[i];
      if (val && val !== "N/A") {
        tdSp.textContent = val;
        tdSp.title = val;
      } else {
        const pill = document.createElement("span");
        pill.className = "na-pill";
        pill.textContent = "N/A";
        tdSp.appendChild(pill);
      }
      tr.appendChild(tdSp);
    }

    // Sponsored Display
    const tdSd = document.createElement("td");
    tdSd.className = "product-cell";
    const sdVal = data.sponsored_display;
    if (sdVal && sdVal !== "N/A") {
      tdSd.textContent = sdVal;
      tdSd.title = sdVal;
    } else {
      const pill = document.createElement("span");
      pill.className = "na-pill";
      pill.textContent = "N/A";
      tdSd.appendChild(pill);
    }
    tr.appendChild(tdSd);

    // Status
    const tdStatus = document.createElement("td");
    const tag = document.createElement("span");
    if (data.success) {
      tag.className = "status-tag ok";
      tag.textContent = "SUCCESS";
    } else {
      tag.className = "status-tag fail";
      tag.textContent = "FAILED";
      if (data.error) {
        tag.title = data.error;
      }
    }
    tdStatus.appendChild(tag);
    tr.appendChild(tdStatus);

    resultsTableBody.appendChild(tr);

    // Apply search filter if active
    filterRow(tr);
  }

  // ==========================================================================
  // Table Search Filter
  // ==========================================================================
  tableSearchFilter.addEventListener("input", () => {
    const rows = resultsTableBody.querySelectorAll("tr:not(.empty-row)");
    rows.forEach(filterRow);
  });

  function filterRow(tr) {
    const q = (tableSearchFilter.value || "").trim().toLowerCase();
    if (!q) {
      tr.style.display = "";
      return;
    }
    const text = tr.textContent.toLowerCase();
    tr.style.display = text.includes(q) ? "" : "none";
  }

  // ==========================================================================
  // Console Log Helpers
  // ==========================================================================
  function addLogLine(msg) {
    const line = document.createElement("div");
    line.className = "log-line";
    line.textContent = msg;
    consoleLogs.appendChild(line);

    if (toggleAutoscroll.checked) {
      consoleLogs.scrollTop = consoleLogs.scrollHeight;
    }
  }

  btnClearLogs.addEventListener("click", () => {
    consoleLogs.innerHTML = "";
  });

  // ==========================================================================
  // Custom Download Modal Logic
  // ==========================================================================
  function getTimestampString() {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, "0");
    const dd = String(now.getDate()).padStart(2, "0");
    const hh = String(now.getHours()).padStart(2, "0");
    const min = String(now.getMinutes()).padStart(2, "0");
    const ss = String(now.getSeconds()).padStart(2, "0");
    return `${yyyy}${mm}${dd}_${hh}${min}${ss}`;
  }

  function updateDownloadPreview() {
    const ts = getTimestampString();
    let raw = (customFilenameInput.value || "").trim();
    // remove disallowed characters and .csv extension if typed
    let clean = raw.replace(/[\\/*?:"<>|]/g, "").trim();
    if (clean.toLowerCase().endsWith(".csv")) {
      clean = clean.slice(0, -4).trim();
    }

    if (clean) {
      downloadPreviewFilename.textContent = `${clean}_${ts}.csv`;
    } else {
      const plat = (downloadTargetPlatform || "results").toLowerCase();
      downloadPreviewFilename.textContent = `visibility_${plat}_${ts}.csv`;
    }
  }

  function openDownloadModal(jobId, platform) {
    if (!jobId) return;
    downloadTargetJobId = jobId;
    downloadTargetPlatform = platform || "results";
    customFilenameInput.value = "";
    updateDownloadPreview();
    downloadModal.classList.remove("hidden");
    customFilenameInput.focus();
  }

  function closeDownloadModal() {
    downloadModal.classList.add("hidden");
    downloadTargetJobId = null;
  }

  customFilenameInput.addEventListener("input", updateDownloadPreview);

  btnCloseDownloadModal.addEventListener("click", closeDownloadModal);
  btnCancelDownload.addEventListener("click", closeDownloadModal);

  btnConfirmDownload.addEventListener("click", () => {
    if (!downloadTargetJobId) return;
    let raw = (customFilenameInput.value || "").trim();
    let clean = raw.replace(/[\\/*?:"<>|]/g, "").trim();
    if (clean.toLowerCase().endsWith(".csv")) {
      clean = clean.slice(0, -4).trim();
    }

    let url = `/api/jobs/${downloadTargetJobId}/download`;
    if (clean) {
      url += `?custom_name=${encodeURIComponent(clean)}`;
    }

    closeDownloadModal();
    window.location.href = url;
  });

  // Execution monitor Download button click handler
  btnDownloadCsv.addEventListener("click", (e) => {
    e.preventDefault();
    if (!currentJobId || btnDownloadCsv.classList.contains("disabled")) return;
    openDownloadModal(currentJobId, activePlatform);
  });

  // ==========================================================================
  // Clear Pre-runs Confirmation Modal Logic
  // ==========================================================================
  btnClearHistory.addEventListener("click", () => {
    clearConfirmModal.classList.remove("hidden");
  });

  btnCloseClearModal.addEventListener("click", () => {
    clearConfirmModal.classList.add("hidden");
  });

  btnCancelClear.addEventListener("click", () => {
    clearConfirmModal.classList.add("hidden");
  });

  btnConfirmClear.addEventListener("click", async () => {
    btnConfirmClear.disabled = true;
    btnConfirmClear.textContent = "Clearing...";
    try {
      const res = await fetch("/api/jobs/clear", { method: "POST" });
      const data = await res.json();
      clearConfirmModal.classList.add("hidden");
      addLogLine(`[SYSTEM] ${data.message || "History cleared."}`);
      await loadRunsHistory();
    } catch (err) {
      console.error("Failed to clear history:", err);
      alert("Failed to clear history. Check console logs.");
    } finally {
      btnConfirmClear.disabled = false;
      btnConfirmClear.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="3 6 5 6 21 6"></polyline>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
        </svg>
        <span>Yes, Clear History</span>
      `;
    }
  });

  // Close modals on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (!downloadModal.classList.contains("hidden")) closeDownloadModal();
      if (!clearConfirmModal.classList.contains("hidden")) clearConfirmModal.classList.add("hidden");
    }
  });

  // ==========================================================================
  // Runs History Table Loader
  // ==========================================================================
  btnRefreshHistory.addEventListener("click", () => {
    loadRunsHistory();
  });

  function formatRunDate(isoString) {
    if (!isoString) return "-";
    try {
      const d = new Date(isoString);
      if (isNaN(d.getTime())) return isoString;
      return d.toLocaleString("en-US", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      });
    } catch (e) {
      return isoString;
    }
  }

  async function loadRunsHistory() {
    try {
      const res = await fetch("/api/jobs");
      if (!res.ok) {
        if (res.status === 401) {
          window.location.href = "/login";
          return;
        }
        throw new Error(`Failed to load jobs: ${res.statusText}`);
      }

      const jobs = await res.json();
      historyCountBadge.textContent = `${jobs.length} Past Run${jobs.length === 1 ? "" : "s"}`;

      historyTableBody.innerHTML = "";
      if (!jobs || jobs.length === 0) {
        historyTableBody.appendChild(historyEmptyRow);
        return;
      }

      jobs.forEach((job, index) => {
        const tr = document.createElement("tr");

        // 1. Index
        const tdIdx = document.createElement("td");
        tdIdx.textContent = index + 1;
        tr.appendChild(tdIdx);

        // 2. Uploaded File
        const tdFile = document.createElement("td");
        tdFile.className = "history-file-cell";
        tdFile.innerHTML = `
          <span class="history-file-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
          </span>
          <span>${job.uploaded_filename || "keywords.csv"}</span>
        `;
        tr.appendChild(tdFile);

        // 3. Platform
        const tdPlat = document.createElement("td");
        const platBadge = document.createElement("span");
        platBadge.className = `badge capitalize platform-tag ${job.platform}`;
        platBadge.textContent = job.platform;
        tdPlat.appendChild(platBadge);
        tr.appendChild(tdPlat);

        // 4. Date & Time Ran
        const tdDate = document.createElement("td");
        const dateStr = formatRunDate(job.started_at || job.created_at || job.completed_at);
        tdDate.textContent = dateStr;
        tdDate.style.fontSize = "0.8125rem";
        tdDate.style.color = "var(--text-muted)";
        tr.appendChild(tdDate);

        // 5. Status
        const tdStatus = document.createElement("td");
        const stTag = document.createElement("span");
        const st = (job.status || "completed").toLowerCase();
        if (st === "completed") {
          stTag.className = "status-tag ok";
          stTag.textContent = "COMPLETED";
        } else if (st === "running") {
          stTag.className = "badge badge-status running";
          stTag.textContent = "RUNNING";
        } else if (st === "cancelled") {
          stTag.className = "status-tag fail";
          stTag.textContent = "CANCELLED";
        } else {
          stTag.className = "status-tag fail";
          stTag.textContent = "FAILED";
        }
        tdStatus.appendChild(stTag);
        tr.appendChild(tdStatus);

        // 6. Keywords & Progress
        const tdKw = document.createElement("td");
        const total = job.total_keywords || 0;
        const comp = job.completed_count || 0;
        tdKw.innerHTML = `<span>${total} keyword${total === 1 ? "" : "s"}</span> <span style="font-size: 0.75rem; color: var(--text-dim);">(${comp} ok)</span>`;
        tr.appendChild(tdKw);

        // 7. Actions
        const tdActions = document.createElement("td");
        tdActions.className = "history-actions-cell";

        // View Results Button
        if (job.has_results_file || job.status === "completed") {
          const btnView = document.createElement("button");
          btnView.className = "btn btn-secondary btn-xs";
          btnView.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
            <span>View</span>
          `;
          btnView.title = "View results in live table";
          btnView.addEventListener("click", () => {
            loadPastJobResultsIntoTable(job.job_id, job.platform, job.top_n || 3);
          });
          tdActions.appendChild(btnView);
        }

        // Download CSV Button
        if (job.has_results_file) {
          const btnDl = document.createElement("button");
          btnDl.className = "btn btn-success btn-xs";
          btnDl.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            <span>Download</span>
          `;
          btnDl.title = "Download CSV with custom or timestamped filename";
          btnDl.addEventListener("click", () => {
            openDownloadModal(job.job_id, job.platform);
          });
          tdActions.appendChild(btnDl);
        }

        tr.appendChild(tdActions);
        historyTableBody.appendChild(tr);
      });
    } catch (err) {
      console.error("Error loading runs history:", err);
    }
  }

  async function loadPastJobResultsIntoTable(jobId, platform, topN) {
    try {
      addLogLine(`[SYSTEM] Loading results for job ${jobId.slice(0, 8)} into live view...`);
      const res = await fetch(`/api/jobs/${jobId}/results`);
      if (!res.ok) throw new Error("Failed to load job results");
      const data = await res.json();

      currentTopN = topN;
      buildTableHeaders(topN);
      resultsTableBody.innerHTML = "";
      processedResultCount = 0;

      if (data.results && data.results.length > 0) {
        data.results.forEach((r) => appendResultRow(r));
      } else if (data.rows && data.rows.length > 0) {
        // Build rows from raw CSV row array
        data.rows.forEach((rowArr) => {
          const kw = rowArr[0] || "";
          const sps = rowArr.slice(1, 1 + topN);
          const sd = rowArr[1 + topN] || "N/A";
          appendResultRow({
            keyword: kw,
            sp_list: sps,
            sponsored_display: sd,
            success: true,
          });
        });
      } else {
        resultsTableBody.appendChild(resultsEmptyRow);
      }

      // Scroll smoothly to results table
      document.getElementById("table-container").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      console.error("Error loading past job results:", err);
      alert("Could not load past job results.");
    }
  }

  // ==========================================================================
  // Remote Access / Tunnel Status Loader
  // ==========================================================================
  const tunnelBadge = document.getElementById("tunnel-badge");
  const tunnelLink = document.getElementById("tunnel-link");
  const btnCopyTunnel = document.getElementById("btn-copy-tunnel");
  const copyTunnelText = document.getElementById("copy-tunnel-text");

  async function checkTunnelStatus() {
    if (!tunnelBadge) return;
    try {
      const res = await fetch("/api/tunnel-info");
      if (!res.ok) return;
      const data = await res.json();
      if (data.active && data.public_url) {
        tunnelLink.href = data.public_url;
        tunnelLink.textContent = data.public_url;
        tunnelBadge.classList.remove("hidden");
      } else {
        tunnelBadge.classList.add("hidden");
      }
    } catch (err) {
      console.debug("Tunnel check:", err);
    }
  }

  if (btnCopyTunnel) {
    btnCopyTunnel.addEventListener("click", async () => {
      const url = tunnelLink.href;
      if (!url || url === "#") return;
      try {
        await navigator.clipboard.writeText(url);
        copyTunnelText.textContent = "Copied!";
        btnCopyTunnel.style.background = "rgba(16, 185, 129, 0.4)";
        setTimeout(() => {
          copyTunnelText.textContent = "Copy";
          btnCopyTunnel.style.background = "";
        }, 2000);
      } catch (e) {
        prompt("Copy this remote access link:", url);
      }
    });
  }

  // Initial tunnel check and periodic check every 30s
  checkTunnelStatus();
  setInterval(checkTunnelStatus, 30000);

  // Initial load of past runs history
  loadRunsHistory();
});
