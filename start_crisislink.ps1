# Starts everything CrisisLink needs on this machine:
#   1. a Cloudflare quick tunnel to n8n (new public URL every run)
#   2. n8n with WEBHOOK_URL set to that URL (so Telegram can reach the trigger)
#   3. re-points Claude Code's "n8n" MCP server at the new URL
# Afterwards: /mcp -> n8n -> Authenticate in Claude Code, then Unpublish + Publish the workflow in n8n.
#
# Usage (from the project folder):  powershell -ExecutionPolicy Bypass -File .\start_crisislink.ps1

$ErrorActionPreference = 'Stop'
$metrics = '127.0.0.1:20241'

if (Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Something is already listening on port 5678 (n8n already running?). Stop it first.'
}

# 1. Tunnel in its own window; the fixed metrics port lets us read the generated URL
Write-Host 'Starting Cloudflare tunnel...'
Start-Process cloudflared -ArgumentList 'tunnel', '--url', 'http://localhost:5678', '--metrics', $metrics
$url = $null
for ($i = 0; $i -lt 30 -and -not $url; $i++) {
    Start-Sleep -Seconds 2
    try { $h = (Invoke-RestMethod "http://$metrics/quicktunnel" -TimeoutSec 2).hostname; if ($h) { $url = "https://$h" } } catch {}
}
if (-not $url) { throw 'The tunnel did not report a URL within 60 s. Check the cloudflared window.' }
Write-Host "Tunnel URL: $url"

# 2. n8n in its own window, started with the tunnel URL
Write-Host 'Starting n8n (takes 1-2 minutes)...'
Start-Process powershell -ArgumentList '-NoExit', '-Command', "`$env:WEBHOOK_URL='$url/'; npx n8n"
$ready = $false
for ($i = 0; $i -lt 90 -and -not $ready; $i++) {
    Start-Sleep -Seconds 2
    try { $ready = (Invoke-WebRequest 'http://127.0.0.1:5678/healthz/readiness' -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200 } catch {}
}
if (-not $ready) { throw 'n8n did not become ready within 3 minutes. Check the n8n window.' }
Write-Host 'n8n is ready: http://localhost:5678'

# 3. Claude Code MCP server (user scope, so it works from any folder)
claude mcp remove n8n -s user 2>$null | Out-Null
claude mcp add --scope user --transport http n8n "$url/mcp-server/http" | Out-Null
Write-Host "Claude Code MCP server 'n8n' now points to $url/mcp-server/http"

Write-Host ''
Write-Host 'Remaining manual steps:'
Write-Host '  1. In VSCode: Developer: Reload Window, then /mcp -> n8n -> Authenticate'
Write-Host '  2. In n8n: open 01_Telegram_Intake_Router, Unpublish then Publish (registers the new URL with Telegram)'
