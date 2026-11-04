# Fission 180 quick update

Most Fission 180 changes (interface, icons, Press/Pull, dialogs, ...) are Python. They do not need
the multi-hour build: you only swap the Fission 180 module inside the Fission 180 you already have.
A full **Fission 180 build** is only needed when FreeCAD's C++ core changes (rare; MEMORY.md says so
when it happens).

The update works on every Fission 180 layout:

- the **installed** Fission 180 (`C:\Program Files\Fission180`, from the installer): found by itself;
- the **portable** build unzipped anywhere (the folder with `bin\Fission180.exe`);
- a build or a FreeCAD 1.1.4 from before the branding pass (the folder with `bin\FreeCAD.exe`).

## Get it

1. GitHub > **Actions** > **Fission 180 tests** > the newest run with a green tick.
2. Scroll to **Artifacts**, download `Fission180-quick-update-...` (a few MB).

## Install it (about a minute)

1. Close Fission 180.
2. Unzip the download: right-click the .zip > **Extract All** (running it from inside the
   .zip does not work).
3. In the unzipped folder, double-click **`install_update.cmd`**.
4. If Fission 180 was installed with the installer, the window says where it found it: press
   **Enter** to update that one. Otherwise (or after typing `n`) a folder picker opens: pick
   your Fission 180 folder (the one with `bin` and `Mod` inside).
5. Read the result in the window, press a key to close it, and start Fission 180.
   **Fission 180 > Diagnostics** shows the build number, the program and the settings folder.

If anything goes wrong, the window stays open with the reason, and everything is also written to
`install_update.log` in the unzipped folder: send that file.

An installed Fission 180 lives under `C:\Program Files`, so Windows asks for administrator
permission: click **Yes**. A second window does the update and shows the result. The portable
build in a normal folder (for example `C:\Fission180`) needs no permission.

Your previous version is copied to `<your Fission 180>\Fission180-backups\<date>` (outside `Mod`,
because FreeCAD loads every folder inside `Mod`). To go back: delete `Mod\Fission180` and copy the
backup folder there under the name `Fission180`. Old backups can be deleted any time; the
uninstaller removes them with the program.

**"Fission 180's AI connector is running (python)"**: an AI app you set up (Claude Desktop, Gemini
CLI, Claude Code) started Fission 180's AI connector, which runs while that app runs, even with
Fission 180 closed. Press **Enter** and the installer stops it (harmless: the AI app starts it again
next time), or quit the AI app first (Claude Desktop: right-click its icon by the clock > Quit).

**"Access to the path is denied"**: Windows would not let the files be changed. Close Fission 180
(also look in Task Manager for `Fission180` or `FreeCAD`), close every File Explorer window showing
the Fission 180 folder, and run `install_update.cmd` again (right-click > **Run as administrator**
if it still fails).

Without the installer: close Fission 180, delete `<your Fission 180>\Mod\Fission180` and copy the
`Fission180` folder from the download into `Mod`.

**Update now** inside Fission 180 (Help > Check for Updates) uses this same script, started for you
after Fission 180 quits: `install_update.ps1 -Target <Fission 180 folder> -WaitPid <Fission 180's process>
-Restart -Quiet`. It waits for Fission 180 to end, does the steps above without asking anything,
puts the old version back and shows one message with the log's path if something fails, and
starts Fission 180 again when it is done. The log is `install_update.log` next to the script, in
`%APPDATA%\Fission180\Fission180\updates\<version>\module`.

The .cmd already starts PowerShell with permission to run the script. The manual equivalent:

```
powershell -ExecutionPolicy Bypass -File .\install_update.ps1
```
