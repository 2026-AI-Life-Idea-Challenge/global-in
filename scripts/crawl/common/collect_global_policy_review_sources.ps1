param([switch]$Refresh)
$ErrorActionPreference='Stop'
$reviewRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$outDir=Join-Path $reviewRoot 'data/raw/legal_review/20261028/global'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$plan=Get-Content -LiteralPath (Join-Path $reviewRoot 'data/processed/legal_review/global_policy_source_plan_20261028.json') -Raw | ConvertFrom-Json
$rows=@()
foreach ($item in $plan) {
    $uri=[Uri]$item.source_url
    if ($uri.Scheme -ne 'https' -or $uri.Host -notmatch '(\.gov$|\.go\.jp$|\.gc\.ca$|(^|\.)canada\.ca$|(^|\.)gesetze-im-internet\.de$|(^|\.)make-it-in-germany\.com$|(^|\.)diplo\.de$)') { throw "Unexpected source domain: $($uri.Host)" }
    $target=Join-Path $outDir ($item.source_id+'.html')
    $row=[ordered]@{source_id=$item.source_id;source_url=$item.source_url;checked_at=[DateTimeOffset]::Now.ToString('o');status='not_fetched'}
    try {
        if ($Refresh -or -not (Test-Path -LiteralPath $target)) {
            Invoke-WebRequest -Uri $uri -OutFile $target -TimeoutSec 18 -MaximumRetryCount 0
        }
        $row.status='downloaded'
        $row.source_file='data/raw/legal_review/20261028/global/'+[IO.Path]::GetFileName($target)
        $row.sha256=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLower()
        $row.bytes=(Get-Item -LiteralPath $target).Length
    } catch { $row.status='download_failed';$row.error=$_.Exception.Message }
    $rows+=[pscustomobject]$row
    Write-Output ($item.source_id+': '+$row.status)
}
$json=ConvertTo-Json -InputObject @($rows) -Depth 8
$json | Set-Content -LiteralPath (Join-Path $outDir 'fetch_manifest.json') -Encoding utf8
$json | Set-Content -LiteralPath (Join-Path $reviewRoot 'data/processed/legal_review/global_policy_source_manifest_20261028.json') -Encoding utf8
