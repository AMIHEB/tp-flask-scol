@echo off
cd /d "%~dp0"
if not exist monvenv (
    echo Creation de l'environnement virtuel...
    python -m venv monvenv
)
call monvenv\Scripts\activate
pip install -r requirements.txt
echo.
echo Ouvre http://127.0.0.1:5000 dans le navigateur
python app.py
pause
