#!/usr/bin/env python3
"""
Ubuntu QEMU Virtual Machine Manager for Android (Termux)
Allows creating, running, and managing Ubuntu VMs with graphical interface (VNC / noVNC).
"""

import os
import sys
import subprocess
import shutil
import json
import time
import argparse

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "vm_config.json")
DISK_FILE = os.path.join(BASE_DIR, "ubuntu_disk.qcow2")
ISO_DIR = os.path.join(BASE_DIR, "iso")
EFI_CODE = os.path.join(BASE_DIR, "QEMU_EFI.fd")
PID_FILE = os.path.join(BASE_DIR, "qemu.pid")
LOG_FILE = os.path.join(BASE_DIR, "qemu.log")
NOVNC_PID_FILE = os.path.join(BASE_DIR, "novnc.pid")
API_PID_FILE = os.path.join(BASE_DIR, "api.pid")

DEFAULT_CONFIG = {
    "arch": "aarch64",  # aarch64 or x86_64
    "ram_mb": 2048,
    "cpu_cores": 2,
    "disk_gb": 20,
    "vnc_port": 5900,
    "novnc_port": 6080,
    "ssh_port": 2222,
    "iso_name": "ubuntu-22.04-desktop-arm64.iso",
    "display": "vnc",
    "use_kvm": "auto"
}

ISO_PRESETS = [
    {
        "name": "Ubuntu 22.04.5 Live Server (ARM64)",
        "arch": "aarch64",
        "filename": "ubuntu-22.04.5-live-server-arm64.iso",
        "url": "https://cdimage.ubuntu.com/ubuntu/releases/22.04/release/ubuntu-22.04.5-live-server-arm64.iso"
    },
    {
        "name": "Ubuntu 24.04.1 Live Server (ARM64)",
        "arch": "aarch64",
        "filename": "ubuntu-24.04.1-live-server-arm64.iso",
        "url": "https://cdimage.ubuntu.com/ubuntu/releases/24.04/release/ubuntu-24.04.1-live-server-arm64.iso"
    },
    {
        "name": "Ubuntu 22.04.5 Desktop (x86_64)",
        "arch": "x86_64",
        "filename": "ubuntu-22.04.5-desktop-amd64.iso",
        "url": "https://releases.ubuntu.com/22.04/ubuntu-22.04.5-desktop-amd64.iso"
    },
    {
        "name": "Ubuntu 24.04.1 Desktop (x86_64)",
        "arch": "x86_64",
        "filename": "ubuntu-24.04.1-desktop-amd64.iso",
        "url": "https://releases.ubuntu.com/24.04/ubuntu-24.04.1-desktop-amd64.iso"
    },
    {
        "name": "Alpine Linux 3.20 Virtual (ARM64 - Ultra Light ~60MB)",
        "arch": "aarch64",
        "filename": "alpine-virt-3.20.3-aarch64.iso",
        "url": "https://dl-cdn.alpinelinux.org/alpine/v3.20/releases/aarch64/alpine-virt-3.20.3-aarch64.iso"
    },
    {
        "name": "Alpine Linux 3.20 Virtual (x86_64 - Ultra Light ~60MB)",
        "arch": "x86_64",
        "filename": "alpine-virt-3.20.3-x86_64.iso",
        "url": "https://dl-cdn.alpinelinux.org/alpine/v3.20/releases/x86_64/alpine-virt-3.20.3-x86_64.iso"
    }
]

def check_kvm_support():
    kvm_path = "/dev/kvm"
    if os.path.exists(kvm_path):
        if os.access(kvm_path, os.R_OK | os.W_OK):
            return True, "Available (Read/Write access)"
        else:
            return False, "Present (Permission denied)"
    return False, "Not available (/dev/kvm missing)"


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
            # merge default keys if missing
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

def check_dependencies():
    print("Checking dependencies...")
    config = load_config()
    arch = config["arch"]
    
    qemu_cmd = f"qemu-system-{arch}"
    
    if shutil.which(qemu_cmd) is None or shutil.which("qemu-img") is None:
        print("Installing QEMU system and utils via pkg...")
        subprocess.run(["pkg", "install", "-y", f"qemu-system-{arch}", "qemu-utils", "wget", "net-tools"], check=False)
        
    novnc_dir = "/data/data/com.termux/files/usr/share/novnc"
    if not os.path.exists(novnc_dir):
        print("Installing noVNC web files...")
        subprocess.run(["git", "clone", "https://github.com/novnc/noVNC.git", novnc_dir], check=False)

    if shutil.which("websockify") is None:
        print("Installing websockify via pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "websockify"], check=False)

def ensure_disk():
    config = load_config()
    disk_gb = config["disk_gb"]
    if not os.path.exists(DISK_FILE):
        print(f"Creating virtual hard disk ({disk_gb} GB)...")
        cmd = ["qemu-img", "create", "-f", "qcow2", DISK_FILE, f"{disk_gb}G"]
        subprocess.run(cmd, check=True)
        print(f"Disk created: {DISK_FILE}")
    else:
        print(f"Virtual hard disk found: {DISK_FILE}")

def download_efi_if_needed():
    config = load_config()
    if config["arch"] == "aarch64":
        sys_efi = "/data/data/com.termux/files/usr/share/qemu/edk2-aarch64-code.fd"
        if os.path.exists(sys_efi):
            return sys_efi
        if not os.path.exists(EFI_CODE) or os.path.getsize(EFI_CODE) < 100000:
            print("Downloading QEMU EFI firmware for ARM64...")
            alt_url = "https://raw.githubusercontent.com/qemu/qemu/master/pc-bios/edk2-aarch64-code.fd"
            try:
                subprocess.run(["wget", "-O", EFI_CODE, alt_url], check=True)
            except Exception:
                print("Failed to download EFI firmware.")
        return EFI_CODE if (os.path.exists(EFI_CODE) and os.path.getsize(EFI_CODE) > 100000) else ""
    return ""

def list_isos():
    os.makedirs(ISO_DIR, exist_ok=True)
    files = [f for f in os.listdir(ISO_DIR) if f.endswith(".iso") or f.endswith(".img") or f.endswith(".qcow2")]
    return files

def is_vm_running():
    if os.path.exists(PID_FILE):
        with open(PID_FILE, "r") as f:
            try:
                pid = int(f.read().strip())
                # Check if pid exists
                os.kill(pid, 0)
                return pid
            except (ValueError, OSError):
                os.remove(PID_FILE)
    return False

def is_novnc_running():
    if os.path.exists(NOVNC_PID_FILE):
        with open(NOVNC_PID_FILE, "r") as f:
            try:
                pid = int(f.read().strip())
                os.kill(pid, 0)
                return pid
            except (ValueError, OSError):
                os.remove(NOVNC_PID_FILE)
    return False

def is_api_server_running():
    if os.path.exists(API_PID_FILE):
        with open(API_PID_FILE, "r") as f:
            try:
                pid = int(f.read().strip())
                os.kill(pid, 0)
                return pid
            except (ValueError, OSError):
                os.remove(API_PID_FILE)
    return False

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class VMControlHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.strip("/")
        res = {"status": "ok"}
        if path == "api/start":
            start_vm()
            res["message"] = "VM Started"
        elif path == "api/stop":
            stop_vm()
            res["message"] = "VM Stopped"
        elif path == "api/restart":
            stop_vm()
            time.sleep(1)
            start_vm()
            res["message"] = "VM Restarted"
        elif path == "api/bios":
            stop_vm()
            time.sleep(1)
            start_vm(boot_bios=True)
            res["message"] = "VM Started in BIOS Mode"
        elif path == "api/update":
            run_update()
            res["message"] = "Auto-update executed"
        elif path == "api/install-app":
            install_app()
            res["message"] = "Opening Android App installer"
        elif path == "api/status":
            vm_pid = is_vm_running()
            novnc_pid = is_novnc_running()
            res["vm_running"] = bool(vm_pid)
            res["novnc_running"] = bool(novnc_pid)
        else:
            res = {"status": "error", "message": "Unknown endpoint"}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(res).encode("utf-8"))

    def log_message(self, format, *args):
        return

def run_api_server():
    server = HTTPServer(("0.0.0.0", 6081), VMControlHandler)
    server.serve_forever()

def start_api_server():
    if is_api_server_running():
        return
    cmd = [sys.executable, os.path.abspath(__file__), "api-server"]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    with open(API_PID_FILE, "w") as f:
        f.write(str(proc.pid))
    print(f"VM API Control Server running on http://localhost:6081/api/ (PID {proc.pid})")

def start_vm(boot_iso=None, boot_bios=False):
    start_api_server()
    pid = is_vm_running()
    if pid:
        print(f"VM is already running with PID {pid}.")
        return

    check_dependencies()
    ensure_disk()
    config = load_config()
    arch = config["arch"]
    ram = config["ram_mb"]
    cores = config["cpu_cores"]
    vnc_port = config["vnc_port"]
    ssh_port = config["ssh_port"]
    use_kvm = config.get("use_kvm", "auto")
    kvm_supported, kvm_reason = check_kvm_support()
    enable_kvm = False

    qemu_cmd = [f"qemu-system-{arch}"]

    if use_kvm == "true" or (use_kvm == "auto" and kvm_supported):
        enable_kvm = True
        qemu_cmd.append("-enable-kvm")

    if boot_bios:
        qemu_cmd.extend(["-boot", "menu=on"])

    qemu_cmd.extend([
        "-m", f"{ram}M",
        "-smp", str(cores),
        "-display", "none",
        "-vnc", f"127.0.0.1:{vnc_port - 5900}",
        "-netdev", f"user,id=net0,hostfwd=tcp::{ssh_port}-:22,hostfwd=tcp::8080-:80",
        "-device", "virtio-net-pci,netdev=net0",
        "-serial", "telnet:127.0.0.1:5555,server,nowait",
    ])

    if arch == "aarch64":
        sys_code = "/data/data/com.termux/files/usr/share/qemu/edk2-aarch64-code.fd"
        qemu_cmd.extend([
            "-machine", "virt",
            "-cpu", "host" if enable_kvm else "cortex-a57",
            "-bios", sys_code,
            "-object", "rng-random,id=rng0,filename=/dev/urandom",
            "-device", "virtio-rng-pci,rng=rng0",
            "-device", "ramfb",
            "-device", "virtio-gpu-pci,xres=1024,yres=768",
            "-device", "virtio-keyboard-pci",
            "-device", "virtio-mouse-pci",
            "-drive", f"if=virtio,format=qcow2,file={DISK_FILE}"
        ])
    else:  # x86_64
        qemu_cmd.extend([
            "-machine", "q35",
            "-cpu", "host" if enable_kvm else "max",
            "-vga", "virtio",
            "-usb", "-device", "usb-tablet",
            "-drive", f"file={DISK_FILE},format=qcow2,if=virtio"
        ])

    if boot_iso:
        if os.path.exists(boot_iso):
            iso_path = os.path.abspath(boot_iso)
        else:
            iso_path = os.path.join(ISO_DIR, os.path.basename(boot_iso))

        if os.path.exists(iso_path):
            print(f"Booting with ISO: {iso_path}")
            if arch == "aarch64":
                qemu_cmd.extend([
                    "-device", "virtio-scsi-pci,id=scsi0",
                    "-device", "scsi-cd,drive=cd0,bootindex=1",
                    "-drive", f"file={iso_path},if=none,id=cd0,media=cdrom,readonly=on"
                ])
            else:
                qemu_cmd.extend(["-cdrom", iso_path, "-boot", "d"])
        else:
            print(f"Warning: ISO file {iso_path} not found.")

    print("Starting QEMU Ubuntu Virtual Machine...")
    print(f"RAM: {ram}MB | Cores: {cores} | Arch: {arch}")
    print(f"KVM Hardware Accel: {'ENABLED' if enable_kvm else 'DISABLED (' + kvm_reason + ')'}")
    print(f"VNC Server starting on 127.0.0.1:{vnc_port}")

    with open(LOG_FILE, "w") as log_f:
        proc = subprocess.Popen(qemu_cmd, stdout=log_f, stderr=log_f, start_new_session=True)
        with open(PID_FILE, "w") as pid_f:
            pid_f.write(str(proc.pid))

    time.sleep(2)
    if is_vm_running():
        print(f"VM started successfully (PID: {proc.pid}).")
        start_novnc()
    else:
        print("Failed to start VM. Check qemu.log for details.")

def start_novnc():
    if is_novnc_running():
        print("noVNC server is already running.")
        return

    config = load_config()
    vnc_port = config["vnc_port"]
    novnc_port = config["novnc_port"]

    novnc_cmd = None
    if shutil.which("novnc"):
        novnc_cmd = ["novnc", "--vnc", f"localhost:{vnc_port}", "--listen", str(novnc_port)]
    elif shutil.which("websockify"):
        # search for novnc web folder
        web_dir = "/data/data/com.termux/files/usr/share/novnc"
        if os.path.exists(web_dir):
            novnc_cmd = ["websockify", "--web", web_dir, str(novnc_port), f"localhost:{vnc_port}"]

    if novnc_cmd:
        print(f"Starting noVNC Web GUI server on http://localhost:{novnc_port}/vnc.html ...")
        proc = subprocess.Popen(novnc_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        with open(NOVNC_PID_FILE, "w") as f:
            f.write(str(proc.pid))
        print(f"noVNC Web Server running on PID {proc.pid}")
        print(f"Open URL in Android Browser / WebView: http://localhost:{novnc_port}/vnc.html")
    else:
        print("noVNC command not found. You can still connect via VNC viewer app to 127.0.0.1:5900")

def stop_novnc():
    pid = is_novnc_running()
    if pid:
        print(f"Stopping noVNC server (PID {pid})...")
        try:
            os.kill(pid, 15)
        except OSError:
            pass
        if os.path.exists(NOVNC_PID_FILE):
            os.remove(NOVNC_PID_FILE)

def stop_vm():
    stop_novnc()
    pid = is_vm_running()
    if pid:
        print(f"Stopping Ubuntu VM (PID {pid})...")
        try:
            os.kill(pid, 15)  # SIGTERM
            time.sleep(1)
        except OSError:
            pass
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        print("VM stopped.")
    else:
        print("VM is not running.")

def download_iso_menu():
    os.makedirs(ISO_DIR, exist_ok=True)
    print("\n--- Download Linux ISO Presets ---")
    for idx, item in enumerate(ISO_PRESETS, start=1):
        print(f"{idx}. [{item['arch']}] {item['name']}")
    print(f"{len(ISO_PRESETS) + 1}. Custom ISO URL")
    
    choice = input("\nSelect ISO to download (or press Enter to cancel): ").strip()
    if not choice:
        return None
    
    if choice.isdigit() and 1 <= int(choice) <= len(ISO_PRESETS):
        item = ISO_PRESETS[int(choice) - 1]
        target_path = os.path.join(ISO_DIR, item["filename"])
        url = item["url"]
    elif choice == str(len(ISO_PRESETS) + 1):
        url = input("Enter ISO direct URL: ").strip()
        if not url:
            return None
        custom_name = url.split("/")[-1] or "custom.iso"
        filename = input(f"Enter filename to save [{custom_name}]: ").strip() or custom_name
        target_path = os.path.join(ISO_DIR, filename)
    else:
        print("Invalid selection.")
        return None
    
    print(f"\nDownloading: {url}")
    print(f"Saving to  : {target_path}")
    try:
        subprocess.run(["wget", "-c", "-O", target_path, url], check=True)
        print("\nDownload completed successfully!")
        return os.path.basename(target_path)
    except subprocess.CalledProcessError:
        print("\nDownload failed. Please check network connection or URL.")
        return None
    except FileNotFoundError:
        print("\n'wget' command is missing. Run setup.sh or 'pkg install wget'.")
        return None

def print_status():
    config = load_config()
    vm_pid = is_vm_running()
    novnc_pid = is_novnc_running()
    kvm_ok, kvm_msg = check_kvm_support()

    print("==========================================")
    print("        Ubuntu QEMU VM Status             ")
    print("==========================================")
    print(f"Architecture : {config['arch']}")
    print(f"RAM Allocation: {config['ram_mb']} MB")
    print(f"CPU Cores    : {config['cpu_cores']}")
    print(f"KVM Hardware : {config.get('use_kvm', 'auto').upper()} ({kvm_msg})")
    print(f"Disk File    : {DISK_FILE} ({config['disk_gb']} GB)")
    print(f"VM Status    : {'RUNNING (PID ' + str(vm_pid) + ')' if vm_pid else 'STOPPED'}")
    print(f"noVNC Server : {'RUNNING (PID ' + str(novnc_pid) + ')' if novnc_pid else 'STOPPED'}")
    print(f"VNC Connection: 127.0.0.1:{config['vnc_port']}")
    print(f"Web GUI URL  : http://localhost:{config['novnc_port']}/vnc.html")
    print(f"SSH Forward  : localhost:{config['ssh_port']}")
    print("==========================================")

def configure_menu():
    config = load_config()
    print("\n--- Configure VM Settings ---")
    print(f"1. RAM (Current: {config['ram_mb']} MB)")
    print(f"2. CPU Cores (Current: {config['cpu_cores']})")
    print(f"3. Architecture (Current: {config['arch']}) [aarch64 / x86_64]")
    print(f"4. Disk Size (Current: {config['disk_gb']} GB)")
    print(f"5. KVM Acceleration (Current: {config.get('use_kvm', 'auto')}) [auto / true / false]")
    choice = input("Select option to change (1-5, or Enter to skip): ").strip()
    
    if choice == "1":
        ram = input("Enter RAM in MB (e.g. 2048, 4096): ").strip()
        if ram.isdigit():
            config["ram_mb"] = int(ram)
    elif choice == "2":
        cores = input("Enter CPU Cores (e.g. 2, 4): ").strip()
        if cores.isdigit():
            config["cpu_cores"] = int(cores)
    elif choice == "3":
        arch = input("Enter architecture (aarch64 or x86_64): ").strip()
        if arch in ["aarch64", "x86_64"]:
            config["arch"] = arch
    elif choice == "4":
        disk = input("Enter disk size in GB (e.g. 20, 40): ").strip()
        if disk.isdigit():
            config["disk_gb"] = int(disk)
    elif choice == "5":
        use_kvm = input("Enter KVM mode (auto / true / false): ").strip().lower()
        if use_kvm in ["auto", "true", "false"]:
            config["use_kvm"] = use_kvm

    save_config(config)
    print("Settings updated successfully.")

def interactive_menu():
    while True:
        print_status()
        print("\nOptions:")
        print("1. Start Ubuntu VM")
        print("2. Start Ubuntu VM with ISO (Install/Boot ISO)")
        print("3. Download ISO (Ubuntu / Alpine presets)")
        print("4. Stop VM")
        print("5. Configure VM (RAM, CPU, Arch, KVM)")
        print("6. Install Dependencies")
        print("7. Exit")
        
        choice = input("\nSelect an option (1-7): ").strip()
        if choice == "1":
            start_vm()
        elif choice == "2":
            isos = list_isos()
            print("\nAvailable ISOs in iso/ directory:")
            for idx, f in enumerate(isos):
                print(f"{idx + 1}. {f}")
            iso_input = input("Enter ISO filename (or full path, or number): ").strip()
            if iso_input.isdigit() and 1 <= int(iso_input) <= len(isos):
                iso_name = isos[int(iso_input) - 1]
            else:
                iso_name = iso_input
            if iso_name:
                start_vm(boot_iso=iso_name)
        elif choice == "3":
            download_iso_menu()
        elif choice == "4":
            stop_vm()
        elif choice == "5":
            configure_menu()
        elif choice == "6":
            check_dependencies()
        elif choice == "7":
            run_update()
        elif choice == "8":
            print("Exiting Manager.")
            break

def run_update():
    print("\n[Auto-Updater] Checking for repository and app updates...")
    update_script = os.path.join(BASE_DIR, "update.sh")
    if os.path.exists(update_script):
        subprocess.run(["bash", update_script])
    else:
        print("update.sh not found.")

def install_app():
    print("\n[App Installer] Searching for APK...")
    candidates = [
        os.path.join(BASE_DIR, "UbuntuVMApp", "app", "build", "outputs", "apk", "debug", "app-debug.apk"),
        os.path.join(BASE_DIR, "UbuntuVMApp", "app-debug.apk"),
        os.path.join(BASE_DIR, "app-debug.apk")
    ]
    for c in candidates:
        if os.path.exists(c):
            print(f"Opening Android Installer for: {c}")
            subprocess.run(["termux-open", c])
            return
    print("APK not found. Please place or build app-debug.apk in UbuntuVMApp/")

def main():
    parser = argparse.ArgumentParser(description="Ubuntu QEMU Manager for Android")
    parser.add_argument("action", nargs="?", choices=["start", "stop", "restart", "bios", "status", "config", "download-iso", "api-server", "update", "install-app", "menu"], default="menu")
    parser.add_argument("--iso", help="Specify ISO to boot")
    args = parser.parse_args()

    if args.action == "start":
        start_vm(boot_iso=args.iso)
    elif args.action == "stop":
        stop_vm()
    elif args.action == "restart":
        stop_vm()
        time.sleep(1)
        start_vm(boot_iso=args.iso)
    elif args.action == "bios":
        stop_vm()
        time.sleep(1)
        start_vm(boot_iso=args.iso, boot_bios=True)
    elif args.action == "api-server":
        run_api_server()
    elif args.action == "status":
        print_status()
    elif args.action == "config":
        configure_menu()
    elif args.action == "download-iso":
        download_iso_menu()
    elif args.action == "update":
        run_update()
    elif args.action == "install-app":
        install_app()
    else:
        interactive_menu()

if __name__ == "__main__":
    main()
