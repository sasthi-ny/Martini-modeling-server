import subprocess
from pathlib import Path

from backend.celery import celery_app

ALLOWED_LIPIDS = {
    "POPC", "DPPC", "POPE",
    "DOPC", "DOPE", "POPS", "DOPS",
    "POPG", "DOPG",
    "CHOL"
}  # extend later if needed

@celery_app.task(name="backend.modeling.run_membrane")
def run_membrane(
    job_id: str,
    lipid: str,
    box_x: float,
    box_y: float,
    box_z: float,
    salt: float = 0.15,
):
    if lipid not in ALLOWED_LIPIDS:
        return {
            "job_id": job_id,
            "status": "error",
            "error": f"Unsupported lipid: {lipid}",
        }

    # Results must live here so FastAPI can serve them
    result_dir = Path(f"/app/results/{job_id}")
    result_dir.mkdir(parents=True, exist_ok=True)

    out_gro = f"{lipid}_solv_ions.gro"
    log_path = result_dir / "log.txt"

    def log(msg: str):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    cmd = [
        "insane",
        "-salt", str(salt),
        "-x", str(box_x),
        "-y", str(box_y),
        "-z", str(box_z),
        "-sol", "W",
        "-o", out_gro,
        "-l", lipid,
        "-u", lipid,
    ]

    log("Running INSANE command:")
    log(" ".join(cmd))

    r = subprocess.run(
        cmd,
        cwd=str(result_dir),
        capture_output=True,
        text=True,
    )

    log("stdout:")
    log(r.stdout or "")
    log("stderr:")
    log(r.stderr or "")

    if r.returncode != 0:
        return {
            "job_id": job_id,
            "status": "error",
            "error": "INSANE failed",
            "stderr": r.stderr,
        }

    out_path = result_dir / out_gro
    if not out_path.exists():
        return {
            "job_id": job_id,
            "status": "error",
            "error": "Expected output file was not created",
        }

    files = [out_gro, "log.txt"]
    urls = {name: f"/results/{job_id}/{name}" for name in files}

    return {
        "job_id": job_id,
        "status": "success",
        "lipid": lipid,
        "box": [box_x, box_y, box_z],
        "files": files,
        "urls": urls,
    }

