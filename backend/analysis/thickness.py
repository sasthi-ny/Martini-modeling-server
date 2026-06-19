import os
import MDAnalysis as mda
import numpy as np
import matplotlib.pyplot as plt

def calculate_thickness(traj, struct, outdir):
    os.makedirs(outdir, exist_ok=True)

    u = mda.Universe(struct, traj)
    P = u.select_atoms("name P")

    thickness = []

    for ts in u.trajectory:
        z = P.positions[:, 2]
        z_mid = np.median(z)

        z_upper = z[z >= z_mid].mean()
        z_lower = z[z <  z_mid].mean()

        thickness.append(z_upper - z_lower)

    thickness = np.asarray(thickness, dtype=float)

    np.savetxt(f"{outdir}/thickness.csv", thickness)

    plt.figure()
    plt.plot(thickness)
    plt.xlabel("Frame")
    plt.ylabel("Bilayer thickness (Å)")
    plt.tight_layout()
    plt.savefig(f"{outdir}/thickness.png", dpi=200)
    plt.close()

