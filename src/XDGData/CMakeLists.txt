include(GNUInstallDirs)

if(NOT DEFINED APPDATA_RELEASE_DATE)
    if(EXISTS "${CMAKE_SOURCE_DIR}/.git")
        execute_process(COMMAND git log -1 --pretty=%cd --date=short
            OUTPUT_VARIABLE APPDATA_RELEASE_DATE
            WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
            OUTPUT_STRIP_TRAILING_WHITESPACE)
    else()
        string(TIMESTAMP APPDATA_RELEASE_DATE "%Y-%m-%d")
    endif()
endif()

# FISSION180: Fission 180's own desktop entry, AppStream data and MIME package under Fission 180's
# id (FISSION180_DESKTOP_ID), so a FreeCAD installed on the same machine keeps its own menu
# entry (docs/fission180/core-patches.md #11). FreeCAD's org.freecad.FreeCAD.* files stay in
# this folder unused, which keeps upstream merges simple.
configure_file(
    ${FISSION180_DESKTOP_ID}.metainfo.xml.in
    ${CMAKE_BINARY_DIR}/${FISSION180_DESKTOP_ID}.metainfo.xml
)
install(
    FILES ${CMAKE_BINARY_DIR}/${FISSION180_DESKTOP_ID}.metainfo.xml
    DESTINATION ${CMAKE_INSTALL_DATAROOTDIR}/metainfo
)

install(
    FILES ${FISSION180_DESKTOP_ID}.desktop
    DESTINATION ${CMAKE_INSTALL_DATAROOTDIR}/applications
)

install(
    FILES ${FISSION180_DESKTOP_ID}.xml
    DESTINATION ${CMAKE_INSTALL_DATAROOTDIR}/mime/packages
)

configure_file(
    FreeCAD.thumbnailer.in
    ${CMAKE_BINARY_DIR}/FreeCAD.thumbnailer
)
install(
    FILES ${CMAKE_BINARY_DIR}/FreeCAD.thumbnailer
    DESTINATION ${CMAKE_INSTALL_DATAROOTDIR}/thumbnailers
)

configure_file(
    ${CMAKE_SOURCE_DIR}/src/Tools/freecad-thumbnailer.in
    ${CMAKE_BINARY_DIR}/freecad-thumbnailer
)
install(
    PROGRAMS ${CMAKE_BINARY_DIR}/freecad-thumbnailer
    TYPE BIN
)
