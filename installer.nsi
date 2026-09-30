Unicode True
Var BackupExe
Var BackupIcon
Var BackupUninstaller
Var ReplaceStarted

!include "MUI2.nsh"
!include "Sections.nsh"

!define APP_NAME "Oxford to Notion"
!ifndef APP_VERSION
!error "APP_VERSION must be supplied by build_installer.bat"
!endif
!define APP_PUBLISHER "johnny05285514-code"
!define APP_EXE "Oxford to Notion.exe"
!define APP_REG_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\OxfordToNotion"

Name "${APP_NAME}"
OutFile "release\Oxford-to-Notion-Setup-${APP_VERSION}.exe"
InstallDir "$LOCALAPPDATA\Programs\Oxford to Notion"
InstallDirRegKey HKCU "${APP_REG_KEY}" "InstallLocation"
RequestExecutionLevel user
Icon "assets\app-icon.ico"
UninstallIcon "assets\app-icon.ico"
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show
BrandingText "Oxford to Notion"

Var ExistingVersion
Var ExistingInstallDir

VIProductVersion "${APP_VERSION}.0"
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
!define MUI_PAGE_CUSTOMFUNCTION_PRE DirectoryPagePre
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "SimpChinese"

LangString UpgradeDetected ${LANG_ENGLISH} "Oxford to Notion $ExistingVersion is installed. This setup will update it to ${APP_VERSION} in the existing folder."
LangString UpgradeDetected ${LANG_SIMPCHINESE} "检测到 Oxford to Notion $ExistingVersion。安装程序将沿用原目录并更新至 ${APP_VERSION}。"
LangString CloseRunningApp ${LANG_ENGLISH} "Oxford to Notion is still running. Close it, then choose Retry."
LangString CloseRunningApp ${LANG_SIMPCHINESE} "Oxford to Notion 仍在运行。请关闭软件，然后选择“重试”。"
LangString InstallFailed ${LANG_ENGLISH} "The existing application could not be replaced. The update has stopped; your current installation and personal settings were not removed."
LangString InstallFailed ${LANG_SIMPCHINESE} "无法替换现有程序，更新已停止。当前安装和个人设置没有被删除。"
LangString RecoveryFailed ${LANG_ENGLISH} "Update failed and some old files could not be restored. Recovery files remain in the installation folder with a .previous suffix. Do not delete them. Personal settings were not changed."
LangString RecoveryFailed ${LANG_SIMPCHINESE} "更新失败，部分旧文件无法自动恢复。安装目录中的 .previous 文件是恢复备份，请勿删除。个人配置未被修改。"

Section "Oxford to Notion (required)" SecMain
    SectionIn RO
    SetOutPath "$INSTDIR"
    SetOverwrite try
checkRunning:
    FindWindow $0 "" "${APP_NAME}"
    StrCmp $0 0 appClosed
    MessageBox MB_ICONEXCLAMATION|MB_RETRYCANCEL "$(CloseRunningApp)" /SD IDCANCEL IDRETRY checkRunning IDCANCEL installCancelled
installCancelled:
    Abort
appClosed:
    InitPluginsDir
    SetOutPath "$PLUGINSDIR\payload"
    ClearErrors
    File "dist\${APP_EXE}"
    File /oname=app-icon.ico "assets\app-icon.ico"
    WriteUninstaller "$PLUGINSDIR\payload\Uninstall.exe"
    IfErrors installFailed
    ExecWait '"$PLUGINSDIR\payload\${APP_EXE}" --smoke-test --expected-version ${APP_VERSION}' $0
    IfErrors installFailed
    StrCmp $0 0 0 installFailed
    StrCpy $BackupExe 0
    StrCpy $BackupIcon 0
    StrCpy $BackupUninstaller 0
    StrCpy $ReplaceStarted 0
    ; Never overwrite an earlier recovery backup.
    IfFileExists "$INSTDIR\${APP_EXE}.previous" installFailed
    IfFileExists "$INSTDIR\app-icon.ico.previous" installFailed
    IfFileExists "$INSTDIR\Uninstall.exe.previous" installFailed
    IfFileExists "$INSTDIR\${APP_EXE}" 0 backupIcon
    ClearErrors
    Rename "$INSTDIR\${APP_EXE}" "$INSTDIR\${APP_EXE}.previous"
    IfErrors rollbackInstall
    StrCpy $BackupExe 1
backupIcon:
    IfFileExists "$INSTDIR\app-icon.ico" 0 backupUninstaller
    ClearErrors
    Rename "$INSTDIR\app-icon.ico" "$INSTDIR\app-icon.ico.previous"
    IfErrors rollbackInstall
    StrCpy $BackupIcon 1
backupUninstaller:
    IfFileExists "$INSTDIR\Uninstall.exe" 0 replaceFiles
    ClearErrors
    Rename "$INSTDIR\Uninstall.exe" "$INSTDIR\Uninstall.exe.previous"
    IfErrors rollbackInstall
    StrCpy $BackupUninstaller 1
replaceFiles:
    StrCpy $ReplaceStarted 1
    ClearErrors
    CopyFiles /SILENT "$PLUGINSDIR\payload\${APP_EXE}" "$INSTDIR\${APP_EXE}"
    IfErrors rollbackInstall
    CopyFiles /SILENT "$PLUGINSDIR\payload\app-icon.ico" "$INSTDIR\app-icon.ico"
    IfErrors rollbackInstall
    CopyFiles /SILENT "$PLUGINSDIR\payload\Uninstall.exe" "$INSTDIR\Uninstall.exe"
    IfErrors rollbackInstall
    ExecWait '"$INSTDIR\${APP_EXE}" --smoke-test --expected-version ${APP_VERSION}' $0
    IfErrors rollbackInstall
    StrCmp $0 0 0 rollbackInstall
    SetOutPath "$INSTDIR"
    Delete "$INSTDIR\Oxford-to-Notion-v1.3.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.1.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.2.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.3.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.4.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.5.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.6.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.7.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.8.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.5.0.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.5.1.ico"

    CreateShortcut "$SMPROGRAMS\Oxford to Notion.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\app-icon.ico" 0
    IfFileExists "$DESKTOP\Oxford to Notion.lnk" 0 +2
    CreateShortcut "$DESKTOP\Oxford to Notion.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\app-icon.ico" 0

    WriteRegStr HKCU "${APP_REG_KEY}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKCU "${APP_REG_KEY}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "${APP_REG_KEY}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKCU "${APP_REG_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "${APP_REG_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
    WriteRegStr HKCU "${APP_REG_KEY}" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
    WriteRegStr HKCU "${APP_REG_KEY}" "QuietUninstallString" '$\"$INSTDIR\Uninstall.exe$\" /S'
    WriteRegDWORD HKCU "${APP_REG_KEY}" "NoModify" 1
    WriteRegDWORD HKCU "${APP_REG_KEY}" "NoRepair" 1
    Delete "$INSTDIR\${APP_EXE}.previous"
    Delete "$INSTDIR\app-icon.ico.previous"
    Delete "$INSTDIR\Uninstall.exe.previous"
    Goto installComplete

rollbackInstall:
    StrCmp $ReplaceStarted 1 0 restoreBackups
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\app-icon.ico"
    Delete "$INSTDIR\Uninstall.exe"
restoreBackups:
    StrCpy $1 0
    ClearErrors
    StrCmp $BackupExe 1 0 restoreIcon
    Rename "$INSTDIR\${APP_EXE}.previous" "$INSTDIR\${APP_EXE}"
    IfErrors 0 +2
    StrCpy $1 1
restoreIcon:
    ClearErrors
    StrCmp $BackupIcon 1 0 restoreUninstaller
    Rename "$INSTDIR\app-icon.ico.previous" "$INSTDIR\app-icon.ico"
    IfErrors 0 +2
    StrCpy $1 1
restoreUninstaller:
    ClearErrors
    StrCmp $BackupUninstaller 1 0 recoveryDone
    Rename "$INSTDIR\Uninstall.exe.previous" "$INSTDIR\Uninstall.exe"
    IfErrors 0 +2
    StrCpy $1 1
recoveryDone:
    StrCmp $1 1 0 installFailed
    SetErrorLevel 1
    MessageBox MB_ICONSTOP|MB_OK "$(RecoveryFailed)" /SD IDOK
    Abort
installFailed:
    SetErrorLevel 1
    MessageBox MB_ICONSTOP|MB_OK "$(InstallFailed)" /SD IDOK
    Abort
installComplete:
SectionEnd

Section /o "Desktop shortcut" SecDesktop
    CreateShortcut "$DESKTOP\Oxford to Notion.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\app-icon.ico" 0
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\app-icon.ico"
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\Oxford-to-Notion-v1.3.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.1.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.2.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.3.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.4.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.5.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.6.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.7.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.4.8.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.5.0.ico"
    Delete "$INSTDIR\Oxford-to-Notion-v1.5.1.ico"
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
    ReadRegStr $ExistingVersion HKCU "${APP_REG_KEY}" "DisplayVersion"
    ReadRegStr $ExistingInstallDir HKCU "${APP_REG_KEY}" "InstallLocation"
    StrCmp $ExistingInstallDir "" initDone
    StrCpy $INSTDIR "$ExistingInstallDir"
    StrCmp $ExistingVersion "" initDone
    MessageBox MB_ICONINFORMATION|MB_OK "$(UpgradeDetected)" /SD IDOK
initDone:
FunctionEnd

Function DirectoryPagePre
    StrCmp $ExistingInstallDir "" showDirectory
    Abort
showDirectory:
FunctionEnd

Function un.onInit
    !insertmacro MUI_UNGETLANGUAGE
FunctionEnd
