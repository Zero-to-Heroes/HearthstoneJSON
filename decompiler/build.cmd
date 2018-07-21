@ECHO OFF

set "BASE_DIR=%~dp0"
set "ILSPY_DIR=%BASE_DIR%\ILSpy"
set "BUILD_DIR=%BASE_DIR%\build"

set "CSPROJ=%ILSPY_DIR%\ICSharpCode.Decompiler\ICSharpCode.Decompiler.csproj"
set "LIBS=Mono.Cecil.dll,ICSharpCode.Decompiler.dll,ICSharpCode.NRefactory.dll,ICSharpCode.NRefactory.CSharp.dll"
set "SOURCES=%BASE_DIR%\decompile.cs"

WHERE msbuild 1>nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo MSBuild wasn't found. Run this file from a developer prompt!
    exit /B 5
)

WHERE git 1>nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Git wasn't found on your PATH. Add the Git binaries to your PATH!
    exit /B 6
)

pushd "%BASE_DIR%"
git submodule update --init
popd

pushd "%ILSPY_DIR%"
git submodule update --init
git reset --hard
git apply "%BASE_DIR%\short-circuit.patch"
popd

msbuild "%CSPROJ%"
msbuild /property:OutputPath="%BUILD_DIR%" "%CSPROJ%"

set "REFS="
for %%G IN (%LIBS%) DO (
    call set "REFS=/r:"%%BUILD_DIR%%\%%G" %%REFS%%"
)
echo Referenced libs: %REFS%

csc /debug /out:"%BUILD_DIR%\decompile.exe" %REFS% "%SOURCES%"

