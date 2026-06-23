$RepoUrl = "ssh://git@localhost:2222/owner/test-repo.git"
$OwnerKey = "C:\path\to\owner_key"
$ReadOnlyKey = "C:\path\to\readonly_key"
$WriteKey = "C:\path\to\write_key"
$AdminKey = "C:\path\to\admin_key"
$UnknownKey = "C:\path\to\unknown_key"
$WorkDir = "C:\temp\securegit-ssh-verification"

Write-Host "====================================================="
Write-Host " SecureGit SSH Role & Branch Protection Verification "
Write-Host "====================================================="

if (Test-Path $WorkDir) {
    Remove-Item -Recurse -Force $WorkDir
}
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
Set-Location $WorkDir

$results = @{
    "OwnerClone" = $false
    "ReadClone" = $false
    "UnauthorizedClone" = $false
    "ReadPushRejected" = $false
    "WriteUnprotectedPush" = $false
    "WriteProtectedPush" = $false
    "AdminProtectedPush" = $false
}

Write-Host "`n--- Test 1: Owner Clone ---"
$env:GIT_SSH_COMMAND = "ssh -i $OwnerKey -o IdentitiesOnly=yes -v"
git clone $RepoUrl owner-clone 2>&1 | Out-String
if ($LASTEXITCODE -eq 0 -and (Test-Path "owner-clone")) {
    Write-Host "PASS: Owner clone succeeded." -ForegroundColor Green
    $results["OwnerClone"] = $true
} else {
    Write-Host "FAIL: Owner clone failed." -ForegroundColor Red
}

Write-Host "`n--- Test 2: Read Collaborator Clone ---"
$env:GIT_SSH_COMMAND = "ssh -i $ReadOnlyKey -o IdentitiesOnly=yes -v"
git clone $RepoUrl readonly-clone 2>&1 | Out-String
if ($LASTEXITCODE -eq 0 -and (Test-Path "readonly-clone")) {
    Write-Host "PASS: Read collaborator clone succeeded." -ForegroundColor Green
    $results["ReadClone"] = $true
} else {
    Write-Host "FAIL: Read collaborator clone failed." -ForegroundColor Red
}

Write-Host "`n--- Test 3: Unauthorized Clone Rejection ---"
$env:GIT_SSH_COMMAND = "ssh -i $UnknownKey -o IdentitiesOnly=yes -v"
git clone $RepoUrl unauthorized-clone 2>&1 | Out-String
if ($LASTEXITCODE -ne 0 -and (-not (Test-Path "unauthorized-clone"))) {
    Write-Host "PASS: Unauthorized clone rejected." -ForegroundColor Green
    $results["UnauthorizedClone"] = $true
} else {
    Write-Host "FAIL: Unauthorized clone was not rejected." -ForegroundColor Red
}

Write-Host "`n--- Test 4: Read Collaborator Push Rejection ---"
if (Test-Path "readonly-clone") {
    $env:GIT_SSH_COMMAND = "ssh -i $ReadOnlyKey -o IdentitiesOnly=yes -v"
    Set-Location "readonly-clone"
    "readonly push attempt" | Out-File readonly-test.txt
    git add readonly-test.txt
    git commit -m "readonly push attempt" | Out-Null
    git push origin main 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PASS: Read collaborator push rejected." -ForegroundColor Green
        $results["ReadPushRejected"] = $true
    } else {
        Write-Host "FAIL: Read collaborator push succeeded." -ForegroundColor Red
    }
    Set-Location $WorkDir
} else {
    Write-Host "SKIP: Read collaborator clone missing." -ForegroundColor Yellow
}

Write-Host "`n--- Test 5: Write Collaborator Push to Unprotected Branch ---"
$env:GIT_SSH_COMMAND = "ssh -i $WriteKey -o IdentitiesOnly=yes -v"
git clone $RepoUrl write-clone 2>&1 | Out-String
if ($LASTEXITCODE -eq 0 -and (Test-Path "write-clone")) {
    Set-Location "write-clone"
    git checkout -b write-test 2>&1 | Out-String
    "write push test" | Out-File write-test.txt
    git add write-test.txt
    git commit -m "write push test" | Out-Null
    git push origin write-test 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0) {
        Write-Host "PASS: Write collaborator unprotected push succeeded." -ForegroundColor Green
        $results["WriteUnprotectedPush"] = $true
    } else {
        Write-Host "FAIL: Write collaborator unprotected push failed." -ForegroundColor Red
    }
    Set-Location $WorkDir
} else {
    Write-Host "FAIL: Write collaborator clone failed." -ForegroundColor Red
}

Write-Host "`n--- Test 6: Write Collaborator Blocked by Protected Branch ---"
if (Test-Path "write-clone") {
    $env:GIT_SSH_COMMAND = "ssh -i $WriteKey -o IdentitiesOnly=yes -v"
    Set-Location "write-clone"
    git checkout main 2>&1 | Out-String
    "protected push attempt" | Out-File protected-test.txt
    git add protected-test.txt
    git commit -m "protected push attempt" | Out-Null
    git push origin main 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PASS: Write collaborator protected push rejected." -ForegroundColor Green
        $results["WriteProtectedPush"] = $true
    } else {
        Write-Host "FAIL: Write collaborator protected push succeeded." -ForegroundColor Red
    }
    Set-Location $WorkDir
} else {
    Write-Host "SKIP: Write collaborator clone missing." -ForegroundColor Yellow
}

Write-Host "`n--- Test 7: Admin/Owner Protected Branch Behavior ---"
$env:GIT_SSH_COMMAND = "ssh -i $AdminKey -o IdentitiesOnly=yes -v"
git clone $RepoUrl admin-clone 2>&1 | Out-String
if ($LASTEXITCODE -eq 0 -and (Test-Path "admin-clone")) {
    Set-Location "admin-clone"
    "admin protected push test" | Out-File admin-test.txt
    git add admin-test.txt
    git commit -m "admin protected push test" | Out-Null
    git push origin main 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0) {
        Write-Host "PASS: Admin protected push succeeded." -ForegroundColor Green
        $results["AdminProtectedPush"] = $true
    } else {
        Write-Host "FAIL: Admin protected push failed." -ForegroundColor Red
    }
    Set-Location $WorkDir
} else {
    Write-Host "FAIL: Admin clone failed." -ForegroundColor Red
}

Write-Host "`n====================================================="
Write-Host " Final Checklist"
Write-Host "====================================================="
function Get-Check { param($val) if ($val) { return "[x]" } else { return "[ ]" } }
Write-Host "$(Get-Check $results["OwnerClone"]) Owner clone passed"
Write-Host "$(Get-Check $results["ReadClone"]) Read collaborator clone passed"
Write-Host "$(Get-Check $results["UnauthorizedClone"]) Unauthorized clone rejected"
Write-Host "$(Get-Check $results["ReadPushRejected"]) Read collaborator push rejected"
Write-Host "$(Get-Check $results["WriteUnprotectedPush"]) Write collaborator unprotected push passed"
Write-Host "$(Get-Check $results["WriteProtectedPush"]) Write collaborator protected push rejected"
Write-Host "$(Get-Check $results["AdminProtectedPush"]) Owner/admin protected push behavior verified"
Write-Host "[ ] Server logs confirmed correct SECUREGIT_USER_ID"

Write-Host "`nDone."
