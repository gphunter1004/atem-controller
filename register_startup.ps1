# ATEM Controller - 자동실행 등록
# atem.exe 와 같은 폴더에 두고 실행하세요

$name    = "ATEMController"
$exePath = Join-Path $PSScriptRoot "atem.exe"
$regKey  = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"

if (-not (Test-Path $exePath)) {
    Write-Host "[오류] atem.exe 를 찾을 수 없습니다: $exePath"
    pause
    exit 1
}

Set-ItemProperty -Path $regKey -Name $name -Value $exePath
Write-Host "등록 완료: $exePath"
Write-Host "다음 로그인부터 자동실행됩니다."
pause
