' Bu VBScript dosyasi, siyah terminal penceresi gorunmeden bat dosyasini arka planda calistirir.
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Debug log dosyasi olustur
strPath = fso.GetParentFolderName(WScript.ScriptFullName)
logPath = fso.BuildPath(strPath, "vbs_debug.log")
Set logFile = fso.OpenTextFile(logPath, 8, True) ' 8 = ForAppending

logFile.WriteLine "--- " & Now & " ---"
logFile.WriteLine "Script Full Name: " & WScript.ScriptFullName
logFile.WriteLine "Parent Path: " & strPath

batPath = fso.BuildPath(strPath, "run_auto.bat")
logFile.WriteLine "Target Bat Path: " & batPath

If fso.FileExists(batPath) Then
    logFile.WriteLine "Success: run_auto.bat found. Launching..."
    ' Batch dosyasini gizli calistir
    WshShell.Run chr(34) & batPath & Chr(34), 0
Else
    logFile.WriteLine "CRITICAL ERROR: run_auto.bat NOT FOUND at " & batPath
End If

logFile.Close
Set WshShell = Nothing
Set fso = Nothing
