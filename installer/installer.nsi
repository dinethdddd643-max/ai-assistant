; ─────────────────────────────────────────────────────────────────────────────
;  AI Assistant Installer  —  NSIS Script
;  Build:  makensis installer.nsi
; ─────────────────────────────────────────────────────────────────────────────

!define APP_NAME      "AI Assistant"
!define APP_VERSION   "1.0.0"
!define PUBLISHER     "YourName"
!define APP_EXE       "launch.bat"
!define INSTALL_DIR   "$PROGRAMFILES64\AIAssistant"
!define UNINSTALLER   "uninstall.exe"

; Modern UI
!include "MUI2.nsh"
!include "LogicLib.nsh"

Name          "${APP_NAME} ${APP_VERSION}"
OutFile       "AIAssistant_Setup.exe"
InstallDir    "${INSTALL_DIR}"
RequestExecutionLevel admin

; ── Pages ─────────────────────────────────────────────────────────────────────
!define MUI_ABORTWARNING
!define MUI_ICON   "assets\icon.ico"    ; optional icon
!define MUI_UNICON "assets\icon.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
Page custom ComponentsPage ComponentsPageLeave
!insertmacro MUI_PAGE_INSTFILES
Page custom FinishPage

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ── Variables ─────────────────────────────────────────────────────────────────
Var InstallPython
Var InstallPip
Var CreateShortcut
Var RunSetupAfter
Var StartOnBoot

; ── Custom Pages ──────────────────────────────────────────────────────────────
Function ComponentsPage
    nsDialogs::Create 1018
    Pop $0

    ; Title
    ${NSD_CreateLabel} 0 0 100% 12u "Select installation options:"
    Pop $0

    ; Python
    ${NSD_CreateCheckbox} 10 20u 80% 12u "Install Python 3.11 (required if not already installed)"
    Pop $InstallPython
    ${NSD_Check} $InstallPython

    ; Pip packages
    ${NSD_CreateCheckbox} 10 38u 80% 12u "Install required Python packages (llama-cpp-python, flask, etc.)"
    Pop $InstallPip
    ${NSD_Check} $InstallPip

    ; Desktop shortcut
    ${NSD_CreateCheckbox} 10 56u 80% 12u "Create desktop shortcut"
    Pop $CreateShortcut
    ${NSD_Check} $CreateShortcut

    ; Start on boot
    ${NSD_CreateCheckbox} 10 74u 80% 12u "Start AI Assistant server automatically on Windows startup"
    Pop $StartOnBoot

    ; Run model downloader
    ${NSD_CreateCheckbox} 10 92u 80% 12u "Launch Model Downloader after installation"
    Pop $RunSetupAfter
    ${NSD_Check} $RunSetupAfter

    nsDialogs::Show
FunctionEnd

Function ComponentsPageLeave
    ${NSD_GetState} $InstallPython $InstallPython
    ${NSD_GetState} $InstallPip    $InstallPip
    ${NSD_GetState} $CreateShortcut $CreateShortcut
    ${NSD_GetState} $StartOnBoot   $StartOnBoot
    ${NSD_GetState} $RunSetupAfter $RunSetupAfter
FunctionEnd

Function FinishPage
    nsDialogs::Create 1018
    Pop $0
    ${NSD_CreateLabel} 0 0 100% 40u "${APP_NAME} has been installed.$\n$\nClick Finish — the Model Downloader will open so you can choose your AI model."
    Pop $0
    nsDialogs::Show
FunctionEnd

; ── Install Section ───────────────────────────────────────────────────────────
Section "Main Application" SEC_MAIN
    SectionIn RO  ; always installed

    SetOutPath "$INSTDIR"

    ; Copy all application files
    File /r "backend\*.*"
    File /r "scripts\*.*"
    File /r "models_list\*.*"
    CreateDirectory "$INSTDIR\models"

    ; Write launch batch
    FileOpen  $0 "$INSTDIR\launch.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "title AI Assistant Server$\r$\n"
    FileWrite $0 "cd /d %~dp0$\r$\n"
    FileWrite $0 "python server.py$\r$\n"
    FileWrite $0 "pause$\r$\n"
    FileClose $0

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\${UNINSTALLER}"

    ; Registry uninstall entry
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAssistant" \
        "DisplayName"    "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAssistant" \
        "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAssistant" \
        "Publisher"      "${PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAssistant" \
        "UninstallString" "$INSTDIR\${UNINSTALLER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAssistant" \
        "InstallLocation" "$INSTDIR"
SectionEnd

Section "Python Packages" SEC_PIP
    DetailPrint "Installing Python packages..."
    nsExec::ExecToLog 'pip install flask llama-cpp-python'
    ; Note: for CUDA use: pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
    ; Note: for Vulkan:   pip install llama-cpp-python[vulkan]
SectionEnd

Section "-Python Install"
    ${If} $InstallPython == ${BST_CHECKED}
        DetailPrint "Downloading Python 3.11..."
        inetc::get /CAPTION "Downloading Python 3.11" \
            "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" \
            "$TEMP\python_installer.exe" /END
        Pop $0
        ${If} $0 == "OK"
            ExecWait '"$TEMP\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1'
        ${Else}
            MessageBox MB_OK "Could not download Python. Install manually from python.org"
        ${EndIf}
    ${EndIf}
SectionEnd

Section "-Pip Packages"
    ${If} $InstallPip == ${BST_CHECKED}
        DetailPrint "Installing Python packages (this may take a few minutes)..."
        nsExec::ExecToLog 'pip install flask llama-cpp-python'
    ${EndIf}
SectionEnd

Section "-Desktop Shortcut"
    ${If} $CreateShortcut == ${BST_CHECKED}
        CreateShortcut "$DESKTOP\${APP_NAME}.lnk" \
            "$INSTDIR\launch.bat" "" "$INSTDIR\assets\icon.ico"
        ; Also create Model Downloader shortcut
        CreateShortcut "$DESKTOP\AI Assistant Setup.lnk" \
            "pythonw.exe" '"$INSTDIR\scripts\model_downloader.py"' \
            "$INSTDIR\assets\icon.ico"
    ${EndIf}
SectionEnd

Section "-Start on Boot"
    ${If} $StartOnBoot == ${BST_CHECKED}
        WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" \
            "AIAssistant" '"$INSTDIR\launch.bat"'
    ${EndIf}
SectionEnd

Section "-Run Model Downloader"
    ${If} $RunSetupAfter == ${BST_CHECKED}
        Exec '"pythonw.exe" "$INSTDIR\scripts\model_downloader.py"'
    ${EndIf}
SectionEnd

; ── Uninstall ─────────────────────────────────────────────────────────────────
Section "Uninstall"
    RMDir /r "$INSTDIR\backend"
    RMDir /r "$INSTDIR\scripts"
    RMDir /r "$INSTDIR\models_list"
    Delete   "$INSTDIR\launch.bat"
    Delete   "$INSTDIR\assistant.db"
    Delete   "$INSTDIR\launch_config.txt"
    Delete   "$INSTDIR\${UNINSTALLER}"
    RMDir    "$INSTDIR"

    ; Remove shortcuts
    Delete "$DESKTOP\${APP_NAME}.lnk"
    Delete "$DESKTOP\AI Assistant Setup.lnk"

    ; Remove registry
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIAssistant"
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "AIAssistant"

    MessageBox MB_YESNO "Delete downloaded models? (This will free up disk space)" IDNO skip_models
        RMDir /r "$INSTDIR\models"
    skip_models:
SectionEnd
