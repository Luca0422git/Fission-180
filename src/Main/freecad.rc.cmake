// SPDX-License-Identifier: LGPL-2.1-or-later
/////////////////////////////////////////////////////////////////////////////
// For info about the file structrure see
// https://docs.microsoft.com/en-us/windows/win32/menurc/versioninfo-resource
// and
// https://docs.microsoft.com/en-us/windows/win32/menurc/stringfileinfo-block

// Icon
//
// Icon with lowest ID value placed first to ensure application icon
// remains consistent on all systems.
// FISSION180: Fission 180's own icon and version strings (docs/fission180/core-patches.md #9)
IDI_ICON1               ICON    DISCARDABLE     "${FISSION180_WIN_ICON}"

// File info for the FreeCAD.exe
//
1 VERSIONINFO
FILEVERSION ${FISSION180_VERSION_MAJOR},${FISSION180_VERSION_MINOR},${FISSION180_VERSION_PATCH},${PACKAGE_BUILD_VERSION}
BEGIN
    BLOCK "StringFileInfo"
    BEGIN
        BLOCK "040904b0" // 409 stands for US English
        BEGIN
            VALUE "CompanyName", "${FISSION180_APP_NAME} contributors"
            VALUE "FileDescription", "${FISSION180_APP_NAME} main executable (based on ${PROJECT_NAME})"
            VALUE "InternalName", "${FISSION180_APP_NAME}.exe"
            VALUE "LegalCopyright", "(C) Fission 180 contributors; based on FreeCAD, (C) FreeCAD contributors (LGPL-2.1-or-later)"
            VALUE "OriginalFilename", "${FISSION180_APP_NAME}.exe"
            VALUE "ProductName", "${FISSION180_APP_NAME}"
            VALUE "ProductVersion", "${FISSION180_VERSION}"
        END
    END
    BLOCK "VarFileInfo"
    BEGIN
        VALUE "Translation", 0x409, 1200 //US English, Unicode
    END
END
