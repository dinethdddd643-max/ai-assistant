; ─────────────────────────────────────────────────────────────────────────────
;  AI Assistant Installer  —  Fixed Version
; ─────────────────────────────────────────────────────────────────────────────

!define APP_NAME      "AI Assistant"
!define APP_VERSION   "1.0.0"
!define PUBLISHER     "YourName"
!define INSTALL_DIR   "$PROGRAMFILES64\AIAssistant"
!define UNINSTALLER   "uninstall.exe"

!include "MUI2.nsh"
!include "LogicLib.nsh"

; Move working directory to project root (one level up from installer/)
!cd ".."

Name          "${APP_NAME} ${APP_VERSION}"
OutFile       "installer\AIAssistant_Setup.exe"
InstallDir    "${INSTALL_DIR}"
RequestExecutionLevel admin

; ── Pages ─────────────────────────────────────────────────────────────────────
!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "installer\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
Page custom ComponentsPage ComponentsPageLeave
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ── Variables ─────────────────────────────────────────────────────────────────
Var CreateShortcut
Var RunSetupAfter
Var StartOnBoot

; ── Custom Options Page ───────────────────────────────────────────────────────
Function ComponentsPage
    nsDialogs::Create 1018
    Pop $0

    ${NSD_CreateLabel} 0 0 100% 12u "Select installation options:"
    Pop $0

    ${NSD_CreateCheckbox} 10 22u 80% 12u "Create desktop shortcuts"
    Pop $CreateShortcut
    ${NSD_Check} $CreateShortcut

    ${NSD_CreateCheckbox} 10 42u 80% 12u "Start AI Assistant server automatically on Windows startup"
    Pop $StartOnBoot

    ${NSD_CreateCheckbox} 10 62u 80% 12u "Launch Model Downloader after installation (recommended)"
    Pop $RunSetupAfter
    ${NSD_Check} $RunSetupAfter

    nsDialogs::Show
FunctionEnd

Function ComponentsPageLeave
    ${NSD_GetState} $CreateShortcut $CreateShortcut
    ${NSD_GetState} $StartOnBoot   $StartOnBoot
    ${NSD_GetState} $RunSetupAfter $RunSetupAfter
FunctionEnd

; ── Main Install Section ──────────────────────────────────────────────────────
Section "Main Application" SEC_MAIN
    SectionIn RO

    ; Copy backend folder
    SetOutPath "$INSTDIR\backend"
    File /r "backend\*.*"

    ; Copy scripts folder
    SetOutPath "$INSTDIR\scripts"
    File /r "scripts\*.*"

    ; Copy models list
    SetOutPath "$INSTDIR\models_list"
    File /r "models_list\*.*"

    ; Create empty models directory
    CreateDirectory "$INSTDIR\models"

    ; Go back to install root for launch.bat
    SetOutPath "$INSTDIR"

    ; Write the launch batch file
    FileOpen  $0 "$INSTDIR\launch.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "title AI Assistant Server$\r$\n"
    FileWrite $0 "cd /d %~dp0backend$\r$\n"
    FileWrite $0 "echo Starting AI Assistant...$\r$\n"
    FileWrite $0 "python server.py$\r$\n"
    FileWrite $0 "pause$\r$\n"
    FileClose $0

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\${UNINSTALLER}"

    ; Registry entry for Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAssistant" \
        "DisplayName"     "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAssistant" \
        "DisplayVersion"  "${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAssistant" \
        "Publisher"       "${PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAssistant" \
        "UninstallString" "$INSTDIR\${UNINSTALLER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAssistant" \
        "InstallLocation" "$INSTDIR"

SectionEnd

; ── Check Python (open browser instead of silent download) ────────────────────
Section "-Check Python"
    DetailPrint "Checking for Python..."
    nsExec::ExecToStack 'python --version'
    Pop $0
    ${If} $0 != 0
        MessageBox MB_YESNO \
            "Python was not found on this PC.$\n$\nClick YES to open the Python download page.$\nInstall Python, then run AI Assistant Setup again." \
            IDYES open_python IDNO skip_python
        open_python:
            ExecShell "open" "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
        skip_python:
    ${Else}
        DetailPrint "Python found."
    ${EndIf}
SectionEnd

; ── Desktop Shortcuts ─────────────────────────────────────────────────────────
Section "-Shortcuts"
    ${If} $CreateShortcut == ${BST_CHECKED}
        CreateShortcut "$DESKTOP\AI Assistant.lnk" \
            "$INSTDIR\launch.bat"
        CreateShortcut "$DESKTOP\AI Assistant Setup.lnk" \
            "pythonw.exe" '"$INSTDIR\scripts\model_downloader.py"'
    ${EndIf}
SectionEnd

; ── Start on Boot ─────────────────────────────────────────────────────────────
Section "-StartOnBoot"
    ${If} $StartOnBoot == ${BST_CHECKED}
        WriteRegStr HKCU \
            "Software\Microsoft\Windows\CurrentVersion\Run" \
            "AIAssistant" '"$INSTDIR\launch.bat"'
    ${EndIf}
SectionEnd

; ── Launch Model Downloader ───────────────────────────────────────────────────
Section "-LaunchSetup"
    ${If} $RunSetupAfter == ${BST_CHECKED}
        DetailPrint "Launching Model Downloader..."
        ExecShell "open" "pythonw.exe" '"$INSTDIR\scripts\model_downloader.py"'
    ${EndIf}
SectionEnd

; ── Uninstaller ───────────────────────────────────────────────────────────────
Section "Uninstall"
    RMDir /r "$INSTDIR\backend"
    RMDir /r "$INSTDIR\scripts"
    RMDir /r "$INSTDIR\models_list"
    Delete   "$INSTDIR\launch.bat"
    Delete   "$INSTDIR\assistant.db"
    Delete   "$INSTDIR\launch_config.txt"
    Delete   "$INSTDIR\${UNINSTALLER}"

    MessageBox MB_YESNO \
        "Delete downloaded AI models?$\nThis will free several GB of disk space." \
        IDNO keep_models
        RMDir /r "$INSTDIR\models"
    keep_models:

    RMDir "$INSTDIR"

    Delete "$DESKTOP\AI Assistant.lnk"
    Delete "$DESKTOP\AI Assistant Setup.lnk"

    DeleteRegKey   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAssistant"
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "AIAssistant"

    MessageBox MB_OK "AI Assistant has been uninstalled."
SectionEnd
