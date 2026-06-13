@echo off
chcp 65001 > nul
set "TASK_NAME=OtoAI Zenginlestirmes"
set "CMD_RUN=wscript.exe \"C:\Users\faruk\OneDrive\Masaüstü\otoAi\run_hidden.vbs\""
schtasks /change /tn "%TASK_NAME%" /tr "%CMD_RUN%"
if %errorlevel% neq 0 (
    echo FAILED to update %TASK_NAME%!
) else (
    echo SUCCESS updating %TASK_NAME%
)

set "TASK_NAME2=OtoAI Zenginlestirme"
schtasks /change /tn "%TASK_NAME2%" /tr "%CMD_RUN%"
if %errorlevel% neq 0 (
    echo FAILED to update %TASK_NAME2%!
) else (
    echo SUCCESS updating %TASK_NAME2%
)
pause
