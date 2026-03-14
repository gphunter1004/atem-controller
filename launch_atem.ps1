Add-Type -AssemblyName System.Windows.Forms
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
$w = 620; $h = 419
$x = 0
$y = $screen.Height - $h

$profile = "$env:LOCALAPPDATA\ATEMControllerEdge"
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$url  = "http://192.168.10.2:8000/"

Start-Process $edge "--app=$url --window-size=$w,$h --window-position=$x,$y --user-data-dir=`"$profile`""
