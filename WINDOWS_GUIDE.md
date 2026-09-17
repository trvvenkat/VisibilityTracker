# Windows Setup & User Guide: Visibility Check Tracker

This guide explains everything needed to run the **Visibility Check Tracker** on Windows, whether you want to run it via **Docker** (recommended for tablet/remote access) or **directly in Windows without Docker**.

---

## 📋 Quick Summary of Prerequisites

| Component | Method 1: Docker (Recommended) | Method 2: Native Windows (No Docker) |
| :--- | :--- | :--- |
| **Docker Desktop** | ✅ **Required** | ❌ Not needed |
| **Python** | ❌ **Not needed** (bundled in container) | ✅ **Required** (Python 3.11+) |
| **ngrok Installed** | ❌ **Not needed** (runs via Docker) | ❌ Not needed (unless tunneling without Docker) |
| **Playwright / Chromium** | ❌ **Not needed** (bundled in container) | ❌ Auto-installed by `setup-windows.bat` |
| **Free ngrok Account Token** | ✅ **Required for remote access** | ⚠️ Optional (only for remote access) |

---

## 🚀 Method 1: Docker (Easiest & Recommended for Remote/Tablet Access)

This is the single-command method. You **do not** need Python, Playwright, or ngrok installed on your Windows machine—everything runs inside isolated containers.

### Prerequisites
1. **Docker Desktop for Windows**:
   - Download and install from: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
   - During installation, leave **"Use WSL 2 instead of Hyper-V"** checked (default).
   - Once installed, open **Docker Desktop** from your Start Menu and wait until the bottom-left corner turns green and says **"Engine running"**.
2. **ngrok Authtoken** (Free):
   - Sign up for a free account at [https://ngrok.com](https://ngrok.com).
   - Copy your authtoken from [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken).
   - *(Note: If someone provided you this folder with `.env` already configured, you can skip this step!)*

---

### Step-by-Step Instructions (Method 1)

1. **Extract / Open the Folder**:
   Open the `VisibilityTracker` folder in Windows File Explorer.

2. **Configure your Token** *(if not already done)*:
   - If there is a file named `.env`, open it with Notepad.
   - Set your token:
     ```env
     NGROK_AUTHTOKEN=your_token_here
     ```
   - Save and close Notepad.
   - *(If `.env` doesn't exist yet, `start-docker.bat` will automatically prompt you for it!)*

3. **Start the Tracker**:
   - Double-click **`start-docker.bat`** (or open Command Prompt in the folder and type `docker compose up`).

4. **Get Your Remote & Local Link**:
   In about 15–30 seconds, a large banner will appear in your Command Prompt window:

   ```text
   ================================================================================
   🚀  VISIBILITY CHECK TRACKER IS LIVE & READY!
   ================================================================================

   📱  TABLET / LAPTOP REMOTE ACCESS URL:
       👉  https://xxxx-xx-xx.ngrok-free.app  👈

   💻  LOCAL ACCESS URL:
       http://localhost:8000

   🔑  LOGIN CREDENTIALS:
       Username: admin
       Password: tracker@2026

   💡  USAGE TIPS:
       • Open the Remote Access URL on any laptop, tablet, or phone.
       • You can also click 'Copy' in the top dashboard navigation to share.
       • Press Ctrl+C in this terminal window anytime to stop the server.
   ================================================================================
   ```

5. **Open on Tablet, Laptop, or Phone**:
   - Type or paste the **Remote Access URL** into the browser on your tablet or laptop.
   - Click the blue **"Visit Site"** button (ngrok standard security prompt).
   - Sign in with:
     - **Username**: `admin`
     - **Password**: `tracker@2026`

6. **To Stop**:
   - Press `Ctrl + C` in the Command Prompt window.

---

## 💻 Method 2: Native Windows (Without Docker)

Use this if you prefer running directly in Windows without Docker.

### Prerequisites
1. **Python 3.11 or Higher**:
   - Download from [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)
   - ⚠️ **CRITICAL STEP DURING INSTALLATION**: On the first installer screen, you **MUST check the box** that says:
     `☑ Add python.exe to PATH`
   - Complete the installation.

---

### Step-by-Step Instructions (Method 2)

1. **One-Time Setup**:
   - Double-click **`setup-windows.bat`**.
   - This script will automatically:
     - Check your Python installation.
     - Create a clean `.venv` virtual environment.
     - Install all Python libraries (`fastapi`, `pandas`, `playwright`, etc.).
     - Download the Playwright Chromium browser.
   - When finished, you will see `[SUCCESS] Setup complete!`. Press any key to close the window.

2. **Start the Tracker**:
   - Double-click **`run-windows.bat`**.
   - The Command Prompt will display:
     ```text
     [*] Starting web server at http://127.0.0.1:8000 ...
     ```

3. **Access the Application**:
   - Open your web browser on that computer and go to:
     [**http://127.0.0.1:8000**](http://127.0.0.1:8000)
   - Sign in with:
     - **Username**: `admin`
     - **Password**: `tracker@2026`

4. **To Stop**:
   - Press `Ctrl + C` in the Command Prompt window.

---

## ❓ Frequently Asked Questions & Troubleshooting

### Q: Do I need ngrok installed on Windows for Docker?
**No.** Docker Compose automatically downloads the official ngrok container image (`ngrok/ngrok:latest`). You do not need to install ngrok software on Windows.

### Q: Do I need Python installed for Docker?
**No.** Docker runs a self-contained Linux environment with Python 3.11 and Playwright Chromium pre-installed.

### Q: "Failed to connect to docker API / docker daemon is not running" error?
Open **Docker Desktop** from your Windows Start Menu and check the whale icon in your system tray. Wait until it shows **"Engine running"** before running `start-docker.bat`.

### Q: How do I share this with my friend?
1. Put your `.env` file into the folder (with your `NGROK_AUTHTOKEN` already filled in).
2. Zip the `VisibilityTracker` folder (exclude `.venv` and `data/jobs` to keep the zip small).
3. Send her the zip file and this `WINDOWS_GUIDE.md`.
4. She just installs Docker Desktop and double-clicks **`start-docker.bat`**!
