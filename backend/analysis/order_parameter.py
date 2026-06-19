import os
import numpy as np
import matplotlib.pyplot as plt
import MDAnalysis as mda


def calculate_order_parameter(traj: str, struct: str, outdir: str):
    """
    Computes SCD along lipid tails from bond vectors vs bilayer normal (z).
    Outputs:
      - scd.csv: columns = tail, bond_index, atom_i, atom_j, SCD
      - scd.png: simple line plot of SCD vs bond index for each tail
      - methods.txt
    """
    os.makedirs(outdir, exist_ok=True)

    # Edit these to match your lipid atom naming
    LIPID_RESNAME = "POPC"

    # Example placeholders. You MUST replace these with your atom names.
    # Provide the ordered carbon names along the sn1 and sn2 chains.
    TAIL1_NAMES = ["C31", "C32", "C33", "C34", "C35", "C36", "C37", "C38", "C39", "C310", "C311", "C312", "C313", "C314", "C315", "C316"]
    TAIL2_NAMES = ["C21", "C22", "C23", "C24", "C25", "C26", "C27", "C28", "C29", "C210", "C211", "C212", "C213", "C214", "C215", "C216", "C217", "C218"]

    u = mda.Universe(struct, traj)

    lipids = u.select_atoms(f"resname {LIPID_RESNAME}")
    if lipids.n_atoms == 0:
        raise ValueError(f"No atoms found for resname {LIPID_RESNAME}. Update LIPID_RESNAME.")

    residues = lipids.residues
    if len(residues) == 0:
        raise ValueError("No lipid residues detected in selection.")

    def scd_for_tail(atom_names):
        # For each bond i->i+1, accumulate cos^2(theta) over frames and residues
        nbonds = len(atom_names) - 1
        sum_cos2 = np.zeros(nbonds, dtype=float)
        count = np.zeros(nbonds, dtype=int)

        for ts in u.trajectory:
            # Precompute z-axis unit vector
            # cos(theta) = vz / |v|
            for res in residues:
                # For speed, try to grab all required atoms in one go
                # If naming is inconsistent, skip that residue for this frame
                try:
                    coords = []
                    for name in atom_names:
                        ag = res.atoms.select_atoms(f"name {name}")
                        if ag.n_atoms != 1:
                            raise KeyError
                        coords.append(ag.positions[0].copy())
                    coords = np.asarray(coords, dtype=float)
                except KeyError:
                    continue

                vecs = coords[1:] - coords[:-1]  # shape (nbonds, 3)
                norms = np.linalg.norm(vecs, axis=1)
                valid = norms > 0

                cosT = np.zeros(nbonds, dtype=float)
                cosT[valid] = vecs[valid, 2] / norms[valid]  # z component over norm
                cos2 = cosT * cosT

                sum_cos2 += cos2
                count += 1

        # Avoid division by zero
        scd = np.full(nbonds, np.nan, dtype=float)
        valid = count > 0
        scd[valid] = 0.5 * (3.0 * (sum_cos2[valid] / count[valid]) - 1.0)
        return scd

    scd1 = scd_for_tail(TAIL1_NAMES)
    scd2 = scd_for_tail(TAIL2_NAMES)

    # Save CSV
    csv_path = os.path.join(outdir, "scd.csv")
    with open(csv_path, "w") as f:
        f.write("tail,bond_index,atom_i,atom_j,scd\n")
        for i in range(len(TAIL1_NAMES) - 1):
            f.write(f"tail1,{i},{TAIL1_NAMES[i]},{TAIL1_NAMES[i+1]},{scd1[i]}\n")
        for i in range(len(TAIL2_NAMES) - 1):
            f.write(f"tail2,{i},{TAIL2_NAMES[i]},{TAIL2_NAMES[i+1]},{scd2[i]}\n")

    # Plot
    scd1 = np.asarray(scd1, dtype=float)
    scd2 = np.asarray(scd2, dtype=float)

    plt.figure(figsize=(8, 4))
    plt.plot(np.arange(len(scd1)), scd1, marker="o", label="tail1")
    plt.plot(np.arange(len(scd2)), scd2, marker="o", label="tail2")
    plt.xlabel("Bond index along tail")
    plt.ylabel("SCD")
    plt.title(f"Order parameter SCD ({LIPID_RESNAME})")
    plt.ylim(-0.2, 0.45)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "scd.png"), dpi=200)
    plt.close()


    # Methods
    methods_path = os.path.join(outdir, "methods.txt")
    with open(methods_path, "w") as f:
        f.write("Order parameter SCD computed from tail bond vectors vs bilayer normal (z-axis).\n")
        f.write("Definition: SCD = 0.5 * (3 <cos^2(theta)> - 1).\n")
        f.write("theta is the angle between each bond vector and the z axis.\n")
        f.write(f"Lipid selection: resname {LIPID_RESNAME}\n")
        f.write(f"Tail1 atom names: {TAIL1_NAMES}\n")
        f.write(f"Tail2 atom names: {TAIL2_NAMES}\n")
        f.write("Assumes bilayer normal aligned with z axis.\n")

