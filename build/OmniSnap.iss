; build/OmniSnap.iss
; OmniSnap — Installateur Windows
; Prérequis : Inno Setup 6 (https://jrsoftware.org/isinfo.php)
; Build : ouvrir ce fichier dans Inno Setup Compiler -> Build

#define MyAppName "OmniSnap"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "JeffDok Média"
#define MyAppURL "https://github.com/Jeff-Dok/omnisnap"
#define MyAppExeName "OmniSnap.exe"

[Setup]
AppId={{A7F3C2D1-4E8B-4F9A-B2C3-D4E5F6A7B8C9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE.txt
OutputDir=installer
OutputBaseFilename=OmniSnap_Setup_{#MyAppVersion}
SetupIconFile=..\assets\omnisnap.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
MinVersion=10.0
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[CustomMessages]
english.InstallingChromium=Installing browser engine (Playwright Chromium, ~300 MB — internet required)...
french.InstallingChromium=Installation du moteur de navigation (Playwright Chromium, ~300 Mo — internet requis)...

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--install-chromium"; StatusMsg: "{cm:InstallingChromium}"; Flags: waituntilterminated runhidden
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
