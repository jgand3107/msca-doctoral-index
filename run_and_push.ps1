# Weekly local runner for the multi-source scholarship tracker.
# Runs from this machine (sites serve full results to residential IPs). Each
# tier only writes valid data, so we always commit whatever changed, then
# report a failure if the primary tier was degraded. Logs to weekly_run.log.

$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo
$log = Join-Path $repo 'weekly_run.log'

"=== Run $(Get-Date -Format s) ===" | Out-File -FilePath $log -Append -Encoding utf8

python run.py *>> $log
$runCode = $LASTEXITCODE

# Regenerate the local HTML reports (incl. the combined scholarships_report.html)
# so they stay current for viewing. They are gitignored, so not committed.
python report.py *>> $log

# Commit + push whatever data changed (valid data only is ever written).
git config merge.ours.driver true
git add data/
git diff --staged --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "Weekly scholarship update (local $(Get-Date -Format yyyy-MM-dd))" *>> $log
    $pushed = $false
    for ($i = 1; $i -le 3; $i++) {
        git push *>> $log
        if ($LASTEXITCODE -eq 0) { $pushed = $true; break }
        "Push rejected; integrating remote changes (attempt $i)..." | Out-File $log -Append -Encoding utf8
        git fetch origin main *>> $log
        git merge --no-edit origin/main *>> $log
    }
    if ($pushed) { "Pushed update." | Out-File $log -Append -Encoding utf8 }
    else { "Could not push after retries." | Out-File $log -Append -Encoding utf8 }
} else {
    "No data changes; nothing to push." | Out-File $log -Append -Encoding utf8
}

if ($runCode -ne 0) {
    "Run reported a primary-tier failure (exit $runCode); any valid data was committed." |
        Out-File $log -Append -Encoding utf8
    exit 1
}
