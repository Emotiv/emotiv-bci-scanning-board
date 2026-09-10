; Inno Setup script for the EMOTIV Scanning Board (Windows).
;
; Wraps the PyInstaller onedir output into a single setup.exe. Onedir rather
; than onefile on purpose: a onefile build of a PyQt6 app unpacks itself to
; %TEMP% on every launch, which costs ten seconds or more of cold start. For an
; assistive communication tool that someone may need in a hurry, installing the
; folder once and starting in a couple of seconds is the right trade.
;
; Built by .github/workflows/build.yml after PyInstaller runs. To build by hand
; from the repository root:
;     pyinstaller packaging/BCIScanningBoard.spec --noconfirm
;     iscc packaging/BCIScanningBoard.iss

#define AppName "EMOTIV Scanning Board"
#define AppPublisher "EMOTIV"
#define AppExe "EMOTIV Scanning Board.exe"
#define AppURL "https://github.com/Emotiv/BCIScanningBoard"

; Overridden by the workflow with /DAppVersion=<tag>; 0.0.0 marks a local build.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

; No source artwork is checked in yet, so the wizard icon is optional. Drop
; app_icon.ico next to this file and it is used automatically.
#define IconFile "app_icon.ico"

[Setup]
AppId={{D78334C2-F0CE-4EFC-A1E6-FF822CAE98A7}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Per-user install by default, so no UAC prompt and no admin rights needed --
; this gets handed to people on machines they may not administer.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..
OutputBaseFilename=EMOTIV-Scanning-Board-windows-x64-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
#if FileExists(AddBackslash(SourcePath) + IconFile)
SetupIconFile={#IconFile}
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; The whole PyInstaller output folder: the exe plus _internal and its DLLs.
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; \
    Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Credentials and the caregiver's phrase list live in
; %APPDATA%\EmotivScanningBoard and are deliberately left behind -- a reinstall
; should not wipe a phrase list somebody spent an afternoon building. Only what
; the installer itself created is removed.
Type: filesandordirs; Name: "{app}\_internal"
