@echo off
title TickTask Serverless Keep-Alive ^& Automated Reminder Daemon
color 0A
echo ====================================================================
echo    TICKTASK SERVERLESS KEEP-ALIVE ^& AUTOMATED REMINDER DAEMON
echo ====================================================================
echo Starting 24/7 pinger for TickTask Vercel Portal...
echo Target: https://ticktask-silk.vercel.app/api/keep-alive
echo.
python keep_alive_app.py --url https://ticktask-silk.vercel.app/api/keep-alive --interval 60
pause
