@echo off
REM ============================================================================
REM  build_windows.bat  --  PayrollPro v2.0
REM  Compiles payroll.asm into payroll.dll using NASM + MinGW gcc.
REM ============================================================================

cd /d "%~dp0"

echo.
echo === [1/3] Assembling payroll.asm with NASM (Win64) ===
nasm -f win64 payroll.asm -o payroll.obj
if errorlevel 1 goto :error

echo.
echo === [2/3] Linking with gcc into ..\lib\payroll.dll ===
gcc -shared -o ..\lib\payroll.dll payroll.obj -Wl,--out-implib,..\lib\payroll.lib
if errorlevel 1 goto :error

echo.
echo === [3/3] Cleaning up object file ===
del payroll.obj

echo.
echo ============================================================
echo  BUILD SUCCESSFUL
echo  Output:  ..\lib\payroll.dll
echo ============================================================
goto :eof

:error
echo.
echo ============================================================
echo  BUILD FAILED
echo  Check that NASM and gcc are on PATH.
echo  Open a NEW Command Prompt after installing them.
echo ============================================================
exit /b 1
