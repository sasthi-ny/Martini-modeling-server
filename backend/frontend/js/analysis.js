const form = document.getElementById("form");
const runBtn = document.getElementById("runBtn");
const resetBtn = document.getElementById("resetBtn");
const resultsWrap = document.getElementById("results");
const plotEl = document.getElementById("plot");
const methodsEl = document.getElementById("methods");
const detailsEl = document.getElementById("details");
const linksEl = document.getElementById("links");
const msgEl = document.getElementById("msg");
const badge = document.getElementById("statusBadge");

function setBadge(text, kind) {
  badge.textContent = text;
  badge.className = "badge" + (kind ? " " + kind : "");
}

function setMsg(text) {
  msgEl.textContent = text;
}

function resetUI() {
  form.reset();
  resultsWrap.style.display = "none";
  plotEl.removeAttribute("src");
  methodsEl.textContent = "";
  detailsEl.textContent = "";
  linksEl.innerHTML = "";
  setMsg("Ready");
  setBadge("Idle", "");
  runBtn.disabled = false;
}

resetBtn.addEventListener("click", resetUI);

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  runBtn.disabled = true;
  resultsWrap.style.display = "none";
  setMsg("Submitting job...");
  setBadge("Submitting", "warn");

  const fd = new FormData(form);

  let resp;
  try {
    resp = await fetch("/run", { method: "POST", body: fd });
  } catch (err) {
    setBadge("Network error", "bad");
    setMsg("Could not reach the API.");
    runBtn.disabled = false;
    return;
  }

  if (!resp.ok) {
    const text = await resp.text();
    setBadge("Request failed", "bad");
    setMsg("Upload failed. Check server logs.");
    detailsEl.textContent = text;
    resultsWrap.style.display = "grid";
    runBtn.disabled = false;
    return;
  }

  const data = await resp.json();
  const jobId = data.job_id;

  setMsg("Running... " + jobId);
  setBadge("Running", "warn");

  async function poll() {
    const r = await fetch("/status/" + jobId);
    const s = await r.json();

    if (s.status === "success") {
      setBadge("Completed", "good");
      setMsg("Completed");

      // Choose a plot file if present
      const plotUrl =
        s.urls["apl.png"] ||
        s.urls["thickness.png"] ||
        s.urls["scd.png"] ||
        s.urls["msd_xy.png"] ||
        "";

      if (!plotUrl) {
        plotEl.removeAttribute("src");
        plotEl.style.display = "none";
      } else {
        // Force reload even if browser cached an older image at same path
        plotEl.onload = () => {
          plotEl.style.display = "block";
        };
        plotEl.onerror = () => {
          setBadge("Plot load failed", "bad");
          setMsg("Could not load plot image. Check URL and logs.");
        };

        plotEl.src = plotUrl + "?t=" + Date.now();
      }
      // Methods
      if (s.urls["methods.txt"]) {
        const m = await fetch(s.urls["methods.txt"]);
        methodsEl.textContent = await m.text();
      } else {
        methodsEl.textContent = "No methods.txt found.";
      }

      // Details and downloads
      detailsEl.textContent = JSON.stringify(
        { job_id: s.job_id, analysis: s.analysis, result_dir: s.result_dir },
        null,
        2
      );

      linksEl.innerHTML = "";
      for (const name of (s.files || [])) {
        const url = s.urls[name];
        if (!url) continue;
        const a = document.createElement("a");
        a.href = url;
        a.textContent = name;
        a.target = "_blank";
        linksEl.appendChild(a);
      }

      resultsWrap.style.display = "grid";
      runBtn.disabled = false;
      return;
    }

    setMsg("Status: " + (s.status || "pending") + " ... " + jobId);
    setTimeout(poll, 1200);
  }

  poll();
});

setBadge("Idle", "");

  // ----------------------------
  // Modeling section
  // ----------------------------
  const modelForm = document.getElementById("modelForm");
  const modelBtn = document.getElementById("modelBtn");
  const modelResetBtn = document.getElementById("modelResetBtn");
  const modelResults = document.getElementById("modelResults");
  const modelPlot = document.getElementById("modelPlot");
  const modelLog = document.getElementById("modelLog");
  const modelDetails = document.getElementById("modelDetails");
  const modelLinks = document.getElementById("modelLinks");
  const modelMsg = document.getElementById("modelMsg");

  function modelSetMsg(t) { modelMsg.textContent = t; }

  function modelResetUI() {
    modelForm.reset();
    modelResults.style.display = "none";
    modelPlot.removeAttribute("src");
    modelLog.textContent = "";
    modelDetails.textContent = "";
    modelLinks.innerHTML = "";
    modelSetMsg("Ready");
    modelBtn.disabled = false;
  }

  if (modelResetBtn) modelResetBtn.addEventListener("click", modelResetUI);

  if (modelForm) {
    modelForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      modelBtn.disabled = true;
      modelResults.style.display = "none";
      modelSetMsg("Submitting job...");

      const fd = new FormData(modelForm);

      let resp;
      try {
        resp = await fetch("/model", { method: "POST", body: fd });
      } catch {
        modelSetMsg("Could not reach the API.");
        modelBtn.disabled = false;
        return;
      }

      if (!resp.ok) {
        modelSetMsg("Request failed. Check logs.");
        modelBtn.disabled = false;
        return;
      }

      const data = await resp.json();
      const jobId = data.job_id;
      modelSetMsg("Running... " + jobId);

      async function pollModel() {
        const r = await fetch("/status/" + jobId);
        const s = await r.json();

        if (s.status === "success") {
          modelSetMsg("Completed");

          // Optional preview image, if you generate one
          const preview =
            (s.urls && (s.urls["preview.png"] || s.urls["cg.png"])) || "";

          if (preview) {
            modelPlot.src = preview + "?t=" + Date.now();
            modelPlot.style.display = "block";
          } else {
            modelPlot.style.display = "none";
          }

          if (s.urls && s.urls["log.txt"]) {
            const m = await fetch(s.urls["log.txt"]);
            modelLog.textContent = await m.text();
          } else {
            modelLog.textContent = "No log.txt found.";
          }

          modelDetails.textContent = JSON.stringify(
            { job_id: s.job_id, model_type: s.model_type, result_dir: s.result_dir },
            null,
            2
          );

          modelLinks.innerHTML = "";
          for (const name of (s.files || [])) {
            const url = s.urls[name];
            if (!url) continue;
            const a = document.createElement("a");
            a.href = url;
            a.textContent = name;
            a.target = "_blank";
            modelLinks.appendChild(a);
          }

          modelResults.style.display = "grid";
          modelBtn.disabled = false;
          return;
        }

        modelSetMsg("Status: " + (s.status || "pending") + " ... " + jobId);
        setTimeout(pollModel, 1200);
      }

      pollModel();
    });
  }

