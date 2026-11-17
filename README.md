# LowCore Launcher

A lightweight, bloat-free Minecraft launcher built for low-end PCs and laptops.

- Isolated instances, so each setup keeps its own mods and settings
- Built-in content browser for mods, resource packs and shaders
- Multiple themes
- Open source
- Available for **Windows** and **Linux**

**Website:** https://lowcore.vercel.app

---

## Download

Get the latest version from the [website](https://lowcore.vercel.app) or the [Releases](../../releases) page.

| Platform | File |
| --- | --- |
| Windows (64-bit) | `LowCoreLauncherSetup.exe` |
| Linux (x64) | `LowCoreLauncher-Linux.zip` |

---

## Install on Windows

1. Go to https://lowcore.vercel.app and click **Download for Windows (.exe)**.
2. Run the downloaded `LowCoreLauncherSetup.exe`.
3. If Windows shows **"Windows protected your PC"**, click **More info**, then **Run anyway**.
4. In the setup wizard:
   1. Choose the install folder (the default is fine) and click **Next**.
   2. Choose whether to create a desktop shortcut and click **Next**.
   3. Click **Install**.
   4. Click **Finish**. Leave "Launch LowCore Launcher" ticked to open it straight away.
5. Add your account on the **Play** tab: click **+ Microsoft** to sign in with your Microsoft account (or **+ Offline**).
6. Pick an instance (or click **+ New Instance**) and press **PLAY**.

---

## Install on Linux

1. Go to https://lowcore.vercel.app and click **Download for Linux**.
2. Extract `LowCoreLauncher-Linux.zip`.
3. Open a terminal inside the extracted folder.
4. Run:

   ```bash
   bash install.sh
   ```

5. Open LowCore Launcher from the desktop shortcut, add your account, and press **PLAY**.

### Troubleshooting (Linux)

**It asks for `libxcb-cursor0`, or fails with an `xcb` error**

Run this one-time command in your terminal (Debian/Ubuntu-based systems):

```bash
sudo apt update && sudo apt install -y libxcb-cursor0
```

**The desktop shortcut doesn't open on Ubuntu/GNOME**

Right-click the desktop icon and select **"Allow Launching"**.

---

## First launch (Windows and Linux)

1. **Add an account:** use **+ Microsoft** to sign in, or **+ Offline**.
2. **Create or import an instance:** click **+ New Instance** or **Import**.
3. **Add mods:** open the **Content Browser** tab, pick your instance, search, and click **Download to Selected Instance**.
4. Press **PLAY**.

---

## Community

Join the Discord server from the [website](https://lowcore.vercel.app).

