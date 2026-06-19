import os
import uuid

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from backend.celery import celery_app
from backend.tasks import run_workflow

from backend.modeling.polymer_tasks import run_polymer
from backend.modeling.membrane_tasks import run_membrane

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


# ----------------------------
# Analysis workflow
# ----------------------------
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

    run_workflow.apply_async(
        args=[job_id, traj_path, struct_path, analysis_type],
        task_id=job_id,
    )

    return {"job_id": job_id}


# ----------------------------
# Shared status endpoint
# ----------------------------
@app.get("/status/{job_id}")
def status(job_id: str):
    task = celery_app.AsyncResult(job_id)

    if task.state == "SUCCESS":
        return task.result

    # If your task returns {"status":"error", ...} but state is SUCCESS
    # it still lands above, which is fine.
    return {"job_id": job_id, "status": task.state}

# TEMPORARY compatibility alias for older JS polling
@app.get("/model_status/{job_id}")
def model_status(job_id: str):
    return status(job_id)


# ----------------------------
# Polymer modeling (polyply)
# ----------------------------
@app.post("/model")
def model_polymer(
    polymer: str = Form(...),
    martini: str = Form(...),
    chain_length: int = Form(...),
    n_chains: int = Form(...),
    box: str = Form(...),
):
    job_id = str(uuid.uuid4())

    # Queue polymer task. Poll with /status/{job_id}
    run_polymer.apply_async(
        args=[job_id, polymer, martini, chain_length, n_chains, box],
        task_id=job_id,
    )

    return {"job_id": job_id}


# ----------------------------
# Membrane modeling (INSANE)
# ----------------------------
@app.post("/membrane")
def membrane(
    upper_lipid: str = Form(...),
    lower_lipid: str = Form(...),
    box_x: float = Form(...),
    box_y: float = Form(...),
    box_z: float = Form(...),
    salt: float = Form(0.15),
):
    job_id = str(uuid.uuid4())

    run_membrane.apply_async(
        args=[job_id, upper_lipid, lower_lipid, box_x, box_y, box_z, salt],
        task_id=job_id,
    )

    return {
        "job_id": job_id,
        "upper_lipid": upper_lipid,
        "lower_lipid": lower_lipid,
    }

