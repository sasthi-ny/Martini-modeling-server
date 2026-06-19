(function () {
  const form = document.getElementById("modelForm");
  if (!form) return;

  const btn = document.getElementById("modelBtn");
  const resetBtn = document.getElementById("modelResetBtn");

  const msgEl = document.getElementById("modelMsg");
  const resultsWrap = document.getElementById("modelResults");
  const detailsEl = document.getElementById("modelDetails");
  const linksEl = document.getElementById("modelLinks");
  const logEl = document.getElementById("modelLog");
  const plotEl = document.getElementById("modelPlot");

  // Track polling so Reset can stop it
  let pollTimer = null;
  let activeJobId = null;

  function setMsg(t) {
    if (msgEl) msgEl.textContent = t;
  }

  function stopPolling() {
    if (pollTimer) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
    activeJobId = null;
  }

  function resetUI() {
    stopPolling();
    form.reset();
    if (resultsWrap) resultsWrap.style.display = "none";
    if (detailsEl) detailsEl.textContent = "";
    if (linksEl) linksEl.innerHTML = "";
    if (logEl) logEl.textContent = "";
    if (plotEl) {
      plotEl.removeAttribute("src");
      plotEl.style.display = "none";
    }
    setMsg("Ready");
    if (btn) btn.disabled = false;
  }

  if (resetBtn) resetBtn.addEventListener("click", resetUI);

  async function loadLogIfPresent(urls) {
    if (!logEl) return;
    try {
      if (urls && urls["log.txt"]) {
        const lr = await fetch(urls["log.txt"]);
        logEl.textContent = await lr.text();
      } else {
        logEl.textContent = "No log.txt found.";
      }
    } catch (e) {
      logEl.textContent = "Could not load log.txt.";
    }
  }

  function renderDownloads(files, urls) {
    if (!linksEl) return;
    linksEl.innerHTML = "";
    for (const name of (files || [])) {
      const url = urls && urls[name];
      if (!url) continue;
      const a = document.createElement("a");
      a.href = url;
      a.textContent = name;
      a.target = "_blank";
      linksEl.appendChild(a);
    }
  }

  function renderPreview(urls) {
    if (!plotEl) return;
    const preview = (urls && (urls["preview.png"] || urls["preview.jpg"])) || "";
    if (preview) {
      plotEl.src = preview + "?t=" + Date.now();
      plotEl.style.display = "block";
    } else {
      plotEl.style.display = "none";
    }
  }

  async function poll(jobId) {
    // If user hit reset or started another job, stop this poll loop
    if (!activeJobId || activeJobId !== jobId) return;

    let r;
    try {
      r = await fetch("/status/" + jobId);
    } catch (err) {
      setMsg("Network error while polling.");
      if (btn) btn.disabled = false;
      return; // stop polling on network failure
    }

    if (!r.ok) {
      setMsg("Polling failed: HTTP " + r.status);
      if (detailsEl) detailsEl.textContent = await r.text().catch(() => "");
      if (resultsWrap) resultsWrap.style.display = "grid";
      if (btn) btn.disabled = false;
      return; // stop polling on HTTP error
    }

    let s;
    try {
      s = await r.json();
    } catch (err) {
      setMsg("Polling failed: invalid JSON response.");
      if (btn) btn.disabled = false;
      return; // stop polling
    }

    const st = (s.status || "").toString();

    // Terminal statuses
    if (st === "success") {
      setMsg("Completed");
      if (detailsEl) detailsEl.textContent = JSON.stringify(s, null, 2);

      renderDownloads(s.files, s.urls);
      await loadLogIfPresent(s.urls);
      renderPreview(s.urls);

      if (resultsWrap) resultsWrap.style.display = "grid";
      if (btn) btn.disabled = false;
      stopPolling();
      return;
    }

    if (st === "error") {
      setMsg("Failed");
      if (detailsEl) detailsEl.textContent = JSON.stringify(s, null, 2);

      // Even on error, try to show log if provided
      await loadLogIfPresent(s.urls);

      if (resultsWrap) resultsWrap.style.display = "grid";
      if (btn) btn.disabled = false;
      stopPolling();
      return;
    }

    if (st === "FAILURE") {
      setMsg("Failed (Celery FAILURE)");
      if (detailsEl) detailsEl.textContent = JSON.stringify(s, null, 2);

      if (resultsWrap) resultsWrap.style.display = "grid";
      if (btn) btn.disabled = false;
      stopPolling();
      return;
    }

    // Continue polling
    setMsg("Status: " + (st || "pending") + " ... " + jobId);
    pollTimer = setTimeout(() => poll(jobId), 1200);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Cancel any previous polling loop before starting a new job
    stopPolling();

    if (btn) btn.disabled = true;
    if (resultsWrap) resultsWrap.style.display = "none";
    setMsg("Submitting polymer job...");

    const fd = new FormData(form);

    let resp;
    try {
      resp = await fetch("/model", { method: "POST", body: fd });
    } catch (err) {
      setMsg("Network error. Could not reach API.");
      if (btn) btn.disabled = false;
      return;
    }

    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      setMsg("Request failed. Check logs.");
      if (detailsEl) detailsEl.textContent = text;
      if (resultsWrap) resultsWrap.style.display = "grid";
      if (btn) btn.disabled = false;
      return;
    }

    const data = await resp.json().catch(() => ({}));
    const jobId = data.job_id;

    if (!jobId) {
      setMsg("Request failed: missing job_id.");
      if (detailsEl) detailsEl.textContent = JSON.stringify(data, null, 2);
      if (resultsWrap) resultsWrap.style.display = "grid";
      if (btn) btn.disabled = false;
      return;
    }

    activeJobId = jobId;
    setMsg("Running... " + jobId);
    poll(jobId);
  });

  resetUI();
})();

