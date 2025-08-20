import shutil
import subprocess
import inquirer
import os
import sys
import platform

# Fun color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

# Detect platform and adjust python candidates
system = platform.system()
if system == "Windows":
    python_names = ["py", "python", "python3"]
elif system == "Darwin":
    python_names = ["python3", "python"]
else:  # Assume Linux/Unix
    python_names = ["python3", "python"]

python_candidates = []
for name in python_names:
    path = shutil.which(name)
    if path:
        try:
            version = subprocess.check_output(
                [path, "--version"], stderr=subprocess.STDOUT
            )
            version = version.decode().strip()
            python_candidates.append(f"{CYAN}{version}{RESET} ({YELLOW}{path}{RESET})")
        except Exception:
            pass

def parse_args():
    """Parse CLI arguments for python path and clyp version."""
    python_path = None
    clyp_version = None
    uninstall = False
    silent = False
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--python", "-p") and i + 1 < len(args):
            python_path = args[i + 1]
            i += 1
        elif arg in ("--version", "-v") and i + 1 < len(args):
            clyp_version = args[i + 1]
            i += 1
        elif arg in ("--uninstall", "-u"):
            uninstall = True
        elif arg in ("--silent", "-s"):
            silent = True
        i += 1
    return python_path, clyp_version, uninstall, silent

def main():
    uninstall = False
    silent = False
    python_path_arg, clyp_version_arg, uninstall, silent = parse_args()

    if not python_candidates and not python_path_arg:
        print(f"{RED}No Python installations found.{RESET}")
        return

    # If --python is specified, use it directly (skip prompt)
    if python_path_arg:
        path = python_path_arg
        # Optionally, check if path exists and is executable
        if not shutil.which(path):
            print(f"{RED}Specified Python executable not found: {path}{RESET}")
            return
        selected = None
    elif silent:
        # Use first candidate and default actions
        selected = python_candidates[0]
        path = selected.split("(")[-1].strip(")").replace(YELLOW, "").replace(RESET, "")
    else:
        questions = [
            inquirer.List(
                "python_choice",
                message=f"{GREEN}Select the Python installation to use{RESET}",
                choices=python_candidates,
            ),
        ]
        if not uninstall:
            questions.append(
                inquirer.List(
                    "version_choice",
                    message=f"{GREEN}Choose a version of Clyp to install{RESET}",
                    choices=[
                        f"{CYAN}Latest (recommended){RESET}",
                        f"{YELLOW}Specify version...{RESET}",
                    ],
                )
            )
        answers = inquirer.prompt(questions)
        selected = answers["python_choice"]
        # Extract path from colored string
        path = selected.split("(")[-1].strip(")").replace(YELLOW, "").replace(RESET, "")

    # Determine uninstall/install logic
    if uninstall:
        pip_cmd = f"{path} -m pip uninstall -y clyp"
        try:
            os.system(pip_cmd)
        except Exception:
            os.system(f"{path} -m pip3 uninstall -y clyp")
        print(f"\n{GREEN}Clyp has been uninstalled!{RESET}\n")
        return

    # Determine version to install
    if clyp_version_arg:
        clyp_version = clyp_version_arg.strip()
        pip_cmd = f"{path} -m pip install clyp=={clyp_version}"
    elif not silent and not python_path_arg:
        # Only prompt if not silent and not using --python
        if "Specify version" in answers.get("version_choice", ""):
            version_answer = inquirer.prompt(
                [
                    inquirer.Text(
                        "clyp_version",
                        message=f"{GREEN}Enter the Clyp version (e.g. 1.2.3){RESET}",
                    )
                ]
            )
            clyp_version = version_answer["clyp_version"].strip()
            pip_cmd = f"{path} -m pip install clyp=={clyp_version}"
        else:
            pip_cmd = f"{path} -m pip install clyp"
    else:
        pip_cmd = f"{path} -m pip install clyp"

    try:
        # Try pip first
        os.system(pip_cmd)
    except Exception:
        # Try pip3 as fallback
        if "==" in pip_cmd:
            os.system(f"{path} -m pip3 install clyp=={clyp_version}")
        else:
            os.system(f"{path} -m pip3 install clyp")
    print(f"\n{GREEN}Clyp is now installed! Restart your shell to use it.{RESET}\n")

if __name__ == "__main__":
    main()
