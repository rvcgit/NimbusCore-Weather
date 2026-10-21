' Create WScript Shell object
Dim shell
Set shell = CreateObject("WScript.Shell")

' Run the batch file hidden, without waiting
shell.Run "cmd.exe /c ""C:\apps\weather_fetcher.bat""", 0, False

' Clean up
Set shell = Nothing
