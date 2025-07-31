@echo off
setlocal

:: =========================================
:: Clean a file by removing non-ASCII characters
:: Usage: clean-text.bat filename.txt
:: =========================================
:: (Get-Content clean-text.bat) -replace '[^\x20-\x7E]', '' | Set-Content clean-text.bat
:: Validate input
if "%~1"=="" (
    echo Usage: clean-text.bat [filename]
    exit /b 1
)

:: Set input and output files
set "INPUT_FILE=%~1"
set "OUTPUT_FILE=cleaned_%~nx1"

:: Check that file exists
if not exist "%INPUT_FILE%" (
    echo ERROR: File not found: "%INPUT_FILE%"
    exit /b 1
)

echo Cleaning "%INPUT_FILE%"...

:: Run PowerShell script block to filter out weird characters
powershell -ExecutionPolicy Bypass -NoProfile -Command "$content = Get-Content -Path '%INPUT_FILE%' -Raw -Encoding UTF8; $cleaned = ($content -replace '[^\u0020-\u007E]', ''); Set-Content -Path '%OUTPUT_FILE%' -Value $cleaned -Encoding ASCII"

:: Confirm output
if exist "%OUTPUT_FILE%" (
    echo  Done! Cleaned file saved as "%OUTPUT_FILE%"
) else (
    echo  Something went wrong during cleaning.
)

endlocal
