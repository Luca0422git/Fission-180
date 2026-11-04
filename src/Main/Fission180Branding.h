// SPDX-License-Identifier: LGPL-2.1-or-later
/***************************************************************************
 *   FISSION180: the application's identity.                                 *
 *                                                                         *
 *   Fission 180 is a fork of FreeCAD (https://freecad.org). The values here  *
 *   make the fork a separate program that installs next to FreeCAD: its   *
 *   own name in every window title and dialog, its own settings folder    *
 *   (%APPDATA%\Fission180 on Windows, ~/.config/Fission180 and                *
 *   ~/.local/share/Fission180 on Linux, derived by App::Application from    *
 *   "ExeName"), its own icon, splash screen and About banner.             *
 *                                                                         *
 *   Used by MainGui.cpp, MainCmd.cpp and MainPy.cpp. The build system     *
 *   keeps the same names in                                               *
 *   cMake/FreeCAD_Helpers/InitializeFreeCADBuildOptions.cmake (program    *
 *   names, Windows version resource, Linux desktop entry); the unit test  *
 *   Fission180Tests/unit/test_branding_files.py checks that they agree.     *
 *   See docs/fission180/core-patches.md #8.                                 *
 ***************************************************************************/

#ifndef FISSION180_BRANDING_H
#define FISSION180_BRANDING_H

// Fission 180's own version, from src/Mod/Fission180/VERSION through CMake (src/Main/CMakeLists.txt).
// FreeCAD's version numbers stay FreeCAD's: the "based on FreeCAD 1.1.4" in Help > About.
#ifndef FISSION180_VERSION
#error "FISSION180_VERSION is set by src/Main/CMakeLists.txt from src/Mod/Fission180/VERSION"
#endif

#define FISSION180_EXE_NAME "Fission180"
#define FISSION180_VENDOR "Fission180"
#define FISSION180_URL "https://github.com/Luca0422git/Fission-180"
#define FISSION180_DESKTOP_ID "org.fission180.Fission180"
#define FISSION180_START_WORKBENCH "Fission180Workbench"

// Pictures compiled into FreeCADGui's resources (src/Gui/Icons/resource.qrc), generated
// by tools/fission180/make_app_icons.py. The splash already shows the wordmark; FreeCAD
// only paints the version number on it, at (x + 235, y - 7) of SplashInfoPosition.
#define FISSION180_APP_ICON "fission180app"
#define FISSION180_SPLASH "fission180splash"
#define FISSION180_ABOUT_IMAGE "fission180about"
#define FISSION180_SPLASH_TEXT_COLOR "#8FD0FF"
#define FISSION180_SPLASH_INFO_COLOR "#CFD8E3"
#define FISSION180_SPLASH_INFO_POSITION "190,189"

// Console banner; its first line is also shown next to the name in Help > About, so
// FreeCAD's credit stays visible (feature outline 2.5). {} is the copyright year.
#define FISSION180_BANNER_FORMAT                                                                 \
    "(C) 2026 Fission 180 contributors. Based on FreeCAD, (C) 2001-{} FreeCAD contributors.\n"    \
    "Fission 180 and FreeCAD are free and open-source software under the LGPL-2.1-or-later "      \
    "license.\n\n"

#endif  // FISSION180_BRANDING_H
