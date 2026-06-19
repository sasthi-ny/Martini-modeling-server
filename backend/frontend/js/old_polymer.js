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

  function setMsg(t) {
    if (msgEl) msgEl.textContent = t;
  }

  function resetUI() {
    form.reset();
    if (resultsWrap) resultsWrap.style.display = "none";
    if (detailsEl) detailsEl.textContent = "";
    if (linksEl) linksEl.innerHTML = "";
    if (logEl) logEl.textContent = "";
    if (plotEl) plotEl.removeAttribute("src");
    setMsg("Ready");
    if (btn) btn.disabled = false;
  }

  if (resetBtn) resetBtn.addEventListener("click", resetUI);

  async function poll(jobId) {
    const r = await fetch("/status/" + jobId);
    const s = await r.json();

    if (s.status === "success") {
      setMsg("Completed");
      if (detailsEl) detailsEl.textContent = JSON.stringify(s, null, 2);

      if (linksEl) {
        linksEl.innerHTML = "";
        for (const name of (s.files || [])) {
          const url = s.urls && s.urls[name];
          if (!url) continue;
          const a = document.createElement("a");
          a.href = url;
          a.textContent = name;
          a.target = "_blank";
          linksEl.appendChild(a);
        }
      }

      if (logEl) {
        if (s.urls && s.urls["log.txt"]) {
          const lr = await fetch(s.urls["log.txt"]);
          logEl.textContent = await lr.text();
        } else {
          logEl.textContent = "No log.txt found.";
        }
      }

      // Optional: if you later generate a preview image, show it here
      // For now, hide image if not available
      if (plotEl) {
        const preview = (s.urls && (s.urls["preview.png"] || s.urls["preview.jpg"])) || "";
        if (preview) {
          plotEl.src = preview + "?t=" + Date.now();
          plotEl.style.display = "block";
        } else {
          plotEl.style.display = "none";
        }
      }

      if (resultsWrap) resultsWrap.style.display = "grid";
      if (btn) btn.disabled = false;
      return;
    }

    if (s.status === "error") {
      setMsg("Failed");
      if (detailsEl) detailsEl.textContent = JSON.stringify(s, null, 2);
      if (logEl && s.urls && s.urls["log.txt"]) {
        const lr = await fetch(s.urls["log.txt"]);
        logEl.textContent = await lr.text();
      }
      if (resultsWrap) resultsWrap.style.display = "grid";
      if (btn) btn.disabled = false;
      return;
    }

    if (s.status === "FAILURE") {
      setMsg("Failed (Celery FAILURE)");
      if (detailsEl) detailsEl.textContent = JSON.stringify(s, null, 2);
      if (resultsWrap) resultsWrap.style.display = "grid";
      if (btn) btn.disabled = false;
      return;
    }

    setMsg("Status: " + (s.status || "pending") + " ... " + jobId);
    setTimeout(() => poll(jobId), 1200);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

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
      const text = await resp.text();
      setMsg("Request failed. Check logs.");
      if (detailsEl) detailsEl.textContent = text;
      if (resultsWrap) resultsWrap.style.display = "grid";
      if (btn) btn.disabled = false;
      return;
    }

    const data = await resp.json();
    const jobId = data.job_id;

    setMsg("Running... " + jobId);
    poll(jobId);
  });

  resetUI();
})();

