@echo off
REM Daily incremental collection of iPhone Duo community posts/comments (registered in Windows Task Scheduler).
REM New units of the day -> data\community_kr\daily\YYYY-MM-DD_new_units.json ; log -> data\community_kr\logs\
cd /d C:\Users\cehha\ai-data-bootcamp\Pjt4
if not exist data\community_kr\logs mkdir data\community_kr\logs
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set TODAY=%%i
set PYTHONIOENCODING=utf-8
C:\Users\cehha\anaconda3\python.exe -u code\collect_kr_community.py daily >> data\community_kr\logs\daily_%TODAY%.log 2>&1
