import psutil
import shutil
import wmi
import subprocess
import pythoncom
import requests

def get_cpu_usage():
    return psutil.cpu_percent(interval=0.5)


def get_memory_metrics():
    mem = psutil.virtual_memory()
    return {
        "usage": mem.percent,
        "used_gb": round(mem.used / (1024**3), 2),
        "total_gb": round(mem.total / (1024**3), 2)
    }


def get_storage_metrics():
    total, used, free = shutil.disk_usage("/")
    percent = round((used / total) * 100, 1)
    return {
        "usage": percent
    }


def get_hardware_temperatures():
    cpu_temp = None
    gpu_temp = None

    try:
        response = requests.get("http://localhost:8085/data.json", timeout=2)
        data = response.json()

        def search_sensors(node):
            nonlocal cpu_temp, gpu_temp

            # Only process actual temperature nodes
            if node.get("Type") == "Temperature":
                name = node.get("Text", "").lower()
                value = node.get("Value", "")

                if value:
                    # remove all non numeric characters except dot
                    numeric = ''.join(c for c in value if c.isdigit() or c == '.')

                    if numeric:
                        numeric = float(numeric)

                        if "cpu package" in name:
                            cpu_temp = numeric

                        if "gpu core" in name:
                            gpu_temp = numeric

            # Recurse
            for child in node.get("Children", []):
                search_sensors(child)

        search_sensors(data)

    except Exception as e:
        print("HTTP temperature error:", e)

    return cpu_temp, gpu_temp

def get_gpu_metrics():
    try:
        result = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits"
            ],
            encoding="utf-8"
        )

        usage, temperature = result.strip().split(",")

        return {
            "detected": True,
            "usage": float(usage.strip()),
            "temperature": float(temperature.strip())
        }

    except Exception:
        return {"detected": False}


def get_system_metrics():
    cpu_temp, gpu_temp = get_hardware_temperatures()
    gpu_data = get_gpu_metrics()

    return {
        "cpu": {
            "usage": get_cpu_usage(),
            "temperature": cpu_temp
        },
        "memory": get_memory_metrics(),
        "gpu": {
            **gpu_data,
            "temperature": gpu_temp if gpu_temp else gpu_data.get("temperature")
        },
        "storage": get_storage_metrics()
    }