# install.ps1
# Tektronix MCP Server Installer
# Copies server files to AppData\Local and updates claude_desktop_config.json

$ErrorActionPreference = "Stop"

# Version - must match build.bat
$VERSION   = "1.4.5"
$DIST_NAME = "TektronixMCP_v$VERSION"

# Paths - install to AppData\Local (no admin rights needed, consistent on all PCs)
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallRoot = "$env:LOCALAPPDATA\$DIST_NAME"
$ExePath     = "$InstallRoot\tektronix_mcp_server.exe"
$ConfigDir   = "$env:APPDATA\Claude"
$ConfigPath  = "$ConfigDir\claude_desktop_config.json"
$EnvFile     = "$ScriptDir\.env"

Write-Host ""
Write-Host "============================================================"
Write-Host "  Tektronix MCP Server v$VERSION - Installer"
Write-Host "============================================================"
Write-Host ""
Write-Host "Install location: $InstallRoot"
Write-Host ""

# Verify the exe is present in the distribution folder
if (-not (Test-Path "$ScriptDir\tektronix_mcp_server.exe")) {
    Write-Host "ERROR: tektronix_mcp_server.exe not found in $ScriptDir"
    Write-Host "       Run install.bat from inside the $DIST_NAME folder."
    Read-Host "Press Enter to exit"
    exit 1
}

# Remove previous install of same version if present
if (Test-Path $InstallRoot) {
    Write-Host "Removing previous installation..."
    Remove-Item -Recurse -Force $InstallRoot
}

# Copy distribution to install location
Write-Host "Copying files..."
Copy-Item -Recurse -Force $ScriptDir $InstallRoot
Write-Host "  [OK] Files copied to $InstallRoot"

# Read settings from .env file if present
$KnowledgeRepo  = ""
$KnowledgeToken = ""
$ExpertMode     = "0"

if (Test-Path $EnvFile) {
    Write-Host "  [OK] Reading settings from .env ..."
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
        $parts = $_ -split '=', 2
        if ($parts.Length -eq 2) {
            $k = $parts[0].Trim()
            $v = $parts[1].Trim()
            switch ($k) {
                "TEK_KNOWLEDGE_REPO"   { $KnowledgeRepo  = $v }
                "TEK_KNOWLEDGE_TOKEN"  { $KnowledgeToken = $v }
                "TEK_EXPERT_MODE"      { $ExpertMode     = $v }
            }
        }
    }
} else {
    Write-Host ""
    Write-Host "No .env file found."
    Write-Host "(Optional: knowledge sync settings for shared lessons learned)"
    Write-Host "(Press Enter to skip - you can edit claude_desktop_config.json later)"
    Write-Host ""

    $KnowledgeRepo = Read-Host "TEK_KNOWLEDGE_REPO (or blank to skip)"
    if ($KnowledgeRepo) {
        $secTok = Read-Host "TEK_KNOWLEDGE_TOKEN (hidden)" -AsSecureString
        $KnowledgeToken = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                              [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secTok))
        $em = Read-Host "TEK_EXPERT_MODE (1=expert, 0=contributor) default 0"
        if ($em.Trim() -ne "") { $ExpertMode = $em.Trim() }
    }
}

# Build the mcpServers entry
$EnvBlock = [PSCustomObject]@{
    TEK_INSTALL_PATH    = $InstallRoot
}
# Only add knowledge sync vars if configured
if ($KnowledgeRepo) {
    $EnvBlock | Add-Member -MemberType NoteProperty -Name "TEK_KNOWLEDGE_REPO"  -Value $KnowledgeRepo
    $EnvBlock | Add-Member -MemberType NoteProperty -Name "TEK_KNOWLEDGE_TOKEN" -Value $KnowledgeToken
    $EnvBlock | Add-Member -MemberType NoteProperty -Name "TEK_EXPERT_MODE"     -Value $ExpertMode
}

$ServerEntry = [PSCustomObject]@{
    command = $ExePath
    args    = @()
    env     = $EnvBlock
}

# Update claude_desktop_config.json - preserve all existing content
Write-Host ""
Write-Host "Updating Claude Desktop config..."

if (-not (Test-Path $ConfigDir)) {
    New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
}

if (Test-Path $ConfigPath) {
    try {
        $Config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        Write-Host "  [WARN] Could not parse existing config - backing up and starting fresh."
        Copy-Item $ConfigPath "$ConfigPath.bak" -Force
        $Config = [PSCustomObject]@{}
    }
} else {
    $Config = [PSCustomObject]@{}
}

if (-not (Get-Member -InputObject $Config -Name "mcpServers" -MemberType NoteProperty)) {
    $Config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value ([PSCustomObject]@{})
}

if (Get-Member -InputObject $Config.mcpServers -Name "tektronix" -MemberType NoteProperty) {
    $Config.mcpServers.tektronix = $ServerEntry
} else {
    $Config.mcpServers | Add-Member -MemberType NoteProperty -Name "tektronix" -Value $ServerEntry
}

# Write UTF-8 without BOM to avoid Claude Desktop parse errors
$ConfigJson = $Config | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText($ConfigPath, $ConfigJson, [System.Text.UTF8Encoding]::new($false))

Write-Host "  [OK] $ConfigPath updated"

# Done
Write-Host ""
Write-Host "============================================================"
Write-Host "  INSTALL COMPLETE"
Write-Host ""
Write-Host "  Installed to: $InstallRoot"
Write-Host "  Config:       $ConfigPath"
Write-Host ""
Write-Host "  Restart Claude Desktop to activate the MCP server."
Write-Host "============================================================"
Read-Host "Press Enter to exit"
