# Install or update Codex Studio in the current project.
& {
    $ErrorActionPreference = 'Stop'
    $studioProject = (Get-Location).ProviderPath

    # WSL checkouts must use Linux file locks, even when invoked from PowerShell.
    if ($studioProject -match '^\\\\(?:wsl\.localhost|wsl\$)\\([^\\]+)(\\.*)?$') {
        $studioDistribution = $Matches[1]
        $studioLinuxProject = if ($Matches[2]) { $Matches[2].Replace('\', '/') } else { '/' }
        & wsl.exe --distribution $studioDistribution --cd $studioLinuxProject -- bash -o pipefail -c 'curl -fsSL https://raw.githubusercontent.com/deepdivekr/codex-studio/main/install.sh | bash'
        if ($LASTEXITCODE -ne 0) { throw 'Codex Studio installation in WSL failed.' }
        return
    }

    $studioPython = $null
    $studioPythonArgs = @()
    foreach ($studioCandidate in @('py', 'python3', 'python')) {
        $studioCommand = Get-Command $studioCandidate -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $studioCommand) { continue }
        $studioCandidateArgs = @()
        if ($studioCandidate -eq 'py') { $studioCandidateArgs = @('-3') }
        & $studioCommand.Source @studioCandidateArgs -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' *> $null
        if ($LASTEXITCODE -eq 0) {
            $studioPython = $studioCommand.Source
            $studioPythonArgs = @($studioCandidateArgs)
            break
        }
    }
    if (-not $studioPython) { throw 'Codex Studio needs Python 3.10 or newer. Install Python, then run this command again.' }

    $studioTemp = Join-Path ([IO.Path]::GetTempPath()) ('codex-studio-install-' + [guid]::NewGuid().ToString('N'))
    $studioBootstrap = Join-Path $studioTemp 'install.py'
    try {
        New-Item -ItemType Directory -Path $studioTemp | Out-Null
        Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/deepdivekr/codex-studio/main/install.py' -OutFile $studioBootstrap
        & $studioPython @studioPythonArgs -X utf8 $studioBootstrap --project $studioProject
        if ($LASTEXITCODE -ne 0) { throw 'Codex Studio installation failed.' }
    }
    finally {
        if (Test-Path -LiteralPath $studioBootstrap) { Remove-Item -LiteralPath $studioBootstrap -Force }
        if (Test-Path -LiteralPath $studioTemp) { [IO.Directory]::Delete($studioTemp) }
    }
}
