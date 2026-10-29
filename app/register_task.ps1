# Registers a Windows scheduled task that runs the live logger every 30 minutes
# (HH:27 and HH:57, shortly after the routine LTAC METARs at HH:20/HH:50).
# Usage (PowerShell, as the current user):  .\app\register_task.ps1
# Remove again with:  Unregister-ScheduledTask -TaskName "Esenboga Fog Live Logger" -Confirm:$false
$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $PSScriptRoot
$py = "$env:USERPROFILE\.venvs\esenboga\Scripts\pythonw.exe"   # windowless interpreter
if (-not (Test-Path $py)) { throw "Python not found at $py - adjust the path to your environment." }

$action = New-ScheduledTaskAction -Execute $py -WorkingDirectory $proj `
    -Argument '"app\live_log.py" --once --logfile "logs\live_logger.log"'
$now = Get-Date
$start = $now.Date.AddHours($now.Hour).AddMinutes(27)
while ($start -le $now.AddMinutes(1)) { $start = $start.AddMinutes(30) }
$trigger = New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval (New-TimeSpan -Minutes 30)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "Esenboga Fog Live Logger" -Action $action -Trigger $trigger -Settings $settings `
    -Description "Fetches the latest LTAC METARs every 30 min, logs calibrated fog nowcasts and verifies earlier ones." -Force
Get-ScheduledTaskInfo -TaskName "Esenboga Fog Live Logger" | Select-Object NextRunTime
