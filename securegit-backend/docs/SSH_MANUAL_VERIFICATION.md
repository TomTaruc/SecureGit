# SSH Manual Verification

This document outlines how to manually verify SSH clone and push behavior across different roles in SecureGit, ensuring branch protection and access controls are fully enforced via SSH.

## Prerequisites

1. Start the SecureGit backend server.
2. Start the SecureGit SSH server (e.g., `python run_ssh_server.py` or equivalent).
3. Create test users: `test_owner`, `readonly_user`, `write_user`, `admin_user`.
4. Register SSH keys for each user via the SecureGit API/UI.
5. Create a repository `test-repo` under `test_owner` and assign roles:
   - `readonly_user`: Read
   - `write_user`: Write
   - `admin_user`: Admin
6. Configure branch protection on `main` to require Admin access for pushes.

## How to Avoid Cached SSH Identity

When running tests locally, SSH clients might try multiple cached identities (from `ssh-agent`). To avoid this and force the exact SSH key for a specific test user, use the following `GIT_SSH_COMMAND`:

```powershell
$env:GIT_SSH_COMMAND = "ssh -i C:\path\to\specific_key -o IdentitiesOnly=yes -v"
```

The `-v` flag (verbose) helps confirm which SSH key was successfully offered and accepted.

## Checking Server Logs

You can inspect the SSH server logs to confirm the identity context. Look for lines indicating the mapped user ID, for example:

```text
Authentication successful for user test_owner (SECUREGIT_USER_ID: 1)
```

## Running the Automated Script

An automated PowerShell script is provided to walk through all scenarios:

```powershell
.\scripts\manual_ssh_verification.ps1
```

Before running, edit the variables at the top of the script to match your environment paths:

```powershell
$RepoUrl = "ssh://git@localhost:2222/test_owner/test-repo.git"
$OwnerKey = "C:\path\to\owner_key"
$ReadOnlyKey = "C:\path\to\readonly_key"
$WriteKey = "C:\path\to\write_key"
$AdminKey = "C:\path\to\admin_key"
```

## Expected Results

### 1. Owner Clone
Command: `git clone <repo>` using owner key.
Expected: Clone succeeds.

### 2. Read Collaborator Clone
Command: `git clone <repo>` using read-only key.
Expected: Clone succeeds.

### 3. Unauthorized Clone
Command: `git clone <repo>` using unknown key.
Expected: Clone rejected (connection closed / access denied).

### 4. Read Collaborator Push Rejection
Command: `git push origin main` using read-only key.
Expected: Push rejected. No commit accepted. Error mentions insufficient permission or branch protection.

### 5. Write Collaborator Push to Unprotected Branch
Command: `git push origin write-test` (new branch) using write key.
Expected: Push succeeds.

### 6. Write Collaborator Blocked by Protected Branch
Command: `git push origin main` using write key.
Expected: Push rejected by branch protection. No commit accepted.

### 7. Admin/Owner Protected Branch Behavior
Command: `git push origin main` using admin or owner key.
Expected: Push succeeds (or follows specific protection policy for admins).

## What Failure Means

If any step fails (e.g., a read collaborator can push, or a write collaborator pushes to a protected branch), it indicates a critical authorization flaw in the SSH `pre-receive` hook or the backend hook validation endpoint. Do not sign off on SecureGit until these tests pass securely.
