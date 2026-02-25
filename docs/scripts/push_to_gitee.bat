@echo off
REM 推送到Gitee

cd /d %~dp0..

echo 正在推送到Gitee...
git push -u gitee master

pause
