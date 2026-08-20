#!/usr/bin/env bash
# Ubuntu QEMU Android Setup Script

set -e

echo "=========================================="
echo "  Ubuntu QEMU VM Setup for Android        "
echo "=========================================="

echo "[1/4] Updating package repository..."
pkg update -y || true

echo "[2/4] Installing QEMU, Python, noVNC & dependencies..."
pkg install -y qemu-utils qemu-system-aarch64 qemu-system-x86_64 novnc websockify wget net-tools python

echo "[3/4] Initializing VM directory & script permissions..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"
mkdir -p iso
chmod +x ubuntu_vm_manager.py

echo "[4/4] Creating easy binary launcher 'ubuntu-vm'..."
mkdir -p "$HOME/bin"
cat << 'EOF' > "$HOME/bin/ubuntu-vm"
#!/usr/bin/env bash
python3 "$HOME/ubuntu-vm-android/ubuntu_vm_manager.py" "$@"
EOF
chmod +x "$HOME/bin/ubuntu-vm"

if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
    export PATH="$HOME/bin:$PATH"
    echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
fi

echo ""
echo "=========================================="
echo "  Setup Completed Successfully!           "
echo "=========================================="
echo "Commands available:"
echo "  1. Run manager: ubuntu-vm menu"
echo "  2. Start VM:    ubuntu-vm start"
echo "  3. Stop VM:     ubuntu-vm stop"
echo "  4. Status:      ubuntu-vm status"
echo ""
echo "Access Ubuntu GUI at: http://localhost:6080/vnc.html"
echo "=========================================="
