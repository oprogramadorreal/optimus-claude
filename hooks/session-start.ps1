# Native Windows entry point for Codex. Launch Bash directly: Git shell aliases
# change cwd, and mixing Git's bundled shell with another Bash can lose env vars.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = [Console]::OutputEncoding

function Find-NativeBash {
    if ($env:CLAUDE_CODE_GIT_BASH_PATH) {
        if (-not (Test-Path -LiteralPath $env:CLAUDE_CODE_GIT_BASH_PATH -PathType Leaf)) {
            throw 'CLAUDE_CODE_GIT_BASH_PATH does not point to a Bash executable.'
        }
        return $env:CLAUDE_CODE_GIT_BASH_PATH
    }

    # Inspect paths without running Git: a broken repository config must not
    # prevent startup, and a minimal Git installation may contain no Bash.
    foreach ($git in @(Get-Command git.exe -All -CommandType Application -ErrorAction SilentlyContinue)) {
        $gitDir = Split-Path -Parent $git.Source
        foreach ($relative in @('../bin/bash.exe', '../usr/bin/bash.exe', '../../bin/bash.exe', '../../usr/bin/bash.exe')) {
            $candidate = [IO.Path]::GetFullPath((Join-Path $gitDir $relative))
            if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                return $candidate
            }
        }
    }

    # System32's bash.exe is a WSL launcher, not an interpreter for native paths.
    foreach ($bash in @(Get-Command bash.exe -All -CommandType Application -ErrorAction SilentlyContinue)) {
        if ($bash.Source -notmatch '\\Windows\\(?:System32|SysWOW64|Sysnative)\\') {
            return $bash.Source
        }
    }

    foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, "$env:LOCALAPPDATA/Programs")) {
        if ($base) {
            $candidate = Join-Path $base 'Git/bin/bash.exe'
            if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                return $candidate
            }
        }
    }
    throw 'Optimus needs native Bash. Install Git for Windows or set CLAUDE_CODE_GIT_BASH_PATH to bash.exe.'
}

$bashPath = Find-NativeBash
$bashDir = Split-Path -Parent $bashPath
$bashRoot = Split-Path -Parent $bashDir
if ((Split-Path -Leaf $bashRoot) -eq 'usr') {
    $bashRoot = Split-Path -Parent $bashRoot
}
# Use utilities from the selected Bash installation, including find rather than
# Windows find.exe. Keep the caller's PATH afterward for project tools.
$toolPaths = @(
    (Join-Path $bashRoot 'usr/bin')
    (Join-Path $bashRoot 'bin')
    (Join-Path $bashRoot 'cmd')
) | Where-Object { Test-Path -LiteralPath $_ -PathType Container }
$env:PATH = (@($toolPaths) + @($env:PATH)) -join [IO.Path]::PathSeparator

$scriptPath = (Join-Path $PSScriptRoot 'session-start').Replace('\', '/')
& $bashPath $scriptPath
exit $LASTEXITCODE
