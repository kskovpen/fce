import os
import sys


def main():
    # Ensure the package root is in sys.path so relative imports work
    pkg_root = os.path.dirname(os.path.abspath(__file__))
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)

    import runpy
    runpy.run_path(os.path.join(pkg_root, "fce.py"), run_name="__main__")


if __name__ == "__main__":
    main()
