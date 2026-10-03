; ==============================================================================
; Vihara - Production Inno Setup 6 Packaging Configuration
; Builds: Vihara-Setup-x64.exe (Zero UAC Elevation, Per-User Distribution)
; ==============================================================================

#define MyAppName "Vihara"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Vihara Team"
#define MyAppURL "https://vihara.com"
#define MyAppExeName "vihara.exe"

[Setup]
AppId={{9F82A4C2-43E1-499D-B44E-294F923D4E72}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/support
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Programs\Vihara
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=Vihara-Setup-x64
OutputDir=..\..\dist\installers
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
SetupIconFile=..\icons\app_icon.ico
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=force
RestartApplications=no
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupentry"; Description: "Launch Vihara automatically when Windows starts"; GroupDescription: "System Integration:"

[Files]
; Primary application payload (PyInstaller onedir distribution)
Source: "..\..\dist\vihara\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcut
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
; Optional Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Auto-start on Windows user login (stored in HKCU, requires zero administrative privileges)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Vihara"; ValueData: """{app}\{#MyAppExeName}"" --silent"; Flags: uninsdeletevalue; Tasks: startupentry

; Register .lucidpack file association for one-click theme & meme pack installation
Root: HKCU; Subkey: "Software\Classes\.lucidpack"; ValueType: string; ValueName: ""; ValueData: "Vihara.Pack"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Vihara.Pack"; ValueType: string; ValueName: ""; ValueData: "Vihara Theme & Meme Pack"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Vihara.Pack\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\Vihara.Pack\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" --install-pack ""%1"""

[Run]
; Launch immediately into system tray after installation without admin elevation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
