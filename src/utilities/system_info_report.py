import platform
import sys
import subprocess
from pathlib import Path

import psutil
import cpuinfo


def get_windows_name() -> str:
    version = platform.version()

    if version.startswith("10.0.22") or version.startswith("10.0.26"):
        return "Windows 11"

    return f"{platform.system()} {platform.release()}"


def get_package_version(package_name: str) -> str:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            capture_output=True,
            text=True,
            check=False,
        )

        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.replace("Version:", "").strip()

        return "Not installed"

    except Exception as ex:
        return f"Could not determine ({ex})"


def print_system_info() -> None:
    cpu = cpuinfo.get_cpu_info()

    print("\n=== COMPUTATIONAL ENVIRONMENT ===")

    print(f"Operating System : {get_windows_name()}")
    print(f"OS Version       : {platform.version()}")

    print(f"CPU              : {cpu['brand_raw']}")
    print(f"Physical Cores   : {psutil.cpu_count(logical=False)}")
    print(f"Logical Cores    : {psutil.cpu_count(logical=True)}")

    ram_gb = round(psutil.virtual_memory().total / (1024**3), 2)
    print(f"RAM              : {ram_gb} GB")

    print(f"Python Version   : {platform.python_version()}")

    print("\n=== PACKAGE VERSIONS ===")

    packages = [
        "gurobipy",
        "pandas",
        "numpy",
        "matplotlib",
        "seaborn",
        "pandapower",
    ]

    for package in packages:
        print(f"{package:<12}: {get_package_version(package)}")

    print("\n=== PROJECT PATH ===")
    print(f"Project Root     : {Path(__file__).resolve().parents[2]}")


if __name__ == "__main__":
    print_system_info()