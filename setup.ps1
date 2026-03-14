# ATEM Controller - 설치 스크립트
# atem.exe 와 같은 폴더에 두고 실행하세요

$name    = "ATEMController"
$exePath = Join-Path $PSScriptRoot "atem.exe"
$url     = "http://192.168.10.2:8000/"
$w = 620; $h = 419

if (-not (Test-Path $exePath)) {
    Write-Host "[오류] atem.exe 를 찾을 수 없습니다: $exePath"
    pause; exit 1
}

# ── 1. 작업 스케줄러 등록 ──────────────────────────
Write-Host "[1/2] 작업 스케줄러 등록 중..."
schtasks /delete /tn $name /f 2>$null | Out-Null
$result = schtasks /create /tn $name /tr "`"$exePath`"" /sc ONLOGON /rl LIMITED /f 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "      완료: 로그인 시 자동실행"
    schtasks /run /tn $name 2>$null | Out-Null
    Write-Host "      완료: 작업 즉시 실행"
} else {
    Write-Host "      [경고] 작업 스케줄러 등록 실패: $result"
}

# ── 2. 바탕화면 + 시작프로그램 Edge 바로가기 생성 ──────
Write-Host "[2/2] 바로가기 생성 중..."

# 런처 스크립트 작성 (화면 크기 동적 계산)
$launcherPath = Join-Path $PSScriptRoot "launch_atem.ps1"
@"
Add-Type -AssemblyName System.Windows.Forms
`$screen = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
`$x = 0
`$y = `$screen.Height - $h
`$profile = "`$env:LOCALAPPDATA\ATEMControllerEdge"
`$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
Start-Process `$edge "--app=$url --window-size=$w,$h --window-position=`$x,`$y --user-data-dir=``"`$profile``""
"@ | Set-Content $launcherPath -Encoding UTF8

$WshShell = New-Object -ComObject WScript.Shell

# 바탕화면
$Desktop = [System.Environment]::GetFolderPath("Desktop")
$lnk = $WshShell.CreateShortcut("$Desktop\ATEM Controller.lnk")
$lnk.TargetPath       = "powershell.exe"
$lnk.Arguments        = "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcherPath`""
$lnk.Description      = "ATEM Mini Controller"
$lnk.WorkingDirectory = $PSScriptRoot
$lnk.Save()
Write-Host "      완료: 바탕화면에 'ATEM Controller' 생성"

# 시작 프로그램 폴더
$Startup = [System.Environment]::GetFolderPath("Startup")
$lnk2 = $WshShell.CreateShortcut("$Startup\ATEM Controller.lnk")
$lnk2.TargetPath       = "powershell.exe"
$lnk2.Arguments        = "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcherPath`""
$lnk2.Description      = "ATEM Mini Controller"
$lnk2.WorkingDirectory = $PSScriptRoot
$lnk2.Save()
Write-Host "      완료: 시작 프로그램에 'ATEM Controller' 등록"

Write-Host ""
Write-Host "설치 완료."
pause
