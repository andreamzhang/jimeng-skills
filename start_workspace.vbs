' 一键启动工作台：后台启动本地服务，等服务就绪后打开浏览器
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
Set http = CreateObject("MSXML2.XMLHTTP")

rootPath = fso.GetParentFolderName(WScript.ScriptFullName)

pyExe = "python"
pyPathFile = rootPath & "\tools\python-path.txt"
If fso.FileExists(pyPathFile) Then
  Set ts = fso.OpenTextFile(pyPathFile, 1)
  If Not ts.AtEndOfStream Then
    cand = Trim(ts.ReadLine)
    If Len(cand) > 2 And fso.FileExists(cand) Then pyExe = cand
  End If
  ts.Close
End If

scriptPath = rootPath & "\tools\serve_workspace.py"
sh.Run """" & pyExe & """ """ & scriptPath & """ 8731", 0, False

url = "http://127.0.0.1:8731/工作台.html"
For i = 1 To 40
  WScript.Sleep 250
  On Error Resume Next
  http.open "GET", url & "?ping=" & i, False
  http.send
  ok = (Err.Number = 0)
  Err.Clear
  On Error GoTo 0
  If ok Then Exit For
Next
sh.Run "explorer.exe """ & url & """"