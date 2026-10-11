Unicode True
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "WinVer.nsh"
!include "x64.nsh"

!ifndef BUNDLE
  !error "Build with scripts/build_windows.py."
!endif
!ifndef OUTPUT
  !error "Installer output path is required."
!endif
!ifndef VERSION
  !define VERSION "1.1.1"
!endif

Name "OpenBEXI Discovery"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\REIResearchExplorer"
InstallDirRegKey HKCU "Software\openbexi\REIResearchExplorer" "InstallPath"
RequestExecutionLevel user
SetCompressor /SOLID zlib
BrandingText "OpenBEXI Discovery Â· V${VERSION}"
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "OpenBEXI Discovery"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "FileDescription" "OpenBEXI Discovery Windows installer"
VIAddVersionKey "LegalCopyright" "OpenBEXI Discovery contributors"

!define MUI_ICON "${ICON}"
!define MUI_UNICON "${ICON}"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "Install OpenBEXI Discovery"
!define MUI_WELCOMEPAGE_TEXT "A personalized learning and research workspace for this Windows account.$\r$\n$\r$\nPython, SQLite, and dependencies are included. Saved material works offline. Administrator access is not required.$\r$\n$\r$\nInternet is needed for public sources. AI uses your own OpenAI API key, entered inside the app after installation."
!define MUI_FINISHPAGE_RUN "$INSTDIR\REIResearchExplorer.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Open OpenBEXI Discovery"
!define MUI_FINISHPAGE_LINK "Installation help and source code"
!define MUI_FINISHPAGE_LINK_LOCATION "https://github.com/arcazj/openbexi_discovery#install-on-windows"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function .onInit
  SetShellVarContext current
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_ICONSTOP "This installer requires Windows 10 or 11, 64-bit."
    Abort
  ${EndIf}
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "This package requires 64-bit Windows. A 32-bit package is not included."
    Abort
  ${EndIf}
FunctionEnd

Section "OpenBEXI Discovery (required)" AppFiles
  SectionIn RO
  IfFileExists "$INSTDIR\REIResearchExplorer.exe" upgrade fresh
  upgrade:
    ExecWait '"$INSTDIR\REIResearchExplorer.exe" --quit' $0
    ${If} $0 != 0
      MessageBox MB_ICONSTOP "Close OpenBEXI Discovery before updating, then run Setup again."
      Abort
    ${EndIf}
  fresh:
  SetOutPath "$INSTDIR"
  File /r "${BUNDLE}\*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  ; Remove only the known legacy shortcuts during an upgrade.
  Delete "$DESKTOP\REI Research Explorer.lnk"
  Delete "$SMPROGRAMS\REI Research Explorer\REI Research Explorer.lnk"
  Delete "$SMPROGRAMS\REI Research Explorer\Uninstall.lnk"
  RMDir "$SMPROGRAMS\REI Research Explorer"
  CreateDirectory "$SMPROGRAMS\OpenBEXI Discovery"
  CreateShortcut "$SMPROGRAMS\OpenBEXI Discovery\OpenBEXI Discovery.lnk" "$INSTDIR\REIResearchExplorer.exe"
  CreateShortcut "$SMPROGRAMS\OpenBEXI Discovery\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\openbexi\REIResearchExplorer" "InstallPath" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\REIResearchExplorer" "DisplayName" "OpenBEXI Discovery"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\REIResearchExplorer" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\REIResearchExplorer" "Publisher" "openbexi"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\REIResearchExplorer" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\REIResearchExplorer" "DisplayIcon" "$INSTDIR\REIResearchExplorer.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\REIResearchExplorer" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\REIResearchExplorer" "QuietUninstallString" '$\"$INSTDIR\Uninstall.exe$\" /S'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\REIResearchExplorer" "URLInfoAbout" "https://github.com/arcazj/openbexi_discovery"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\REIResearchExplorer" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\REIResearchExplorer" "NoRepair" 1
SectionEnd

Section "Desktop shortcut" DesktopShortcut
  CreateShortcut "$DESKTOP\OpenBEXI Discovery.lnk" "$INSTDIR\REIResearchExplorer.exe"
SectionEnd

Function un.onInit
  SetShellVarContext current
FunctionEnd

Section "Uninstall"
  ExecWait '"$INSTDIR\REIResearchExplorer.exe" --quit' $0
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "Close OpenBEXI Discovery before uninstalling, then try again."
    Abort
  ${EndIf}
  ; Exact packaged files only. New user files, settings, and browser research stay intact.
  !include "${UNINSTALL_FILES}"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  Delete "$DESKTOP\OpenBEXI Discovery.lnk"
  Delete "$SMPROGRAMS\OpenBEXI Discovery\OpenBEXI Discovery.lnk"
  Delete "$SMPROGRAMS\OpenBEXI Discovery\Uninstall.lnk"
  RMDir "$SMPROGRAMS\OpenBEXI Discovery"
  DeleteRegKey HKCU "Software\openbexi\REIResearchExplorer"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\REIResearchExplorer"
SectionEnd
