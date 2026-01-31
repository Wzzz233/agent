@echo off
REM Keysight ADS2025 专用 Python 环境启动脚本
REM 用途：确保在纯净的ADS环境中运行Python脚本，避免系统Python环境冲突

REM === 1. 设置ADS环境变量 ===
set "ADS_ROOT=C:\Program Files\Keysight\ADS2025"
set "ADS_BIN=%ADS_ROOT%\bin"
set "ADS_LIB=%ADS_ROOT%\lib\win32_64"

REM === 2. 保存当前环境变量 (以便后续恢复) ===
set "ORIGINAL_PATH=%PATH%"
set "ORIGINAL_PYTHONPATH=%PYTHONPATH%"
set "ORIGINAL_PYTHONHOME=%PYTHONHOME%"

REM === 3. 设置纯净的ADS环境 ===
set "PATH=%ADS_BIN%;%ADS_LIB%;%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem"
set "PYTHONPATH="
set "PYTHONHOME="

REM === 4. 验证ADS可执行文件存在 ===
if not exist "%ADS_BIN%\hpeesofde.exe" (
    echo 错误: 未找到ADS可执行文件: %ADS_BIN%\hpeesofde.exe
    echo 请检查ADS安装路径
    goto restore_and_exit
)

REM === 5. 检查是否提供了Python脚本参数 ===
if "%~1"=="" (
    echo 错误: 未指定Python脚本
    echo 用法: %0 ^<python_script.py^>
    goto restore_and_exit
)

REM === 6. 检查Python脚本是否存在 ===
if not exist "%~1" (
    echo 错误: Python脚本不存在: %1
    goto restore_and_exit
)

REM === 7. 运行ADS Python脚本 ===
echo 运行ADS Python脚本: %1
echo ADS环境: %ADS_ROOT%
"%ADS_BIN%\hpeesofde.exe" -batch -python "%~1"
set ADS_EXIT_CODE=%ERRORLEVEL%

REM === 8. 输出执行结果 ===
if %ADS_EXIT_CODE% EQU 0 (
    echo ADS脚本执行成功
) else (
    echo ADS脚本执行失败，退出代码: %ADS_EXIT_CODE%
)

:restore_and_exit
REM === 9. 恢复原始环境变量 ===
set "PATH=%ORIGINAL_PATH%"
set "PYTHONPATH=%ORIGINAL_PYTHONPATH%"
set "PYTHONHOME=%ORIGINAL_PYTHONHOME%"

REM === 10. 结束 ===
exit /b %ADS_EXIT_CODE%