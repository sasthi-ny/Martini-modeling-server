import os
import uuid

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from backend.celery import celery_app
from backend.tasks import run_workflow
from backend.modeling.polymer_tasks import run_polymer
from backend.modeling.membrane_tasks import run_membrane

from fastapi import Form

app = FastAPI()

# ----------------------------
# Directories
# ----------------------------
BASE_DIR = "/app"
UPLOAD_DIR = os.path.join(BASE_DIR, "data")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Serve generated result files
app.mount("/results", StaticFiles(directory=RESULTS_DIR), name="results")

# Serve frontend static assets
app.mount("/static", StaticFiles(directory="backend/frontend"), name="static")


@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse("backend/frontend/index.html")


@app.post("/run")
async def run_analysis(
    trajectory: UploadFile = File(...),
    structure: UploadFile = File(...),
    analysis_type: str = Form(...),
):
    job_id = str(uuid.uuid4())

    traj_path = os.path.join(UPLOAD_DIR, f"{job_id}.xtc")
    struct_path = os.path.join(UPLOAD_DIR, f"{job_id}.gro")

    with open(traj_path, "wb") as f:
        f.write(await trajectory.read())

    with open(struct_path, "wb") as f:
        f.write(await structure.read())

    # Make Celery task id equal to job_id so /status/{job_id} works
    run_workflow.apply_async(
        args=[job_id, traj_path, struct_path, analysis_type],
        task_id=job_id,
    )

    return {"job_id": job_id}


@app.get("/status/{job_id}")
def status(job_id: str):
    task = celery_app.AsyncResult(job_id)

    if task.state == "SUCCESS":
        return task.result

    return {"job_id": job_id, "status": task.state}


@app.get("/view/{job_id}", response_class=HTMLResponse)
def view(job_id: str):
    task = celery_app.AsyncResult(job_id)
    if task.state != "SUCCESS":
        return f"<html><body><h3>Status: {task.state}</h3></body></html>"

    result = task.result or {}
    urls = result.get("urls", {})
    plot = urls.get("apl.png") or urls.get("thickness.png") or ""
    methods = urls.get("methods.txt", "")

    return f"""
    <html>
      <body style="font-family: system-ui; padding: 16px;">
        <h2>Job {job_id}</h2>
        <img src="{plot}" style="max-width: 100%; border: 1px solid #ddd;" />
        <h3>Methods</h3>
        <pre id="m">Loading...</pre>
        <script>
          fetch("{methods}").then(r => r.text()).then(t => document.getElementById("m").textContent = t);
        </script>
      </body>
    </html>
    """

@app.post("/model")
async def run_model(
    structure: UploadFile = File(...),
    model_type: str = Form(...),
    ps_length: int = Form(25),
):
    job_id = str(uuid.uuid4())

    job_dir = os.path.join(UPLOAD_DIR, f"model_{job_id}")
    os.makedirs(job_dir, exist_ok=True)

    struct_path = os.path.join(job_dir, structure.filename)
    with open(struct_path, "wb") as f:
        f.write(await structure.read())

    # Task id equals job_id for clean polling
    run_modeling.apply_async(
        args=[job_id, struct_path, model_type, ps_length],
        task_id=job_id,
    )

    return {"job_id": job_id}


@app.get("/model_status/{job_id}")
def model_status(job_id: str):
    task = celery_app.AsyncResult(job_id)

    if task.state == "SUCCESS":
        return task.result

    return {"job_id": job_id, "status": task.state}

@app.post("/model")
async def run_model(
    polymer: str = Form(...),
    martini: str = Form(...),
    chain_length: int = Form(...),
    n_chains: int = Form(...),
    box: str = Form(...),
):
    job_id = str(uuid.uuid4())

    job_dir = os.path.join(UPLOAD_DIR, f"model_{job_id}")
    os.makedirs(job_dir, exist_ok=True)

    # Store inputs so the worker can read them safely if needed
    params_path = os.path.join(job_dir, "params.txt")
    with open(params_path, "w") as f:
        f.write(f"polymer={polymer}\n")
        f.write(f"martini={martini}\n")
        f.write(f"chain_length={chain_length}\n")
        f.write(f"n_chains={n_chains}\n")
        f.write(f"box={box}\n")

    from backend.modeling.tasks import run_modeling
    run_modeling.apply_async(
        args=[job_id, polymer, martini, chain_length, n_chains, box],
        task_id=job_id,
    )

    return {"job_id": job_id}


@app.get("/model_status/{job_id}")
def model_status(job_id: str):
    task = celery_app.AsyncResult(job_id)

    if task.state == "SUCCESS":
        return task.result

    return {"job_id": job_id, "status": task.state}

@app.post("/model")
def model(
    polymer: str = Form(...),
    martini: str = Form(...),
    chain_length: int = Form(...),
    n_chains: int = Form(...),
    box: str = Form(...),
):
    job_id = str(uuid.uuid4())

    # enqueue your celery modeling task
    run_modeling.apply_async(
        args=[job_id, polymer, martini, chain_length, n_chains, box],
        task_id=job_id,
    )

    return {"job_id": job_id}

from fastapi import Form
import uuid

@app.post("/membrane")
def membrane(
    lipid: str = Form(...),
    box_x: float = Form(...),
    box_y: float = Form(...),
    box_z: float = Form(...),
):
    job_id = str(uuid.uuid4())
    run_membrane.apply_async(args=[job_id, lipid, box_x, box_y, box_z], task_id=job_id)
    return {"job_id": job_id}
