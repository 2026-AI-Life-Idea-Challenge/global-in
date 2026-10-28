param([switch]$Refresh, [switch]$FollowupOnly)
$ErrorActionPreference = 'Stop'
$reviewRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$reviewOut = Join-Path $reviewRoot 'data/raw/legal_review/20261028/australia'
New-Item -ItemType Directory -Force -Path $reviewOut | Out-Null
$sources = [ordered]@{
    regulations_volume1 = 'https://www.legislation.gov.au/F1996B03551/2026-10-02/2026-10-02/text/original/epub/OEBPS/document_1/document_1.html'
    regulations_volume2 = 'https://www.legislation.gov.au/F1996B03551/2026-10-02/2026-10-02/text/original/epub/OEBPS/document_2/document_2.html'
    regulations_volume3 = 'https://www.legislation.gov.au/F1996B03551/2026-10-02/2026-10-02/text/original/epub/OEBPS/document_3/document_3.html'
    student_reform_2026 = 'https://www.legislation.gov.au/F2026L01347/asmade/2026-10-01/text/original/epub/OEBPS/document_1/document_1.html'
    sid_reform_2024 = 'https://www.legislation.gov.au/F2024L01585/asmade/2024-12-06/text/original/epub/OEBPS/document_1/document_1.html'
    training_reform_2026 = 'https://www.legislation.gov.au/F2026L00221/asmade/2026-03-10/text/original/epub/OEBPS/document_1/document_1.html'
    english_482_2025 = 'https://www.legislation.gov.au/F2025L01066/asmade/2025-09-10/text/original/epub/OEBPS/document_1/document_1.html'
    wh_uk_exemption_2024 = 'https://www.legislation.gov.au/F2024L00661/asmade/2024-06-07/text/original/epub/OEBPS/document_1/document_1.html'
    exemptions_186_494 = 'https://www.legislation.gov.au/F2019L01404/2024-12-07/2024-12-07/text/1/epub/OEBPS/document_1/document_1.html'
    student_classes = 'https://www.legislation.gov.au/F2020L00955/2026-10-02/2026-10-02/text/original/epub/OEBPS/document_1/document_1.html'
    wh_age_reform_2026 = 'https://www.legislation.gov.au/F2026L00876/asmade/2026-06-30/text/original/epub/OEBPS/document_1/document_1.html'
    wh_417_arrangements = 'https://www.legislation.gov.au/F2026L00878/asmade/2026-06-30/text/original/epub/OEBPS/document_1/document_1.html'
    points_pass_mark = 'https://www.legislation.gov.au/F2019L01400/asmade/2019-10-31/text/original/epub/OEBPS/document_1/document_1.html'
    english_500_2025 = 'https://www.legislation.gov.au/F2025L00906/latest/text'
    english_levels_2025 = 'https://www.legislation.gov.au/F2025L00905/latest/text'
    wh_462_arrangements = 'https://www.legislation.gov.au/F2026L00883/asmade/text'
    skilled_occupations = 'https://www.legislation.gov.au/F2019L00278/latest/text'
    occupations_482 = 'https://www.legislation.gov.au/F2024L01620/latest/text'
    occupations_494 = 'https://www.legislation.gov.au/F2019L01403/latest/text'
    mandatory_skills_482 = 'https://www.legislation.gov.au/F2018L00294/latest/text'
    specified_work_462 = 'https://www.legislation.gov.au/F2022L00272/latest/text'
    specified_work_417 = 'https://www.legislation.gov.au/F2022L00271/latest/text'
    occupations_186 = 'https://www.legislation.gov.au/F2024L01618/latest/text'
    act_volume1 = 'https://www.legislation.gov.au/C1958A00062/2026-10-08/2026-10-08/text/original/epub/OEBPS/document_1/document_1.html'
    act_volume2 = 'https://www.legislation.gov.au/C1958A00062/2026-10-08/2026-10-08/text/original/epub/OEBPS/document_2/document_2.html'
}
if ($FollowupOnly) {
    $reviewOut = Join-Path $reviewRoot 'data/raw/legal_review/20261028/australia/followup'
    New-Item -ItemType Directory -Force -Path $reviewOut | Out-Null
    $sources = [ordered]@{
        nsw_190 = 'https://www.nsw.gov.au/visas-and-migration/skilled-visas/skilled-nominated-visa-subclass-190'
        nsw_491 = 'https://www.nsw.gov.au/visas-and-migration/skilled-visas/skilled-work-regional-visa-subclass-491'
        nsw_skills = 'https://www.nsw.gov.au/visas-and-migration/skilled-visas/nsw-skills-lists'
        victoria_2026 = 'https://liveinmelbourne.vic.gov.au/migrate/skilled-migration-visas/2026-27-skilled-visa-nomination-program'
        tasmania_2026 = 'https://www.migration.tas.gov.au/news/2024-25_program_open_to_rois'
        act_190 = 'https://www.act.gov.au/migration/skilled-migrants/190-nomination-criteria'
        act_491 = 'https://www.act.gov.au/migration/skilled-migrants/491-nomination-criteria'
        act_guidelines = 'https://www.act.gov.au/migration/resources/library-guidelines-and-invitations'
        nt_status = 'https://australiasnorthernterritory.com.au/move/migrate-to-work/nt-government-visa-nomination'
        queensland_skilled = 'https://migration.qld.gov.au/visa-options/skilled-visas'
        queensland_roi = 'https://migration.qld.gov.au/nomination-process/registration-of-interest'
        sa_skilled = 'https://migration.sa.gov.au/before-applying/visa-options-and-pathways/skilled-migrants'
        sa_news = 'https://migration.sa.gov.au/news'
        sa_update_2026 = 'https://migration.sa.gov.au/news/south-australias-general-skilled-migration-program-update'
        wa_program = 'https://migration.wa.gov.au/our-services-support/state-nominated-migration-program'
        thapa_primary_archive = 'https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/FCCA/2021/686.html'
    }
}
$rows = @()
$previous = @{}
if (Test-Path -LiteralPath (Join-Path $reviewOut 'fetch_manifest.json')) {
    foreach ($item in (Get-Content -LiteralPath (Join-Path $reviewOut 'fetch_manifest.json') -Raw | ConvertFrom-Json)) { $previous[$item.source_id]=$item }
}
foreach ($entry in $sources.GetEnumerator()) {
    $target = Join-Path $reviewOut ($entry.Key + '.html')
    $row = [ordered]@{source_id=$entry.Key; source_url=$entry.Value; checked_at=[DateTimeOffset]::Now.ToString('o'); status='not_fetched'}
    try {
        if ($Refresh -or -not (Test-Path -LiteralPath $target) -or ($previous.ContainsKey($entry.Key) -and $previous[$entry.Key].source_url -ne $entry.Value)) {
            Invoke-WebRequest -Uri $entry.Value -OutFile $target -TimeoutSec 22 -MaximumRetryCount 0
        } elseif ($previous.ContainsKey($entry.Key) -and $previous[$entry.Key].resolved_source_url) {
            $row.resolved_source_url=$previous[$entry.Key].resolved_source_url
        }
        $content = Get-Content -LiteralPath $target -Raw
        if ($content -match 'https://www\.legislation\.gov\.au/[^"<> ]+/epub/OEBPS/document_1/document_1\.html') {
            $directUrl = $Matches[0]
            Invoke-WebRequest -Uri $directUrl -OutFile $target -TimeoutSec 22 -MaximumRetryCount 0
            $row.resolved_source_url=$directUrl
        }
        $row.status='downloaded'
        $row.source_file='data/raw/legal_review/20261028/australia/' + $(if ($FollowupOnly) { 'followup/' } else { '' }) + [IO.Path]::GetFileName($target)
        $row.sha256=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLower()
        $row.bytes=(Get-Item -LiteralPath $target).Length
    } catch { $row.status='download_failed'; $row.error=$_.Exception.Message }
    $rows += [pscustomobject]$row
    Write-Output ($entry.Key + ': ' + $row.status)
}
$json = ConvertTo-Json -InputObject @($rows) -Depth 8
$json | Set-Content -LiteralPath (Join-Path $reviewOut 'fetch_manifest.json') -Encoding utf8
$manifestName = if ($FollowupOnly) { 'australia_followup_source_manifest_20261028.json' } else { 'australia_source_manifest_20261028.json' }
$json | Set-Content -LiteralPath (Join-Path $reviewRoot ('data/processed/legal_review/' + $manifestName)) -Encoding utf8
