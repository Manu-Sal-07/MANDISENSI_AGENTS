#!/usr/bin/env pwsh
<#
.SYNOPSIS
MandiSense AI - Agent Runner PowerShell Script
.DESCRIPTION
Run both Seasonality and Arrival Volume agents and output JSON.
.EXAMPLE
.\run_agents.ps1 -Commodity tomato -Mandi kolar
.\run_agents.ps1 tomato kolar
.\run_agents.ps1
#>

param(
    [Parameter(Position=0)]
    [string]$Commodity = "tomato",
    
    [Parameter(Position=1)]
    [string]$Mandi = "kolar"
)

# Activate virtual environment
$venvPath = ".venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    & $venvPath
} else {
    Write-Host "❌ Virtual environment not found at $venvPath" -ForegroundColor Red
    exit 1
}

# Run the agent script
python "run_agents.py" "$Commodity" "$Mandi"
