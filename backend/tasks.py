import os
from backend.celery import celery_app
from backend.analysis.apl import calculate_apl
from backend.analysis.thickness import calculate_thickness
from backend.report import generate_methods
from backend.analysis.order_parameter import calculate_order_parameter
from backend.analysis.diffusion import calculate_diffusion

@celery_app.task(name="backend.tasks.run_workflow")
def run_workflow(job_id, traj, struct, analysis_type):
    result_dir = f"/app/results/{job_id}"
    os.makedirs(result_dir, exist_ok=True)

    if analysis_type == "apl":
        calculate_apl(traj, struct, result_dir)

    elif analysis_type == "thickness":
        calculate_thickness(traj, struct, result_dir)

    elif analysis_type == "order_parameter":
        calculate_order_parameter(traj, struct, result_dir)

    elif analysis_type == "diffusion":
        calculate_diffusion(traj, struct, result_dir)

    else:
        raise ValueError(f"Unknown analysis_type: {analysis_type}")

    generate_methods(analysis_type, result_dir)

    files = sorted(os.listdir(result_dir))
    urls = {name: f"/results/{job_id}/{name}" for name in files}

    return {
        "job_id": job_id,
        "analysis": analysis_type,
        "status": "success",
        "result_dir": result_dir,
        "files": files,
        "urls": urls
        }
