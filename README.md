# 🐧 Ubuntu QEMU VM para Android (com Interface Gráfica)

[![Build Android APK](https://github.com/Thiago142007/ubuntu-vm-android/actions/workflows/build-apk.yml/badge.svg)](https://github.com/Thiago142007/ubuntu-vm-android/actions/workflows/build-apk.yml)

Este repositório contém uma solução completa para rodar o **Ubuntu Desktop (com Interface Gráfica)** no Android via **QEMU + noVNC + App Android Nativo em Kotlin**.

---

## 📱 Baixar o APK Compilado

Você pode baixar o arquivo **`.apk`** gerado automaticamente após a compilação:

1. Acesse as [Ações do GitHub (Actions)](https://github.com/Thiago142007/ubuntu-vm-android/actions/runs/32363454599)
2. Baixe o artefato **`UbuntuVMApp-debug.apk`**
3. Instale o APK no seu celular Android.

---

## 🛠️ Arquivos e Estrutura do Projeto

* `ubuntu_vm_manager.py`: Gerenciador interativo Python para alocação de RAM/CPU, criação de disco e controle de servidores VNC/noVNC.
* `setup.sh`: Script de instalação rápida de dependências (`qemu-system-aarch64`, `novnc`, `websockify`).
* `UbuntuVMApp/`: Projeto completo em Kotlin/Gradle com WebView noVNC integrado, controles e modo tela cheia.
* `.github/workflows/build-apk.yml`: Workflow para compilar o APK automaticamente na nuvem.

---

## 🚀 Como Executar a Máquina Virtual no Termux

```bash
# 1. Clonar o repositório no Termux
git clone https://github.com/Thiago142007/ubuntu-vm-android.git
cd ubuntu-vm-android

# 2. Instalar dependências
./setup.sh

# 3. Iniciar a Máquina Virtual Ubuntu
python3 ubuntu_vm_manager.py menu
```

### 🖥️ Acessar a Interface Gráfica

* **Via App Android**: Abra o `UbuntuVMApp` instalado no seu celular.
* **Via Navegador**: Acesse [http://localhost:6080/vnc.html](http://localhost:6080/vnc.html)
* **Via Cliente VNC**: Conecte no IP `127.0.0.1:5900`
