Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

WshShell.Run "cmd /c ""py -3 run_pcbot.py""", 0, False

Set FSO = Nothing
Set WshShell = Nothing
