@echo off
title OmniDropShop - AliExpress & Temu Dropshipping Website
echo ========================================================
echo Starting OmniDropShop Website...
echo ========================================================
python -m pip install flask requests
echo.
echo Website is starting at http://localhost:5000
echo Open your browser and go to http://localhost:5000
echo.
python app.py
pause
