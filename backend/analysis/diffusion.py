import os
import numpy as np
import matplotlib.pyplot as plt
import MDAnalysis as mda


def calculate_diffusion(traj: str, struct: str, outdir: str):
    """
    Computes lateral diffusion coefficient of lipid residues from COM MSD in xy.
    Outputs:
      - msd_xy.csv: time_ps, msd_A2
      - msd_xy.png
      - diffusion.txt: fitted slope and D
      - methods.txt
    Notes:
      - Requires trajectory to be unwrapped or otherwise continuous for meaningful MSD.
      - Uses time from ts.time if available, otherwise assumes uniform dt via fallback.
    """
    os.makedirs(outdir, exist_ok=True)

    LIPID_RESNAME = "POPC"

    # Fit window in ps
    FIT_TMIN_PS = 2000.0
    FIT_TMAX_PS = 20000.0

    u = mda.Universe(struct, traj)
    lipids = u.select_atoms(f"resname {LIPID_RESNAME}")
    if lipids.n_atoms == 0:
        raise ValueError(f"No atoms found for resname {LIPID_RESNAME}. Update LIPID_RESNAME.")

    residues = lipids.residues
    if len(residues) == 0:
        raise ValueError("No lipid residues detected in selection.")

    # Initial COM positions at first frame
    u.trajectory[0]
    r0 = np.array([res.atoms.center_of_mass() for res in residues], dtype=float)
    x0 = r0[:, 0].copy()
    y0 = r0[:, 1].copy()

    times = []
    msd = []

    # Determine whether ts.time exists
    has_time = True
    try:
        _ = u.trajectory[0].time
    except Exception:
        has_time = False

    # Fallback dt if needed
    dt_ps = None
    if not has_time and len(u.trajectory) >= 2:
        # Try to infer dt from timestep info if present
        dt_ps = 1.0

    for ts in u.trajectory:
        ri = np.array([res.atoms.center_of_mass() for res in residues], dtype=float)
        dx = ri[:, 0] - x0
        dy = ri[:, 1] - y0
        msd_xy = np.mean(dx * dx + dy * dy)

        if has_time:
            t = float(ts.time)
        else:
            # fallback assumes dt_ps and uses frame index
            t = float(ts.frame) * float(dt_ps)

        times.append(t)
        msd.append(msd_xy)

    times = np.asarray(times, dtype=float)
    msd = np.asarray(msd, dtype=float)

    # Save CSV
    csv_path = os.path.join(outdir, "msd_xy.csv")
    np.savetxt(csv_path, np.column_stack([times, msd]), delimiter=",", header="time_ps,msd_A2", comments="")

    # Fit window
    fit_mask = (times >= FIT_TMIN_PS) & (times <= FIT_TMAX_PS)
    if np.count_nonzero(fit_mask) < 2:
        raise ValueError("Not enough points in fit window. Adjust FIT_TMIN_PS and FIT_TMAX_PS.")

    slope, intercept = np.polyfit(times[fit_mask], msd[fit_mask], 1)  # msd = slope*t + intercept
    D_A2_per_ps = slope / 4.0

    # Convert A^2/ps to cm^2/s
    # 1 A^2/ps = 1e-4 cm^2/s
    D_cm2_per_s = D_A2_per_ps * 1.0e-4

    # Plot
    plt.figure()
    plt.plot(times, msd)
    plt.xlabel("Time (ps)")
    plt.ylabel("MSD_xy (Å^2)")
    plt.title(f"MSD_xy ({LIPID_RESNAME})")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "msd_xy.png"), dpi=200)
    plt.close()

    # Save diffusion output
    with open(os.path.join(outdir, "diffusion.txt"), "w") as f:
        f.write(f"lipid_resname: {LIPID_RESNAME}\n")
        f.write(f"fit_tmin_ps: {FIT_TMIN_PS}\n")
        f.write(f"fit_tmax_ps: {FIT_TMAX_PS}\n")
        f.write(f"slope_A2_per_ps: {slope}\n")
        f.write(f"intercept_A2: {intercept}\n")
        f.write(f"D_A2_per_ps: {D_A2_per_ps}\n")
        f.write(f"D_cm2_per_s: {D_cm2_per_s}\n")

    # Methods
    with open(os.path.join(outdir, "methods.txt"), "w") as f:
        f.write("Lateral diffusion from lipid center-of-mass MSD in the xy plane.\n")
        f.write("MSD_xy(t) = <(x(t)-x(0))^2 + (y(t)-y(0))^2> averaged over lipid residues.\n")
        f.write("2D diffusion relation: MSD_xy = 4 D t, so D = slope/4.\n")
        f.write(f"Lipid selection: resname {LIPID_RESNAME}\n")
        f.write(f"Fit window: {FIT_TMIN_PS} to {FIT_TMAX_PS} ps\n")
        f.write("Important: Meaningful MSD requires unwrapped or continuous trajectories.\n")

