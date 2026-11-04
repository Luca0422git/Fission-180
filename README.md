<!-- FISSION180: Fission 180's own README. FreeCAD's original is README.FreeCAD.md (core-patches.md #5).
     The block between the two "smartscreen" markers is docs/fission180/smartscreen.md word for word
     (a unit test checks it); change that file, then copy the text here. -->
<div align="center">

# Fission 180

**Parametric CAD that works the way Fusion users expect. Free and open source, based on FreeCAD.**

![version](https://img.shields.io/badge/version-0.1.0--beta.3-3fa9f5) ![platforms](https://img.shields.io/badge/Windows%20%7C%20Linux-lightgrey) ![licence](https://img.shields.io/badge/licence-LGPL--2.1--or--later-lightgrey)

[**Download**](https://github.com/Luca0422git/Fission-180/releases) ·
[What works](#what-works-and-what-does-not-yet) ·
[Known issues](docs/fission180/known-issues.md) ·
[Cheat sheet](docs/fission180/cheat-sheet.md) ·
[Privacy](docs/fission180/privacy.md) ·
[Changelog](CHANGELOG.md)

<img src="docs/fission180/images/home.png" alt="Fission 180's Home tab: recent designs, places and the AI panel, in the dark look" width="900">

</div>

Fission 180 is a free CAD program for 3D design: sketches with dimensions and constraints, solid
modeling with a timeline you can edit afterwards, Press Pull, components and joints, surfaces,
sheet metal, plastic parts, meshes, stress simulation, drawings and 3D printing. If you know Fusion, you know Fission 180: the ribbon, the browser,
the timeline, the navigation bar, `S` for command search and Fusion's keys and mouse are all
there. It is built on [FreeCAD](https://www.freecad.org), which does the heavy geometry work, and
adds its own interface and tools on top.

> **New name.** Fission 180 was called **SciForge** until November 2026; the releases up to
> 0.1.0-beta.3.2.1 still carry that name. If you have SciForge, download Fission 180 from the
> [Releases](https://github.com/Luca0422git/Fission-180/releases) page and install it: it replaces
> SciForge, and your designs, settings, places and AI keys come with it.

**This is a beta (0.1.0-beta.3).** Every feature is tested automatically by driving the real
program with clicks and keys, but Fission 180 has had little use by anyone except the person
building it, so expect rough edges. Save often, and read the
[known issues](docs/fission180/known-issues.md) before you start. Your feedback is what makes the
next beta better.

| Sketching, with the sketch palette | The timeline, with a finished design |
|---|---|
| <img src="docs/fission180/images/sketch.png" alt="A sketch with dimensions and the Sketch Palette"> | <img src="docs/fission180/images/timeline.png" alt="A Raspberry Pi 5 case with the browser and the timeline"> |
| **Press Pull, with its arrow** | **The AI panel** |
| <img src="docs/fission180/images/presspull.png" alt="Press Pull on the top of a box: an arrow and a distance box"> | <img src="docs/fission180/images/ai.png" alt="The AI panel next to a design"> |

## Download and install

**[Go to the Releases page](https://github.com/Luca0422git/Fission-180/releases)** and pick the
newest release at the top (Fission 180's betas are "pre-releases", which is why GitHub's
"latest" button does not show them).

### Which file to take

| You use | Take this file | Notes |
|---|---|---|
| **Windows 10 or 11** (recommended) | `Fission180_...-installer.exe` | Installs to `C:\Program Files\Fission180`, adds a Start menu entry and an uninstaller. A FreeCAD you already have is not touched. |
| Windows, without installing | `Fission180_...-Windows-...7z` | Unpack it with [7-Zip](https://www.7-zip.org) anywhere (for example `C:\Fission180`) and run `bin\Fission180.exe`. Nothing is installed or registered. |
| **Linux** (64-bit) | `Fission180_...AppImage` | Make it executable (`chmod +x Fission180_...AppImage`) and run it. If your system lacks FUSE, run it with `--appimage-extract` first. |

Next to the downloads there is a checksum file (`SHA256SUMS.txt`) to check that your copy is the
real one (see the next section).

### What your computer needs

- **Windows 10 or 11, 64-bit**, or **Linux on a 64-bit Intel/AMD processor** (x86-64). There is
  **no macOS version**.
- A graphics card and driver with OpenGL support. Fission 180 draws 3D with FreeCAD's engine, and
  FreeCAD's code states that it "requires OpenGL 2.0 or above" and warns at start-up when the
  system is older (`src/Gui/StartupProcess.cpp`). Any PC from roughly the last ten years with an
  up-to-date graphics driver should be fine; if the 3D view stays black, update the driver first.
- About **3 GB** of free disk space for the program (it is about as large as FreeCAD itself),
  plus room for your designs.

<!-- smartscreen:begin -->
### "Windows protected your PC" (Fission 180 is not signed)

When you start the Fission 180 installer for the first time, Windows may show a blue window called
**Windows protected your PC**. This is normal for Fission 180, and it does not mean the download
is broken or dangerous.

**Why it appears.** The installer is not signed with a paid code-signing certificate. Those
certificates cost money every year, and Fission 180 is free and open source, so it does not have one
yet. Windows (the feature is called Microsoft Defender SmartScreen) warns about every program it
has not seen many times before, signed or not. That is its job, and it is a sensible default. It
only tells you that Windows does not know this program yet, not that anything is wrong with it.

**What to click** (Windows 10 and 11):

1. In the blue window, click **More info** (the small text under the message).
2. The window now shows the file name and says "Publisher: Unknown publisher", and a new button
   **Run anyway** appears. Click **Run anyway**.
3. Windows then asks "Do you want to allow this app to make changes to your device?". Click
   **Yes**. The installer needs this to put Fission 180 in `C:\Program Files\Fission180`.

If you use the portable download (the `.7z` file), unpack it with 7-Zip and start
`bin\Fission180.exe`. The same blue window can appear the first time; click **More info**, then
**Run anyway**, the same way.

**If your browser already complained while downloading.** Edge and Chrome may say the file "is
not commonly downloaded". In Edge, open the download's `...` menu, click **Keep**, then **Show
more**, then **Keep anyway**. In Chrome, open the download's menu and click **Keep** (and **Keep anyway** if it asks
again). This is the same warning, one step earlier.

**If there is no "More info" link at all.** Right-click the downloaded file, choose
**Properties**, tick **Unblock** at the bottom of the General tab, click **OK**, and start the
file again. (An administrator can also have set Windows to block unknown programs completely. In
that case ask them.)

**Check that your download is the real one (optional, takes a minute).** Every release has a
checksum file, `SHA256SUMS.txt`, next to the downloads on the releases page. A checksum is a
fingerprint of a file. If your copy gives the same fingerprint as the one on the page, nothing
changed it on the way to you. In PowerShell (Start menu, type "PowerShell"), go to your
Downloads folder and run this, with your real file name:

```
cd $HOME\Downloads
Get-FileHash .\Fission180_YOUR_FILE_NAME-installer.exe -Algorithm SHA256
```

Compare the long `Hash` value with the line for the same file in `SHA256SUMS.txt` (capital or
small letters do not matter). If they differ, delete the file, download it again, and if it
still differs, please tell us:
https://github.com/Luca0422git/Fission-180/issues

**If your antivirus program blocks or removes the file.** Programs that are new, unsigned, and
bring their own Python and many libraries (like Fission 180 and FreeCAD, which it is based on) are
sometimes flagged by mistake. This is called a false positive. What to do:

- Do not switch your antivirus off for good. Check the checksum as described above first.
- Look in the antivirus program's quarantine or history list. If it moved the Fission 180 file
  there and the checksum matched, you can restore it. If you trust the checked download, you can
  tell the antivirus to allow Fission 180's folder (usually `C:\Program Files\Fission180`). How to do
  this differs by program; its help page has the steps ("add an exclusion").
- Most antivirus makers have a page to report a false positive; sending them the file helps
  everyone who downloads Fission 180 after you.
- If you are not comfortable with any of this, wait: nothing is lost by not installing a beta.
  And if you would like help, open an issue and tell us which antivirus program it was.

Fission 180 never needs an account. The installer puts the program in its own folder
(`C:\Program Files\Fission180`), adds a Start menu entry and an entry in Windows' "Installed apps"
(so you can uninstall it), and only if you tick them, a desktop icon and the `.FCStd` file type.
It leaves an installed FreeCAD alone. All of the source code can be read at
https://github.com/Luca0422git/Fission-180
<!-- smartscreen:end -->

## First steps

1. **Start Fission 180.** It opens on the **Home** tab: your recent designs, the places they live in,
   and a **New design** button.
2. **New design** (or `Ctrl+N`). You get an empty design with a body. The **ribbon** at the top
   works like Fusion's: SOLID, SURFACE, MESH, SHEET METAL, PLASTIC, UTILITIES, and SKETCH appears
   while you sketch. The **browser** is on the left, the **timeline** at the bottom: click a step
   to edit it, drag the marker to go back in time.
3. **Create Sketch**, click a plane, draw with `L` (line), `R` (rectangle), `C` (circle), dimension
   with `D`, **Finish Sketch**, then `E` for **Extrude** and `Q` for **Press Pull**.
4. **Press `S`** to search every command by name; Enter runs the best match.
5. **Open an example:** [docs/fission180/examples/pi5-case](docs/fission180/examples/pi5-case/README.md)
   is a Raspberry Pi 5 case built entirely in Fission 180 (download `pi5_case.FCStd` and open it
   from Home with **Open...**).
6. **Stress test a part:** click **DESIGN ▾** at the top left and pick **Simulation**, then
   **New Simulation Study** > Create Study. Add **Structural Constraints** > Fixed where the
   part is held and **Structural Loads** > Force where it is pushed, press **Solve**, and read
   the **Safety Factor** (red is weak). The **Pre-check** light says what is still missing.

The [cheat sheet](docs/fission180/cheat-sheet.md) lists Fusion's keys and mouse habits next to what
Fission 180 does. If you want to know exactly where Fission 180 still differs from Fusion, the
documents in [docs/fission180/parity](docs/fission180/parity) say so for each tool.

## What works, and what does not yet

**Works (and is tested by running it like a person would):** sketches (lines, rectangles, circles,
arcs, polygons, slots, splines, text, dimensions, constraints), Extrude, Revolve, Sweep, Loft,
Press Pull, fillets and chamfers, shell, draft, scale, holes and threads, patterns and mirrors,
components and joints, surfaces, sheet metal (flanges, bends, hems, flat patterns with DXF export),
plastic parts (bosses, snap fits, lips, rests, design advice), mesh tools, 2D drawings, 3D printing
(3MF / STL / send to your slicer), a hardware library (screws, nuts, washers), measuring and
analysis, parameters, version history for each design, STEP / DXF / SVG / mesh import and export,
**stress simulation** (Fusion's Simulation workspace with the Static Stress study: supports,
loads, mesh, solved on your own computer; safety factor, stresses and displacements, probes,
compare and a report), robotics assemblies (snaps at the centre of square holes for VEX parts,
many STEP files at once), and **AI connectors** (a chat panel that uses your own key from Claude,
ChatGPT, Gemini or a local model; and a connector so AI apps like Claude Desktop can build in
Fission 180, off until you switch it on). With an AI connected, **Auto Timeline** rebuilds a part
that has no timeline (an imported STEP or a simple mesh) as timeline steps you can edit.

**Does not (yet):** sculpting, simulation other than Static Stress (no thermal, vibration
modes, buckling, nonlinear, event or shape optimization studies), rendering and animation, CAM,
electronics, cloud collaboration, macOS, other languages than English, Fusion's `.f3d` files
(export STEP from Fusion instead), and some options inside tools that exist (shown greyed out,
with the reason). Press Pull is still rough on complex curved shapes. The full, honest list with
workarounds is in **[Known issues](docs/fission180/known-issues.md)**.

## Updating

Fission 180 looks for a new version when it starts (at most once a day; you can switch this off in
Preferences > General > "Check for updates when Fission 180 starts", and **Help > Check for
Updates** checks any time). If there is one, an update icon appears in the top right of the window, next to the search
button (click it for **Update now** or **What's new**), and a line appears at the top of the Home
tab with **What's new**, **Update now** and **Later**. Nothing is installed until you click **Update now**,
and Fission 180 asks about unsaved designs first.

Updating yourself works too: download the newest installer from the
[Releases page](https://github.com/Luca0422git/Fission-180/releases) and run it over the old one (your
settings are in `%APPDATA%\Fission180` and your designs where you saved them, not in the program
folder), or use the small module-only update described in
[docs/fission180/quick-update.md](docs/fission180/quick-update.md). On Linux, download the new
AppImage and replace the old file.

## Reporting problems and ideas

- **Something went wrong?** Choose **Help > Report a Problem** in Fission 180. It writes down the
  useful details (versions, graphics card, the last Fission 180 messages, the crash log) with your
  name and folders removed, shows you all of it, and lets you **Open on GitHub** (your browser
  opens a pre-filled form; you need a free GitHub account), **Save** it to a file, or **Copy**
  it. Fission 180 never sends anything by itself.
- You can also open an issue yourself: **[Issues](https://github.com/Luca0422git/Fission-180/issues/new/choose)**
  (a bug report form or an idea form). Say what you did, what happened and what you expected, and
  paste **Fission 180 > Diagnostics**.
- **Questions, ideas and chatting:** [Discussions](https://github.com/Luca0422git/Fission-180/discussions).

## Privacy

Fission 180 has **no accounts and no telemetry**. By itself it goes online for exactly two things:
the update check (one request to `api.github.com`, which can be switched off in Preferences) and,
only if you connect one, the AI service you chose. AI keys are kept on your computer (Windows:
encrypted for your user), your designs are never uploaded, and cloud places are just folders that
your own cloud app syncs. Every detail, and where in the code to check it, is in
**[docs/fission180/privacy.md](docs/fission180/privacy.md)**.

## Building from source

You never need to compile anything to try Fission 180: GitHub builds it (Actions > "Fission 180 build").
How the builds and tests work, and how the code is organised, is described in
**[docs/fission180/README.md](docs/fission180/README.md)**. Fission 180's own code is the Python module in
`src/Mod/Fission180`; the rest of the repository is FreeCAD's source with a few documented changes
([docs/fission180/core-patches.md](docs/fission180/core-patches.md)).

## Licence and credits

Fission 180 is free software under the **LGPL-2.1-or-later** licence, the same as FreeCAD (see
[LICENSE](LICENSE)). You may use it, also commercially, and share and change it under that
licence.

Fission 180 is built on **[FreeCAD](https://www.freecad.org)** (version 1.1.4 is inside), and owes
almost everything under the hood to the FreeCAD community and to OpenCASCADE, the geometry
kernel: thank you. Simulation meshes with **[Gmsh](https://gmsh.info)** and solves with
**[CalculiX](http://www.calculix.de)**, which come with FreeCAD. Fission 180 **is not FreeCAD and is
not endorsed by the FreeCAD project**; please do not report Fission 180 problems to FreeCAD.
FreeCAD's original README is kept as [README.FreeCAD.md](README.FreeCAD.md), and FreeCAD's
credits are in Fission 180's Help > About.
The anvil logo, Fission 180's interface icons and the splash picture are original Fission 180 artwork.

Fission 180 is not affiliated with or endorsed by Autodesk. Autodesk and Fusion are trademarks of
Autodesk, Inc. "Fusion" is used on this page only to say who Fission 180 is made for. Fission 180 uses
none of Autodesk's logos, icons, colours or text.
