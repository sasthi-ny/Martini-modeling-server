def generate_methods(analysis_type, outdir):
    text = f"""
Molecular dynamics trajectories were analyzed using MDAnalysis.
The {analysis_type} was calculated for each frame after equilibration.
Time series were averaged over the production run.
"""

    with open(f"{outdir}/methods.txt", "w") as f:
        f.write(text.strip())

