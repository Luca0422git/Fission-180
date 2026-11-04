/*
declaration.nsh

Configuration and variables of FreeCAD installer
*/

#--------------------------------
# File locations

!define FILES_LICENSE "license.rtf"

#--------------------------------
# Names and version

!define APP_VERSION_NUMBER "${APP_VERSION_MAJOR}.${APP_VERSION_MINOR}.${APP_VERSION_PATCH}.${APP_VERSION_BUILD}"
# For the proposed install folder we use the scheme "FreeCAD x.x"
# however for the Registry, we need the scheme "FreeCAD x.x.x" in order
# to check if it is exactly this version (to support side-by-side installations)
!define APP_SERIES_NAME "${APP_VERSION_MAJOR}.${APP_VERSION_MINOR}"
!define APP_SERIES_KEY "${APP_VERSION_MAJOR}${APP_VERSION_MINOR}${APP_VERSION_PATCH}${APP_VERSION_EMERGENCY}"
!define APP_SERIES_KEY2 "${APP_VERSION_MAJOR}.${APP_VERSION_MINOR}.${APP_VERSION_PATCH}${APP_EMERGENCY_DOT}${APP_VERSION_EMERGENCY}"
# FISSION180: Fission 180's installer (docs/fission180/core-patches.md #13). APP_NAME is read from
# the program itself ("ExeName" = Fission 180, version.nsh), so every key below is Fission 180's
# own: SOFTWARE\Fission180114, Uninstall\Fission180114, the Fission180.Document class and the
# settings folder %APPDATA%\Fission180. A FreeCAD on the same machine is never touched.
!define APP_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\${APP_NAME}.exe"
!define APP_DIR "${APP_NAME}" # FISSION180: "Program Files\Fission180" (FreeCAD: "FreeCAD 1.1")
# Fixme: FC should use different preferences folder for every release
!define APP_DIR_USERDATA ${APP_NAME}
#!define APP_DIR_USERDATA "${APP_NAME}${APP_VERSION_MAJOR}.${APP_VERSION_MINOR}"
!define APP_SHORTCUT_INFO "${APP_NAME} - Parametric CAD with the Fusion workflow" # FISSION180
!define APP_INFO "Install/Uninstall ${APP_NAME}"
!define APP_WEBPAGE "https://github.com/Luca0422git/Fission-180" # FISSION180
!define APP_WEBPAGE_INFO "${APP_NAME} on GitHub" # FISSION180
!define APP_WIKI "https://github.com/Luca0422git/Fission-180/issues" # FISSION180
!define APP_WIKI_INFO "Report a ${APP_NAME} problem" # FISSION180
!define APP_COPYRIGHT "${APP_NAME} © 2026 ${APP_NAME} contributors, based on FreeCAD © 2001-${COPYRIGHT_YEAR} by the FreeCAD Team" # FISSION180

!define APP_RUN "bin\${APP_NAME}.exe"
!define BIN_FREECAD "${APP_NAME}.exe"
!define BIN_FREECADCMD "${APP_NAME}Cmd.exe" # FISSION180: Fission180Cmd.exe keeps its case

!define APP_REGKEY "SOFTWARE\${APP_NAME}${APP_SERIES_KEY}" # like "FreeCAD0180"
!define APP_REGKEY_SETUP "${APP_REGKEY}\Setup"
!define APP_REGKEY_SETTINGS "${APP_REGKEY}\Settings"

!define APP_REGNAME_DOC "${APP_NAME}.Document"

!define APP_EXT ".FCStd"
!define APP_EXT1 ".FCStd1"
!define APP_MIME_TYPE "application/x-zip-compressed"

!define APP_EXT_BAK ".FCBak"
!define APP_EXT_MACRO ".FCMacro"
!define APP_EXT_MAT ".FCMat"
!define APP_EXT_SCRIPT ".FCScript"

!define APP_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SETUP_UNINSTALLER_KEY}"

#--------------------------------
# Setup settings

!define SETUP_EXE ${ExeFile}

# FISSION180: own icon and pictures, made by tools/fission180/make_app_icons.py
!define SETUP_ICON "icons\Fission180.ico"
!define SETUP_HEADERIMAGE "graphics\fission180-header.bmp"
!define SETUP_WIZARDIMAGE "graphics\fission180-banner.bmp"
!define SETUP_UNINSTALLER "Uninstall-${APP_NAME}.exe"
!define SETUP_UNINSTALLER_KEY "${APP_NAME}${APP_SERIES_KEY}"

#--------------------------------
# Variables that are shared between multiple files

Var APPDATemp
Var AppPre
var AppSubfolder
Var AppSuff
Var CreateDesktopIcon
Var CreateFileAssociations
Var OldVersionNumber
Var OriginalCmdInstDir
Var Pointer
Var RemoveInstDir
Var Search
Var StartmenuFolder
Var String
Var UserList
Var LangName
