(function () {
  const form = document.getElementById("membraneForm");
  if (!form) return;

  const btn = document.getElementById("membraneBtn");
  const resetBtn = document.getElementById("membraneResetBtn");

  const msgEl = document.getElementById("membraneMsg");
  const resultsWrap = document.getElementById("membraneResults");
  const detailsEl = document.getElementById("membraneDetails");
  const linksEl = document.getElementById("membraneLinks");
  const logEl = document.getElementById("membraneLog");

  function setMsg(t) {
    if (msgEl) msgEl.textContent = t;
  }

  function resetUI() {
    form.reset();
    if (resultsWrap) resultsWrap.style.display = "none";
    if (detailsEl) detailsEl.textContent = "";
    if (linksEl) linksEl.innerHTML = "";
    if (logEl) logEl.textContent = "";
    setMsg("Ready");
    if (btn) btn.disabled = false;
  }

  if (resetBtn) resetBtn.addEventListener("click", resetUI);

  async function poll(jobId) {
    const r = await fetch("/status/" + jobId);
    const s = await r.json();

    // Celery states: PENDING, STARTED, SUCCESS, FAILURE
    // Your tasks return: {status:"success"| "error"| ...}
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

      if (resultsWrap) resultsWrap.style.display = "block";
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

      if (resultsWrap) resultsWrap.style.display = "block";
      if (btn) btn.disabled = false;
      return;
    }

    // Celery meta fallback
    if (s.status === "FAILURE") {
      setMsg("Failed (Celery FAILURE)");
      if (detailsEl) detailsEl.textContent = JSON.stringify(s, null, 2);
      if (resultsWrap) resultsWrap.style.display = "block";
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
    setMsg("Submitting membrane job...");

    const fd = new FormData(form);

    let resp;
    try {
      resp = await fetch("/membrane", { method: "POST", body: fd });
    } catch (err) {
      setMsg("Network error. Could not reach API.");
      if (btn) btn.disabled = false;
      return;
    }

    if (!resp.ok) {
      const text = await resp.text();
      setMsg("Request failed. Check logs.");
      if (detailsEl) detailsEl.textContent = text;
      if (resultsWrap) resultsWrap.style.display = "block";
      if (btn) btn.disabled = false;
      return;
    }

    const data = await resp.json();
    const jobId = data.job_id;

    setMsg("Running... " + jobId);
    poll(jobId);
  });

  // initial
  resetUI();
})();

