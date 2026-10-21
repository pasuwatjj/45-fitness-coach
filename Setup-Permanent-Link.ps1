param([Parameter(Mandatory=$true)][string]$PublicUrl)
$ErrorActionPreference = 'Stop'
$uri = [Uri]$PublicUrl
if (!$uri.IsAbsoluteUri -or $uri.Scheme -ne 'https' -or $uri.AbsolutePath -ne '/' -or $uri.Query -or $uri.Fragment -or $uri.UserInfo -or !$uri.IsDefaultPort -or $uri.Host -eq 'localhost' -or $uri.Host.EndsWith('.trycloudflare.com')) {
    throw 'Enter your own configured HTTPS domain origin only, e.g. https://fitness.your-domain.com'
}
$folder = Join-Path $PSScriptRoot 'data'
New-Item -ItemType Directory -Force -Path $folder | Out-Null
@{public_url=$uri.GetLeftPart([System.UriPartial]::Authority)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $folder 'public-site.json') -Encoding UTF8
Write-Host 'Saved domain setting. This does not register a domain or create a tunnel.' -ForegroundColor Yellow
Write-Host 'In Cloudflare: create a named tunnel, install its Windows connector, publish this hostname to HTTP localhost:5000.'
Write-Host 'Then stop and restart the website. Keep the Host header set to your public hostname.'
Write-Host ($uri.GetLeftPart([System.UriPartial]::Authority) + '/45-fitness-coach') -ForegroundColor Cyan
