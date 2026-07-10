Unicode True

!include "MUI2.nsh"
!include "Sections.nsh"

!define APP_NAME "Oxford to Notion"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "johnny05285514-code"
!define APP_EXE "Oxford to Notion.exe"
!define APP_REG_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\OxfordToNotion"

Name "${APP_NAME}"
OutFile "release\Oxford-to-Notion-Setup-${APP_VERSION}.exe"
InstallDir "$LOCALAPPDATA\Programs\Oxford to Notion"
InstallDirRegKey HKCU "${APP_REG_KEY}" "InstallLocation"
RequestExecutionLevel user
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show
BrandingText "Oxford to Notion"

VIProductVersion "1.0.0.0"
VIAddVersionKey "ProductName" "${APP_NAME}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey "FileDescription" "Oxford Learner's Dictionaries to Notion desktop app"
VIAddVersionKey "LegalCopyright" "MIT License"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Open Oxford to Notion"
!define MUI_LANGDLL_REGISTRY_ROOT HKCU
!define MUI_LANGDLL_REGISTRY_KEY "Software\OxfordToNotion"
!define MUI_LANGDLL_REGISTRY_VALUENAME "InstallerLanguage"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "SimpChinese"

Section "Oxford to Notion (required)" SecMain
    SectionIn RO
    SetOutPath "$INSTDIR"
    SetOverwrite on
    File "dist\${APP_EXE}"
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    CreateShortcut "$SMPROGRAMS\Oxford to Notion.lnk" "$INSTDIR\${APP_EXE}"

    WriteRegStr HKCU "${APP_REG_KEY}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKCU "${APP_REG_KEY}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "${APP_REG_KEY}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKCU "${APP_REG_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "${APP_REG_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
    WriteRegStr HKCU "${APP_REG_KEY}" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
    WriteRegStr HKCU "${APP_REG_KEY}" "QuietUninstallString" '$\"$INSTDIR\Uninstall.exe$\" /S'
    WriteRegDWORD HKCU "${APP_REG_KEY}" "NoModify" 1
    WriteRegDWORD HKCU "${APP_REG_KEY}" "NoRepair" 1
SectionEnd

Section /o "Desktop shortcut" SecDesktop
    CreateShortcut "$DESKTOP\Oxford to Notion.lnk" "$INSTDIR\${APP_EXE}"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir "$INSTDIR"

    Delete "$DESKTOP\Oxford to Notion.lnk"
    Delete "$SMPROGRAMS\Oxford to Notion.lnk"
    DeleteRegKey HKCU "${APP_REG_KEY}"

    ; Intentionally preserve $APPDATA\Oxford to Notion so uninstalling does
    ; not destroy the user's private Notion configuration.
SectionEnd

Function .onInit
    !insertmacro MUI_LANGDLL_DISPLAY
    SectionSetFlags ${SecDesktop} ${SF_SELECTED}
FunctionEnd

Function un.onInit
    !insertmacro MUI_UNGETLANGUAGE
FunctionEnd
