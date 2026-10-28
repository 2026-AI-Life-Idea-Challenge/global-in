param([switch]$SupplementalOnly, [switch]$ResolutionOnly, [switch]$F1Only)
$ErrorActionPreference = 'Stop'
$reviewRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$reviewInput = Get-Content -LiteralPath (Join-Path $reviewRoot 'data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json') -Raw | ConvertFrom-Json
$reviewIds = @{}
foreach ($policy in $reviewInput.policy_candidates) {
    if ($policy.country -in @('usa', 'japan')) {
        foreach ($id in $policy.source_evidence_ids) { $reviewIds[$id] = $true }
    }
}
$reviewUrls = @($reviewInput.evidence | Where-Object { $reviewIds.ContainsKey($_.evidence_id) } | Select-Object -ExpandProperty source_url -Unique | Sort-Object)
if ($SupplementalOnly) {
    $reviewUrls = @(
        'https://www.niied.go.kr/web/main/file/download/uu/d38331d7144c4042b8069bfbbb7855da',
        'https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-62/subpart-B/section-62.22',
        'https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-62/subpart-B/section-62.23',
        'https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-62/subpart-B/section-62.32',
        'https://www.ecfr.gov/current/title-8/chapter-I/subchapter-B/part-214/section-214.2',
        'https://www.ecfr.gov/current/title-8/chapter-I/subchapter-B/part-214/section-214.1',
        'https://www.ecfr.gov/current/title-20/chapter-V/part-655/subpart-H/section-655.731',
        'https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/section-300.html'
    )
}
$reviewOut = Join-Path $reviewRoot 'data/raw/legal_review/20261028'
if ($ResolutionOnly) {
    $reviewUrls = @(
        'https://www.moj.go.jp/isa/content/001363332.pdf',
        'https://www.moj.go.jp/isa/applications/status/student.html',
        'https://www.moj.go.jp/isa/10_00258.html',
        'https://www.ca1.uscourts.gov/content/26-1699o_6828777',
        'https://www.ca1.uscourts.gov/sites/ca1/files/opnfiles/26-1699O-01A.pdf',
        'https://www.govinfo.gov/content/pkg/USCOURTS-mad-1_25-cv-13829/pdf/USCOURTS-mad-1_25-cv-13829-0.pdf',
        'https://www.govinfo.gov/content/pkg/USCOURTS-cand-4_25-cv-08454/pdf/USCOURTS-cand-4_25-cv-08454-17.pdf',
        'https://www.ecfr.gov/current/title-8/chapter-I/subchapter-B/part-106/section-106.2'
    )
}
if ($F1Only) {
    $reviewUrls = @(
        'https://www.ecfr.gov/current/title-8/chapter-I/subchapter-B/part-214/section-214.13',
        'https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html'
    )
}
New-Item -ItemType Directory -Force -Path $reviewOut | Out-Null
$reviewRows = [System.Collections.Generic.List[object]]::new()
if (($SupplementalOnly -or $ResolutionOnly -or $F1Only) -and (Test-Path -LiteralPath (Join-Path $reviewOut 'fetch_manifest.json'))) {
    foreach ($existing in (Get-Content -LiteralPath (Join-Path $reviewOut 'fetch_manifest.json') -Raw | ConvertFrom-Json)) {
        if ($existing.source_url -notin $reviewUrls) { $reviewRows.Add($existing) }
    }
}
foreach ($sourceUrl in $reviewUrls) {
    $sourceUri = [Uri]$sourceUrl
    if ($sourceUri.Scheme -ne 'https' -or $sourceUri.Host -notmatch '(\.gov$|\.go\.jp$|\.go\.kr$|\.gc\.ca$)') { throw 'Unexpected source host' }
    $urlHash = [Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($sourceUrl))).ToLower().Substring(0,16)
    $extension = if ($sourceUri.AbsolutePath.EndsWith('.pdf')) { '.pdf' } else { '.html' }
    $target = Join-Path $reviewOut ($urlHash + $extension)
    $row = [ordered]@{ source_url=$sourceUrl; checked_at=[DateTimeOffset]::Now.ToString('o'); status='not_fetched' }
    try {
        if (-not (Test-Path -LiteralPath $target)) {
            Invoke-WebRequest -Uri $sourceUrl -OutFile $target -TimeoutSec 18 -MaximumRetryCount 0
        }
        $row.status='downloaded'
        $row.source_file='data/raw/legal_review/20261028/' + [IO.Path]::GetFileName($target)
        $row.sha256=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLower()
        $row.bytes=(Get-Item -LiteralPath $target).Length
    } catch {
        $row.status='fetch_failed'
        $row.error_type=$_.Exception.GetType().Name
        if ($_.Exception.Response) { $row.http_status=[int]$_.Exception.Response.StatusCode }
    }
    $reviewRows.Add($row)
    $reviewRows | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $reviewOut 'fetch_manifest.json') -Encoding utf8
    Write-Output ($row.status + ' ' + $sourceUri.Host + $sourceUri.AbsolutePath)
}
Write-Output ('TOTAL ' + $reviewRows.Count)
$reviewSharedManifest = Join-Path $reviewRoot 'data/processed/legal_review/source_manifest_20261028.json'
$reviewRows | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reviewSharedManifest -Encoding utf8
