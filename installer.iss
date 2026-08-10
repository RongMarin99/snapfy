; Snapfy Downloader Pro - Inno Setup Script
; Compile with: ISCC.exe installer.iss /DMyAppVersion=1.3.32
; (build_exe.ps1 does this for you automatically, reading the version from app/core/version.py)

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

#define MyAppName "Snapfy Downloader Pro"
#define MyAppExeName "Snapfy.exe"
#define MyAppPublisher "Snapfy"
#define MyAppURL "https://github.com/RongMarin99/snapfy"

[Setup]
AppId={{B3F6C8A0-6D5E-4C7B-9A1F-6E6E9C4A0F01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
SetupIconFile=logo.ico
DefaultDirName={autopf}\Snapfy Downloader Pro
DefaultGroupName=Snapfy Downloader Pro
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=Snapfy-Setup-v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
; Restart Manager: if Snapfy.exe is still running when the silent updater
; launches this installer, Inno Setup will close it automatically and
; relaunch it after install completes - no manual "please close the app" step.
CloseApplications=yes
RestartApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

; PyInstaller onedir output (dist\Snapfy\*) gets copied wholesale into the install dir.
[Files]
Source: "dist\Snapfy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Snapfy Downloader Pro"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,Snapfy Downloader Pro}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Snapfy Downloader Pro"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,Snapfy Downloader Pro}"; Flags: nowait postinstall skipifsilent

[Code]
// build_exe.ps1 hardlinks python3.dll -> python313.dll in dist\Snapfy to fix a
// duplicate-CPython-runtime access violation (0xC0000005) some build machines
// hit (see comment in build_exe.ps1). A plain file copy - which is all the
// [Files] section above does - does NOT preserve that hardlink; it silently
// re-duplicates the DLL into two independent files, bringing the crash back
// for every installed user. Redo the hardlink here, after install, in place.
procedure FixPython3DllHardlink();
var
  ResultCode: Integer;
  python3Dll, python313Dll: String;
begin
  python3Dll := ExpandConstant('{app}\_internal\python3.dll');
  python313Dll := ExpandConstant('{app}\_internal\python313.dll');
  if FileExists(python3Dll) and FileExists(python313Dll) then
  begin
    DeleteFile(python3Dll);
    Exec('fsutil.exe', 'hardlink create "' + python3Dll + '" "' + python313Dll + '"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    FixPython3DllHardlink();
end;
