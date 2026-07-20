import subprocess
import tempfile
import os
import uuid
import base64
import re
from rich.syntax import Syntax
from pathlib import Path
import shutil
import threading
import time
import sys  # NEW: for sys.executable



# Global configuration
USE_APPTAINER = False
APPTAINER_IMAGE_NAME = "python_3.10-slim.sif"
APPTAINER_DOCKER_URI = "docker://python:3.10-slim"


# Global synchronization for home2 copy operation
home2_copy_lock = threading.Lock()
home2_copy_active = threading.Event()  # False when copy is not running



def set_use_apptainer(value: bool) -> None:
    """Setter so other modules can control whether Apptainer is used."""
    global USE_APPTAINER
    USE_APPTAINER = bool(value)



def is_base64_image(s: str) -> bool:
    if not s or len(s) < 100:
        return False
    s_clean = "".join(s.split())
    if len(s_clean) % 4 != 0:
        return False
    if not re.fullmatch(r"[A-Za-z0-9+/=]+", s_clean):
        return False
    try:
        decoded = base64.b64decode(s_clean, validate=True)
        if decoded.startswith(b"\x89PNG") or decoded.startswith(b"\xFF\xD8"):
            return True
        return False
    except Exception:
        return False



def wait_for_home2_copy_complete(timeout=30.0):
    """Wait for home2 async copy to complete, checking every 100ms."""
    if home2_copy_lock.acquire(blocking=False):
        # No copy is running, immediately release and return
        home2_copy_lock.release()
        return True
    
    # Copy is running, wait for it to complete
    deadline = time.time() + timeout
    while time.time() < deadline:
        if home2_copy_lock.acquire(blocking=False):
            # Copy just completed, release lock and return
            home2_copy_lock.release()
            return True
        time.sleep(0.1)  # 100ms
    
    return False



def ensure_apptainer_image() -> Path:
    """
    Ensure the Apptainer .sif image exists in the current working directory.
    If not present, pull it from the specified docker:// URI.
    """
    image_path = Path.cwd() / APPTAINER_IMAGE_NAME
    if image_path.exists():
        return image_path

    result = subprocess.run(
        ["apptainer", "pull", str(image_path), APPTAINER_DOCKER_URI],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to pull Apptainer image ({APPTAINER_DOCKER_URI}). "
            f"Output:\n{result.stdout}"
        )
    return image_path

# Uncomment this version of run_python_in_docker if you want to restore the original sandboxed behavior using Docker or Apptainer.
# def run_python_in_docker(code: str, data_dir: Path = None):
#     tmpdir = tempfile.mkdtemp()
#     script_path = os.path.join(tmpdir, "script.py")
    
#     with open(script_path, "w") as f:
#         f.write(code)


#     use_apptainer = USE_APPTAINER


#     base_dir = Path(__file__).parent
#     base_home_dir = base_dir / "apptainer_base_home"
#     home1 = base_dir / "apptainer_home_1"
#     home2 = base_dir / "apptainer_home_2"


#     #
#     # Async utilities - MODIFIED to use global lock
#     #
#     def async_task(func):
#         t = threading.Thread(target=func, daemon=True)
#         t.start()


#     def async_delete(path: Path):
#         def _delete():
#             try:
#                 shutil.rmtree(path)
#             except Exception as e:
#                 pass
#         async_task(_delete)


#     def async_copy_base_to_home2():
#         """Async copy with proper lock acquisition."""
#         def _copy():
#             try:
#                 # Acquire lock (blocks until previous copy completes)
#                 home2_copy_lock.acquire()
#                 home2_copy_active.set()  # Signal copy is active
                
#                 if home2.exists():
#                     shutil.rmtree(home2)
                
#                 clone_home(base_home_dir, home2)
                
#             except Exception as e:
#                 pass
#             finally:
#                 home2_copy_active.clear()  # Clear active flag
#                 home2_copy_lock.release()  # Always release lock
        
#         async_task(_copy)


#     def clone_home(source: Path, dest: Path):
#         """Literal copy of directory contents using working tar pipe method."""
#         if dest.exists():
#             shutil.rmtree(dest)
#         dest.mkdir(parents=True, exist_ok=True)
        
#         # Exact bash: rm -rf dest && mkdir -p dest && tar cf - -C source . | tar xf - -C dest
#         tar_cmd = ["tar", "cf", "-", "-C", str(source), "."]
#         extract_cmd = ["tar", "xf", "-", "-C", str(dest)]
        
#         proc1 = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE, text=False)
#         proc2 = subprocess.Popen(extract_cmd, stdin=proc1.stdout, cwd=str(dest))
#         proc1.stdout.close()
        
#         proc1.wait()
#         proc2.wait()
        
#         if proc1.returncode != 0 or proc2.returncode != 0:
#             raise RuntimeError(f"tar clone failed: proc1={proc1.returncode}, proc2={proc2.returncode}")

#     #
#     # Main logic branch
#     #
#     if use_apptainer:
        
#         # Ensure Apptainer image exists
#         try:
#             sif_path = ensure_apptainer_image()
#         except Exception as e:
#             return {
#                 "success": False,
#                 "output": f"Error ensuring Apptainer image: {e}",
#                 "is_image": False,
#             }


#         # One-time setup of base Apptainer home
#         if not (base_home_dir.exists() and home1.exists() and home2.exists()):
#             os.makedirs(base_home_dir, exist_ok=True)
            
#             setup_cmd = [
#                 "apptainer", "exec",
#                 "--cleanenv", "--containall", "--no-home",
#                 "--pwd", "/tmp",
#                 "--bind", f"{base_home_dir}:/home",
#                 "--home", f"{base_home_dir}:/home",
#                 str(sif_path),
#                 "bash", "-c",
#                 "python -m venv /home/venv && "
#                 "source /home/venv/bin/activate && "
#                 "pip install --cache-dir /home/.cache/pip -q uv"
#             ]
            
#             result = subprocess.run(setup_cmd, capture_output=True, text=True)
            
#             if result.returncode != 0:
#                 return {
#                     "success": False,
#                     "output": f"Error setting up Apptainer base home: {result.stdout or result.stderr}",
#                     "is_image": False,
#                 }


#             clone_home(base_home_dir, home1)
#             clone_home(base_home_dir, home2)


#         # Compose Apptainer exec command for code
#         apptainer_cmd = [
#             "apptainer", "exec",
#             "--cleanenv", "--containall", "--no-home",
#             "--pwd", "/tmp",
#             "--bind", f"{home1}:/home",
#             "--home", f"{base_home_dir}:/home",
#             "--bind", f"{tmpdir}:/tmp:ro",
#             str(sif_path),
#             "bash", "-c",
#             "source /home/venv/bin/activate && python -u /tmp/script.py",
#         ]
#         cmd = apptainer_cmd


#     else:
#         # Docker path (unchanged)
#         container_name = f"code-runner-{uuid.uuid4().hex[:8]}"
#         docker_cmd = [
#             "docker", "run", "--rm",
#             "-v", f"{script_path}:/tmp/script.py:ro",
#         ]
#         if data_dir is not None:
#             docker_cmd.extend(["-v", f"{data_dir}:/data:ro"])
#         docker_cmd.extend([
#             "--name", container_name,
#             "python:3.10-slim",
#             "python", "-u", "/tmp/script.py",
#         ])
#         cmd = docker_cmd


#     #
#     # Run and collect results
#     #
#     try:
#         result = subprocess.run(
#             cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
#         )
#         success = (result.returncode == 0)
#         output = result.stdout
#         is_image = is_base64_image(output) if success else False
#         return {"success": success, "output": output, "is_image": is_image}


#     except Exception as e:
#         import traceback
#         return {"success": False, "output": f"subprocess exception: {e}", "is_image": False}


#     finally:
#         try:
#             # Always clean temp script directory
#             os.remove(script_path)
#             os.rmdir(tmpdir)


#             if use_apptainer:
                
#                 # CRITICAL: Wait for any home2 copy to complete before rotation
#                 if not wait_for_home2_copy_complete():
#                     pass
                
#                 # Rotate/cleanup environment homes
#                 if home1.exists():
#                     # Move old home1 to temp dir for async deletion
#                     tmp_delete_path = base_dir / f"delete_home_{uuid.uuid4().hex[:8]}"
#                     home1.rename(tmp_delete_path)
#                     async_delete(tmp_delete_path)


#                 # Promote home2 → home1 (now safe - home2 copy is complete)
#                 if home2.exists():
#                     home2.rename(home1)


#                 # Recreate new home2 asynchronously from base
#                 async_copy_base_to_home2()


#         except Exception as e:
#             import traceback
#             pass


# This Modified version DOES NOT SANDBOX CODE WHEN USING DOCKER!!  
# This is a temporary fix for usage in the pearc tutorial where
# the students are expected to be running the agent in a docker container
# locally which provides adequate isolation.
def run_python_in_docker(code: str, data_dir: Path = None):
    """
    Updated: execute the provided Python code directly in the current container
    by writing it to a temporary script and invoking the current interpreter.
    """
    tmpdir = tempfile.mkdtemp()
    script_path = os.path.join(tmpdir, "script.py")
    
    with open(script_path, "w") as f:
        f.write(code)

    # You could still use USE_APPTAINER here to select an alternate interpreter or env,
    # but per request we no longer spawn a separate Docker/Apptainer container.
    use_apptainer = USE_APPTAINER

    base_dir = Path(__file__).parent
    base_home_dir = base_dir / "apptainer_base_home"
    home1 = base_dir / "apptainer_home_1"
    home2 = base_dir / "apptainer_home_2"

    #
    # Async utilities - unchanged
    #
    def async_task(func):
        t = threading.Thread(target=func, daemon=True)
        t.start()

    def async_delete(path: Path):
        def _delete():
            try:
                shutil.rmtree(path)
            except Exception:
                pass
        async_task(_delete)

    def async_copy_base_to_home2():
        """Async copy with proper lock acquisition."""
        def _copy():
            try:
                home2_copy_lock.acquire()
                home2_copy_active.set()  # Signal copy is active
                
                if home2.exists():
                    shutil.rmtree(home2)
                
                clone_home(base_home_dir, home2)
            except Exception:
                pass
            finally:
                home2_copy_active.clear()
                home2_copy_lock.release()
        
        async_task(_copy)

    def clone_home(source: Path, dest: Path):
        """Literal copy of directory contents using working tar pipe method."""
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        
        tar_cmd = ["tar", "cf", "-", "-C", str(source), "."]
        extract_cmd = ["tar", "xf", "-", "-C", str(dest)]
        
        proc1 = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE, text=False)
        proc2 = subprocess.Popen(extract_cmd, stdin=proc1.stdout, cwd=str(dest))
        proc1.stdout.close()
        
        proc1.wait()
        proc2.wait()
        
        if proc1.returncode != 0 or proc2.returncode != 0:
            raise RuntimeError(
                f"tar clone failed: proc1={proc1.returncode}, proc2={proc2.returncode}"
            )

    #
    # Main logic: run script with current Python interpreter
    #
    # If you want to support an alternate virtualenv, you can modify cmd accordingly,
    # but we no longer use `docker run` or `apptainer exec`.
    cmd = [sys.executable, "-u", script_path]  # direct execution in current container

    #
    # Run and collect results
    #
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        success = (result.returncode == 0)
        output = result.stdout
        is_image = is_base64_image(output) if success else False
        return {"success": success, "output": output, "is_image": is_image}

    except Exception as e:
        return {
            "success": False,
            "output": f"subprocess exception: {e}",
            "is_image": False,
        }

    finally:
        try:
            os.remove(script_path)
            os.rmdir(tmpdir)

            if use_apptainer:
                # CRITICAL: Wait for any home2 copy to complete before rotation
                if not wait_for_home2_copy_complete():
                    pass
                
                # Rotate/cleanup environment homes
                if home1.exists():
                    tmp_delete_path = base_dir / f"delete_home_{uuid.uuid4().hex[:8]}"
                    home1.rename(tmp_delete_path)
                    async_delete(tmp_delete_path)

                if home2.exists():
                    home2.rename(home1)

                async_copy_base_to_home2()

        except Exception:
            pass



def process_docker_response(response, app=None):
    def log(msg=None, syntax=None, role="system"):
        if app:
            if role == "error":
                app.log_error(msg if msg else syntax)
            elif role in ("assistant", "system"):
                if syntax:
                    app.log_syntax(syntax)
                else:
                    app.log_agent_message(msg)
            else:
                app.log_agent_message(msg)
        else:
            if syntax:
                print(syntax)
            else:
                print(msg)

    if not response["success"]:
        syntax = Syntax(response["output"], "python", theme="monokai", line_numbers=False)
        log(role="error", syntax=syntax)
        return

    if response.get("is_image"):
        try:
            image_bytes = base64.b64decode(response["output"])
            image_path = "image.png"
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            log(f"✅ Image saved successfully to '{image_path}'")
        except Exception as e:
            log(f"❌ Failed to decode and save image: {e}", role="error")
    else:
        log(f"Execution Output:\n{response['output']}")


if __name__ == "__main__":
    # Example: now runs inside current container
    response = run_python_in_docker("print('Hello from current container!')")
    process_docker_response(response)

    response = run_python_in_docker("raise ValueError('Oops!')")
    process_docker_response(response)

    response = run_python_in_docker(
        """
import subprocess
import sys
def install_uv():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "uv"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"Failed to install uv: {e}")
        sys.exit(1)
def install_packages_with_uv():
    required_packages = ['matplotlib', 'numpy']
    try:
        subprocess.check_call([sys.executable, "-m", "uv", "pip", "install"]
                              + required_packages,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"Failed to install packages with uv: {e}")
        sys.exit(1)
def main():
    install_uv()
    install_packages_with_uv()
    import matplotlib.pyplot as plt
    import numpy as np
    import base64
    from io import BytesIO
    t = np.linspace(0, 1, 1000)
    y = np.sin(2 * np.pi * t)
    plt.plot(t, y)
    plt.title('1Hz Sine Wave')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return img_base64
if __name__ == "__main__":
    print(main())
"""
    )
    process_docker_response(response)