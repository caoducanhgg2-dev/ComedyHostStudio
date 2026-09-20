[Setup]
AppId={{68F0C1C1-17CB-4CED-8261-5C18EB92571A}
AppName=SRT Voice Studio
AppVersion=1.7.2
VersionInfoVersion=1.7.2.0
AppPublisher=SRT Voice Studio
DefaultDirName={localappdata}\Programs\SRTVoiceStudio
DefaultGroupName=SRT Voice Studio
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=installer-output
OutputBaseFilename=SRTVoiceStudio_Setup_1.7.2
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=SRT Voice Studio
UninstallDisplayIcon={app}\SRTVoiceStudio.exe
CloseApplications=yes
SetupLogging=yes

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "dist\SRTVoiceStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SRT Voice Studio"; Filename: "{app}\SRTVoiceStudio.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\SRT Voice Studio"; Filename: "{app}\SRTVoiceStudio.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\SRTVoiceStudio.exe"; Description: "Launch SRT Voice Studio"; Flags: nowait postinstall skipifsilent
