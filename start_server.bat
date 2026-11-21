@echo off
title FoodBridge AI - Dev Server
echo.
echo ============================================
echo   FoodBridge AI - Starting Development Server
echo ============================================
echo.
cd /d "%~dp0"
echo [INFO] Running database migrations...
venv\Scripts\python.exe manage.py migrate
echo.
echo [INFO] Starting Django server on http://127.0.0.1:8000
echo [INFO] Press CTRL+C to stop the server.
echo.
echo [ACCOUNTS - All passwords: Pass@1234]
echo   Admin:      username=admin
echo   Donor:      donor_demo / donor1
echo   NGO:        ngo_demo / ngo1
echo   Volunteer:  volunteer_demo / volunteer1
echo.
echo [NOTES]
echo   - OTP emails print to this console (not real email)
echo   - Admin panel: http://127.0.0.1:8000/admin/
echo   - App:         http://127.0.0.1:8000/
echo.
venv\Scripts\python.exe manage.py runserver 8000
pause
