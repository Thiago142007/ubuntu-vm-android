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

DEFAULT_CONFIG = {
    "arch": "aarch64",  # aarch64 or x86_64
    "ram_mb": 2048,
    "cpu_cores": 2,
    "disk_gb": 20,
    "vnc_port": 5900,
    "novnc_port": 6080,
    "ssh_port": 2222,
    "iso_name": "ubuntu-22.04-desktop-arm64.iso",
    "display": "vnc"
}

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
        subprocess.run([sys.executable, "-m", "pip", "install", "websockify"], check=False)

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
    if config["arch"] == "aarch64" and not os.path.exists(EFI_CODE):
        print("Downloading QEMU EFI firmware for ARM64...")
        url = "https://releases.linaro.org/components/kernel/uefi-linaro/latest/release/qemu64/QEMU_EFI.fd"
        try:
            subprocess.run(["wget", "-O", EFI_CODE, url], check=True)
        except Exception:
            print("Downloading alternative EFI firmware...")
            # Fallback download or copy if present
            alt_url = "https://github.com/qemu/qemu/raw/master/pc-bios/edk2-aarch64-code.fd"
            subprocess.run(["wget", "-O", EFI_CODE, alt_url], check=False)

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

def start_vm(boot_iso=None):
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

    qemu_cmd = [
        f"qemu-system-{arch}",
        "-m", f"{ram}M",
        "-smp", str(cores),
        "-display", "none",
        "-vnc", f"127.0.0.1:{vnc_port - 5900}",
        "-net", "nic,model=virt",
        "-net", f"user,hostfwd=tcp::{ssh_port}-:22,hostfwd=tcp::8080-:80",
    ]

    if arch == "aarch64":
        download_efi_if_needed()
        qemu_cmd.extend([
            "-machine", "virt",
            "-cpu", "cortex-a57",
            "-bios", EFI_CODE if os.path.exists(EFI_CODE) else "",
            "-device", "virtio-gpu-pci",
            "-device", "virtio-keyboard-pci",
            "-device", "virtio-mouse-pci",
            "-drive", f"if=virtio,format=qcow2,file={DISK_FILE}"
        ])
    else:  # x86_64
        qemu_cmd.extend([
            "-machine", "q35",
            "-cpu", "max",
            "-vga", "virtio",
            "-usb", "-device", "usb-tablet",
            "-drive", f"file={DISK_FILE},format=qcow2,if=virtio"
        ])

    if boot_iso:
        iso_path = os.path.join(ISO_DIR, boot_iso) if not os.path.isabs(boot_iso) else boot_iso
        if os.path.exists(iso_path):
            print(f"Booting with ISO: {iso_path}")
            if arch == "aarch64":
                qemu_cmd.extend(["-drive", f"if=virtio,media=cdrom,file={iso_path}"])
            else:
                qemu_cmd.extend(["-cdrom", iso_path, "-boot", "d"])
        else:
            print(f"Warning: ISO file {iso_path} not found.")

    print("Starting QEMU Ubuntu Virtual Machine...")
    print(f"RAM: {ram}MB | Cores: {cores} | Arch: {arch}")
    print(f"VNC Server starting on 127.0.0.1:{vnc_port}")

    with open(LOG_FILE, "w") as log_f:
        proc = subprocess.Popen(qemu_cmd, stdout=log_f, stderr=log_f)
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
        proc = subprocess.Popen(novnc_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

def print_status():
    config = load_config()
    vm_pid = is_vm_running()
    novnc_pid = is_novnc_running()

    print("==========================================")
    print("        Ubuntu QEMU VM Status             ")
    print("==========================================")
    print(f"Architecture : {config['arch']}")
    print(f"RAM Allocation: {config['ram_mb']} MB")
    print(f"CPU Cores    : {config['cpu_cores']}")
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
    choice = input("Select option to change (1-4, or Enter to skip): ").strip()
    
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

    save_config(config)
    print("Settings updated successfully.")

def interactive_menu():
    while True:
        print_status()
        print("\nOptions:")
        print("1. Start Ubuntu VM")
        print("2. Start Ubuntu VM with ISO (Install/Boot ISO)")
        print("3. Stop VM")
        print("4. Configure VM (RAM, CPU, Arch)")
        print("5. Install Dependencies")
        print("6. Exit")
        
        choice = input("\nSelect an option (1-6): ").strip()
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
            stop_vm()
        elif choice == "4":
            configure_menu()
        elif choice == "5":
            check_dependencies()
        elif choice == "6":
            print("Exiting Manager.")
            break

def main():
    parser = argparse.ArgumentParser(description="Ubuntu QEMU Manager for Android")
    parser.add_argument("action", nargs="?", choices=["start", "stop", "status", "config", "menu"], default="menu")
    parser.add_argument("--iso", help="Specify ISO to boot")
    args = parser.parse_args()

    if args.action == "start":
        start_vm(boot_iso=args.iso)
    elif args.action == "stop":
        stop_vm()
    elif args.action == "status":
        print_status()
    elif args.action == "config":
        configure_menu()
    else:
        interactive_menu()

if __name__ == "__main__":
    main()
