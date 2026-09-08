Unicode true
!include "MUI2.nsh"
Name "Comedy Host Studio 5.5.4"
OutFile "..\dist\ComedyHostStudio_Setup_5.5.4.exe"
InstallDir "$LOCALAPPDATA\Programs\ComedyHostStudio"
RequestExecutionLevel user
SetCompressor /SOLID lzma
VIProductVersion "5.5.4.0"
VIAddVersionKey "ProductName" "Comedy Host Studio"
VIAddVersionKey "ProductVersion" "5.5.4"
VIAddVersionKey "FileVersion" "5.5.4.0"
VIAddVersionKey "FileDescription" "Comedy Host Studio 5.5.4 Clean Installer"
VIAddVersionKey "LegalCopyright" "Comedy Host Studio contributors"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Section "Comedy Host Studio"
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  File /r "..\payload\*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\Comedy Host Studio"
  CreateShortcut "$SMPROGRAMS\Comedy Host Studio\Comedy Host Studio.lnk" "$INSTDIR\ComedyHostStudio.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ComedyHostStudio" "DisplayName" "Comedy Host Studio 5.5.4"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ComedyHostStudio" "DisplayVersion" "5.5.4"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ComedyHostStudio" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ComedyHostStudio" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ComedyHostStudio" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ComedyHostStudio" "NoRepair" 1
SectionEnd
Section "Uninstall"
  SetShellVarContext current
  Delete "$SMPROGRAMS\Comedy Host Studio\Comedy Host Studio.lnk"
  RMDir "$SMPROGRAMS\Comedy Host Studio"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ComedyHostStudio"
  RMDir /r "$INSTDIR"
SectionEnd
