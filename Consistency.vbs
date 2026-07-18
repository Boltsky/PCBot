Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\Public\PCBot"
WshShell.Run "cmd /c ""py -3 run_pcbot.py""", 0, False
Set WshShell = Nothing