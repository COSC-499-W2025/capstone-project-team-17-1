import os
import requests
import time
import platform

IS_WINDOWS = platform.system().lower() == "windows"
if IS_WINDOWS:
    import win32con
    from win32com.shell import shell
    import win32com.shell.shellcon as shellcon


monitor_process = None


def is_monitor_running():
    try:
        requests.get("http://localhost:8085/data.json", timeout=1)
        return True
    except:
        return False


def start_monitor():
    if not IS_WINDOWS:
        return

    if is_monitor_running():
        print("Hardware monitor already running.")
        return

    exe_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "tools/system_metrics/LibreHardwareMonitor",
            "LibreHardwareMonitor.exe"
        )
    )

    try:
        proc_info = shell.ShellExecuteEx(
            nShow=win32con.SW_HIDE,   # This hides the window
            fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
            lpVerb="runas",
            lpFile=exe_path,
            lpParameters="",
            lpDirectory=os.path.dirname(exe_path)
        )

        monitor_handle = proc_info['hProcess']
        print("Monitor launched elevated and hidden.")

        # Optional: wait until it fully starts
        time.sleep(2)

    except Exception as e:
        print(f"Failed to launch monitor: {e}")
    
    # Give it a second to boot
    time.sleep(2)

    print("Hardware monitor started silently.")


def stop_monitor():
    global monitor_process

    if not IS_WINDOWS:
        return

    if monitor_process:
        monitor_process.terminate()
        monitor_process.wait()
        print("Hardware monitor stopped.")
