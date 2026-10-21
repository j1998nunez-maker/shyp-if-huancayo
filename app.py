Get-Clipboard | Set-Content -Path ".\app.py" -Encoding UTF8
git status
git add app.py
git commit -m "feat: filtro por departamentos, diferenciador geomorfologico cerro vs ciudad y validacion retrospectiva por fechas"
git push origin main
