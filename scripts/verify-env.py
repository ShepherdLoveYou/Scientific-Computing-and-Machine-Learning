"""Verify the SCML conda environment has all critical packages importable.

Run after `conda activate D:\\Conda\\envs\\scml` (or your chosen prefix). Exits 0
if every critical package imports, otherwise prints the first ImportError and
exits 1.
"""
import importlib
import os
import sys

CRITICAL = [
    "numpy", "scipy", "sympy", "pandas", "matplotlib",
    "seaborn", "sklearn",
    "ase", "bqplot", "k3d",
    "ipywidgets", "jupyterlab", "nbconvert",
    "skfem",
]
OPTIONAL = [
    # These live only in the Docker image, not in the Windows conda env.
    # The Windows env doesn't carry them because conda-forge has no Windows build.
    "dolfinx", "lammps",
    # Historical — were in the fat image, now intentionally removed project-wide.
    "torch", "keras",
]


def report(name: str, required: bool) -> bool:
    try:
        mod = importlib.import_module(name)
        version = getattr(mod, "__version__", "?")
        print(f"  [OK]   {name:<14} {version}")
        return True
    except Exception as exc:
        tag = "FAIL" if required else "WARN"
        print(f"  [{tag}] {name:<14} {exc!s}")
        return not required


def main() -> int:
    print(f"Python: {sys.version.split()[0]}  ({sys.executable})")
    print()
    print("Critical packages:")
    ok = all(report(name, required=True) for name in CRITICAL)
    print()
    print("Optional packages (missing is fine; these were stripped during slim build):")
    for name in OPTIONAL:
        report(name, required=False)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
