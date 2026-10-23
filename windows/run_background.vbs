' VBScript เพื่อรัน line-report ใน Background แบบซ่อนหน้าต่าง CMD ดำๆ
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
AppDir = FSO.GetParentFolderName(ScriptDir) & "\line-report\app"

' รัน python main.py โดยหน้าต่างซ่อนอยู่เบื้องหลัง (0 = Hidden)
WshShell.CurrentDirectory = AppDir
WshShell.Run "python main.py", 0, False
