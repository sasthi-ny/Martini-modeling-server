import os
import MDAnalysis as mda
import numpy as np
import matplotlib.pyplot as plt

def calculate_apl(traj, struct, outdir):
    os.makedirs(outdir, exist_ok=True)

    u = mda.Universe(struct, traj)
    lipids = u.select_atoms("resname POPC DOPE DOPG")

    apl_values = []

    n_lipids = lipids.n_residues

    for ts in u.trajectory:
        box_area = ts.dimensions[0] * ts.dimensions[1]
        apl = box_area / (n_lipids / 2)
        apl_values.append(apl)

    apl_values = np.array(apl_values)

    np.savetxt(os.path.join(outdir, "apl.csv"), apl_values)

    plt.plot(apl_values)
    plt.xlabel("Frame")
    plt.ylabel("Area per lipid (Å²)")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "apl.png"), dpi=300)
    plt.close()

    return apl_values

