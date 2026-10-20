# Weekly local runner for the MSCA doctoral scraper.
# Scrapes from this machine (EURAXESS serves full results to residential IPs),
# and only commits/pushes if the scrape passed validation. Run by Windows Task
# Scheduler; also fine to run by hand. Output is logged to weekly_run.log.

$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo
$log = Join-Path $repo 'weekly_run.log'

"=== Run $(Get-Date -Format s) ===" | Out-File -FilePath $log -Append -Encoding utf8

# 1) Scrape. run.py exits non-zero (and writes nothing) if the scrape looks
#    degraded, so a bad run never commits.
python run.py *>> $log
if ($LASTEXITCODE -ne 0) {
    "Scrape failed (exit $LASTEXITCODE); data left unchanged, nothing pushed." |
        Out-File -FilePath $log -Append -Encoding utf8
    exit 1
}

# 2) Commit + push only if the data changed.
git config merge.ours.driver true
git add data/
git diff --staged --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "Weekly MSCA doctoral update (local $(Get-Date -Format yyyy-MM-dd))" *>> $log
    $pushed = $false
    for ($i = 1; $i -le 3; $i++) {
        git push *>> $log
        if ($LASTEXITCODE -eq 0) { $pushed = $true; break }
        "Push rejected; integrating remote changes (attempt $i)..." |
            Out-File -FilePath $log -Append -Encoding utf8
        git fetch origin main *>> $log
        git merge --no-edit origin/main *>> $log
    }
    if ($pushed) { "Pushed update." | Out-File -FilePath $log -Append -Encoding utf8 }
    else { "Could not push after retries." | Out-File -FilePath $log -Append -Encoding utf8; exit 1 }
} else {
    "No data changes; nothing to push." | Out-File -FilePath $log -Append -Encoding utf8
}
