@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0start-mqtt-proxy.ps1" %*
