$script = Split-Path -Parent $MyInvocation.MyCommand.Path
$ps1 = "$script\launch_atem.ps1"

$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$Desktop\ATEM Controller.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ps1`""
$Shortcut.Description = "ATEM Mini Controller"
$Shortcut.WorkingDirectory = $script
$Shortcut.Save()
Write-Host "바로가기 생성 완료: $Desktop\ATEM Controller.lnk"
