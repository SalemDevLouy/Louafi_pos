!include "MUI2.nsh"

Name "LouafiPOS"
OutFile "..\dist\LouafiPOS_Setup.exe"
InstallDir "$PROGRAMFILES\LouafiPOS"
InstallDirRegKey HKCU "Software\LouafiPOS" ""
RequestExecutionLevel admin

!define MUI_ABORTWARNING
!define MUI_ICON "..\assets\logo.ico"
!define MUI_UNICON "..\assets\logo.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "French"

Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    File /r "..\dist\LouafiPOS\*.*"

    CreateDirectory "$INSTDIR\backups"
    CreateDirectory "$INSTDIR\receipts"
    CreateDirectory "$INSTDIR\assets"

    CreateShortCut "$DESKTOP\LouafiPOS.lnk" "$INSTDIR\LouafiPOS.exe"
    CreateDirectory "$SMPROGRAMS\LouafiPOS"
    CreateShortCut "$SMPROGRAMS\LouafiPOS\LouafiPOS.lnk" "$INSTDIR\LouafiPOS.exe"
    CreateShortCut "$SMPROGRAMS\LouafiPOS\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

    WriteRegStr HKCU "Software\LouafiPOS" "" "$INSTDIR"
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LouafiPOS" \
        "DisplayName" "LouafiPOS"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LouafiPOS" \
        "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LouafiPOS" \
        "DisplayVersion" "1.0.0"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LouafiPOS" \
        "Publisher" "SalemDevLouy"
SectionEnd

Section "Uninstall"
    Delete "$DESKTOP\LouafiPOS.lnk"
    Delete "$SMPROGRAMS\LouafiPOS\LouafiPOS.lnk"
    Delete "$SMPROGRAMS\LouafiPOS\Uninstall.lnk"
    RMDir "$SMPROGRAMS\LouafiPOS"
    RMDir /r "$INSTDIR"
    DeleteRegKey HKCU "Software\LouafiPOS"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LouafiPOS"
SectionEnd
