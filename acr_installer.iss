; ACR Telemetry Studio installer script (Inno Setup 6).
; Build (from this directory):
;   ISCC.exe acr_installer.iss              -> dist\ACR Telemetry Setup <version>.exe
;   ISCC.exe /O<outdir> acr_installer.iss   -> installer in <outdir>
; The app is a single-file exe whose data directory is "<install dir>\telemetry",
; so it is installed per-user (no UAC) into %LOCALAPPDATA%\Programs\ACR Telemetry.

#ifndef MyAppVersion
  #define MyAppVersion "0.3.16"
#endif

#define MyAppName "ACR Telemetry Studio"
#define MyAppExeName "ACR Telemetry.exe"
#define MyAppPublisher "ACRallyRec"

[Setup]
AppId={{A0EE3B1C-5A4B-4C5F-9C1E-AC0000000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\ACR Telemetry
DefaultGroupName=ACR Telemetry
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=ACR Telemetry Setup {#MyAppVersion}
SetupIconFile=assets/acr.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "{#SourcePath}\installer\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\ACR Telemetry.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\telemetry"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
