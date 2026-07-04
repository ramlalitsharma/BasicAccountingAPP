; Accounting Pro v2.8.0 Installer
; Requires Inno Setup 6.2+ (https://jrsoftware.org/isdl.php)

#define MyAppName "Accounting Pro"
#define MyAppVersion "2.8.0"
#define MyAppPublisher "Accounting Pro"
#define MyAppURL "https://github.com/ramlalitsharma/BasicAccountingAPP"
#define MyAppExeName "AccountingPro.exe"
#define MyAppIcon "..\icon\accounting_pro.ico"
#define VC_REDIST_URL "https://aka.ms/vs/17/release/vc_redist.x64.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=AccountingPro_Setup_v{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
DisableWelcomePage=no
ShowLanguageDialog=no
UninstallDisplayIcon={app}\{#MyAppExeName}
ChangesAssociations=yes
SetupIconFile={#MyAppIcon}
LicenseFile=..\LICENSE.txt
InfoBeforeFile=..\README.txt
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
VersionInfoTextVersion={#MyAppVersion}
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\icon\accounting_pro.ico"; DestDir: "{app}\icon"; Flags: ignoreversion

[Dirs]
Name: "{app}\data"; Permissions: users-modify
Name: "{app}\backups"; Permissions: users-modify
Name: "{app}\logs"; Permissions: users-modify
Name: "{app}\config"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\icon\accounting_pro.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon; IconFilename: "{app}\icon\accounting_pro.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function VC_RedistInstalled: Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\VisualStudio\VC\Runtimes\x64', 'Version', Version);
  if not Result then
    Result := RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\VisualStudio\VC\Runtimes\x64', 'Version', Version);
end;

procedure DownloadAndInstallVCRedist;
var
  TmpFile: String;
  ResultCode: Integer;
begin
  TmpFile := ExpandConstant('{tmp}\vc_redist.x64.exe');
  Log('Downloading Visual C++ Redistributable...');

  if Exec('powershell.exe',
    '-ExecutionPolicy Bypass -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ' +
    '$wc = New-Object Net.WebClient; ' +
    '$wc.DownloadFile(''https://aka.ms/vs/17/release/vc_redist.x64.exe'', ''' + TmpFile + '''); ' +
    'exit 0 } catch { exit 1 }"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) then
  begin
    if Exec(TmpFile, '/install /quiet /norestart', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      Log('VC++ Redistributable installed successfully (code: ' + IntToStr(ResultCode) + ')')
    else
      Log('VC++ Redistributable install failed with code: ' + IntToStr(ResultCode));
  end
  else
    Log('VC++ Redistributable download failed');
end;

function InitializeSetup: Boolean;
var
  ResultCode: Integer;
begin
  Result := True;

  // Kill any running AccountingPro instances silently
  Exec('taskkill.exe', '/f /im AccountingPro.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  if not VC_RedistInstalled then
  begin
    Log('VC++ Redistributable not found, installing silently...');
    DownloadAndInstallVCRedist;
  end
  else
  begin
    Log('VC++ Redistributable already installed, skipping');
  end;
end;