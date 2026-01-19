@echo off
powershell.exe -NoProfile -Command "& { param($args) Start-Process powershell.exe -ArgumentList (@('-ExecutionPolicy', 'Bypass', '-File', '%~dp0BuildSourceIndex.ps1') + $args) -Verb RunAs -Wait }" %*
