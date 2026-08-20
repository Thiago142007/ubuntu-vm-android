#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Auto-Updater for Ubuntu VM Android and Android App
# ==============================================================================
set -e

PROJECT_DIR="/data/data/com.termux/files/home/ubuntu-vm-android"
cd "$PROJECT_DIR"

echo "=========================================="
echo "    Ubuntu VM Android - Auto-Updater      "
echo "=========================================="

echo "[1/4] Verificando atualizações no Git..."
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Atualizando repositório Git local..."
    git fetch origin || true
    git pull origin main --rebase || git pull || true
    echo "Repositório atualizado com sucesso!"
else
    echo "Aviso: Diretório não é um repositório git ativo."
fi

echo "[2/4] Atualizando dependências e pacotes..."
pkg install -y qemu-system-aarch64 python termux-api android-tools xclip ttyd inetutils || true
python3 -m pip install --upgrade websockify 2>/dev/null || true

echo "[3/4] Atualizando permissões de scripts..."
chmod +x setup.sh update.sh ubuntu_vm_manager.py 2>/dev/null || true

echo "[4/4] Verificando aplicativo Android (UbuntuVMApp)..."
APK_PATH="$PROJECT_DIR/UbuntuVMApp/app/build/outputs/apk/debug/app-debug.apk"
if [ ! -f "$APK_PATH" ]; then
    APK_PATH="$PROJECT_DIR/UbuntuVMApp/app-debug.apk"
fi

if [ -f "$APK_PATH" ]; then
    echo "Instalando/Atualizando o aplicativo no Android..."
    termux-open "$APK_PATH" || termux-open-url "file://$APK_PATH" || true
    echo "Janela do instalador do Android aberta!"
fi

echo "=========================================="
echo "  Atualização concluída com sucesso! 🎉   "
echo "=========================================="
