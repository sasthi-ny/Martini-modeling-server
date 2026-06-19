import subprocess
from pathlib import Path

from backend.celery import celery_app

ALLOWED_POLYMERS = {"PE", "PP", "PS"}
ALLOWED_MARTINI = {"martini2", "martini3"}

# This is the path INSIDE the CONTAINER.
# You must ensure these files exist in the container at these locations.
TOPPAR_INCLUDE_BY_MARTINI = {
    "martini2": '#include "/app/toppar/martini_v2.0_PEO_PS_CNP.itp"',
    "martini3": '#include "/app/toppar/martini_v3.0.0.itp"',
}

@celery_app.task(name="backend.modeling.run_polymer")
def run_polymer(
    job_id: str,
    polymer: str,
    martini: str,
    chain_length: int,
    n_chains: int,
    box: str,
):
    if polymer not in ALLOWED_POLYMERS:
        return {"job_id": job_id, "status": "error", "error": "Unsupported polymer"}

    if martini not in ALLOWED_MARTINI:
        return {"job_id": job_id, "status": "error", "error": "Unsupported martini selection"}

    box_parts = box.split()
    if len(box_parts) != 3:
        return {"job_id": job_id, "status": "error", "error": "Box must have exactly 3 values like '15 15 15'"}

    # IMPORTANT: write into /app/results so FastAPI can serve it via /results mount
    result_dir = Path(f"/app/results/{job_id}")
    result_dir.mkdir(parents=True, exist_ok=True)

    log_path = result_dir / "log.txt"

    def log(line: str):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    itp_name = f"{polymer}{chain_length}.itp"
    gro_name = f"{polymer}{chain_length}.gro"
    top_name = "topol.top"

    itp_path = result_dir / itp_name
    gro_path = result_dir / gro_name
    top_path = result_dir / top_name

    log(f"job_id: {job_id}")
    log(f"polymer: {polymer}")
    log(f"martini: {martini}")
    log(f"chain_length: {chain_length}")
    log(f"n_chains: {n_chains}")
    log(f"box: {box}")
    log(f"workdir: {result_dir}")

    # Step 1: polyply gen_params
    cmd1 = [
        "polyply",
        "gen_params",
        "-lib", martini,
        "-o", itp_name,
        "-name", polymer,
        "-seq", f"{polymer}:{chain_length}",
    ]
    log("Running: " + " ".join(cmd1))
    r1 = subprocess.run(cmd1, cwd=str(result_dir), capture_output=True, text=True)
    log("stdout:\n" + (r1.stdout or ""))
    log("stderr:\n" + (r1.stderr or ""))
    if r1.returncode != 0:
        return {
            "job_id": job_id,
            "status": "error",
            "error": "polyply gen_params failed",
            "stderr": r1.stderr,
        }

    if not itp_path.exists():
        return {
            "job_id": job_id,
            "status": "error",
            "error": f"Expected {itp_name} was not created",
        }

    # Step 2: write topol.top
    include_line = TOPPAR_INCLUDE_BY_MARTINI[martini]

    # This include points to the ITP we just generated in the same folder
    topol_text = (
        f"{include_line}\n"
        f'#include "{itp_name}"\n'
        "\n"
        "[system]\n"
        "PS in water\n"
        "\n"
        "[molecules]\n"
        "; Compound #mols\n"
        f"{polymer} {n_chains}\n"
    )
    top_path.write_text(topol_text, encoding="utf-8")
    log("Wrote topol.top:\n" + topol_text)

    # Step 3: polyply gen_coords
    cmd2 = [
        "polyply",
        "gen_coords",
        "-p", top_name,
        "-o", gro_name,
        "-name", polymer,
        "-box", box_parts[0], box_parts[1], box_parts[2],
    ]
    log("Running: " + " ".join(cmd2))
    r2 = subprocess.run(cmd2, cwd=str(result_dir), capture_output=True, text=True)
    log("stdout:\n" + (r2.stdout or ""))
    log("stderr:\n" + (r2.stderr or ""))
    if r2.returncode != 0:
        return {
            "job_id": job_id,
            "status": "error",
            "error": "polyply gen_coords failed",
            "stderr": r2.stderr,
        }

    if not gro_path.exists():
        return {
            "job_id": job_id,
            "status": "error",
            "error": f"Expected {gro_name} was not created",
        }

    files = [itp_name, top_name, gro_name, "log.txt"]
    urls = {name: f"/results/{job_id}/{name}" for name in files}

    return {
        "job_id": job_id,
        "status": "success",
        "result_dir": str(result_dir),
        "files": files,
        "urls": urls,
    }

