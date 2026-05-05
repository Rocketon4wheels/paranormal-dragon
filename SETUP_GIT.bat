@echo off
cd /d "%~dp0"
git init
git remote remove origin 2>nul
git remote add origin https://github.com/Rocketon4wheels/paranormal-dragon.git
git fetch origin
git branch -M main
git add -A
git commit -m "initial setup"
git push -u origin main --force
echo.
echo Git is connected. Use DEPLOY.bat from now on.
pause
