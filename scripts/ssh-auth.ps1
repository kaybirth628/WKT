# Shared SSH password / credential helpers for WKT cloud scripts.

function Get-WktSshPlainPassword {
    param($Cfg)

    $pass = [string]$Cfg.ssh_password
    if ([string]::IsNullOrWhiteSpace($pass)) {
        $pass = [string]$env:WKT_SSH_PASS
    }

    while ([string]::IsNullOrWhiteSpace($pass)) {
        $sec = Read-Host "SSH password (root)" -AsSecureString
        if ($null -eq $sec) {
            Write-Host "Password cannot be empty. Try again." -ForegroundColor Yellow
            continue
        }
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
        try {
            $pass = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
        if ([string]::IsNullOrWhiteSpace($pass)) {
            Write-Host "Password cannot be empty. Try again." -ForegroundColor Yellow
        }
    }

    return $pass.Trim()
}

function Get-WktSshCredential {
    param($Cfg)

    $user = if ($Cfg.ssh_user) { [string]$Cfg.ssh_user } else { "root" }
    $pass = Get-WktSshPlainPassword -Cfg $Cfg
    return New-Object System.Management.Automation.PSCredential($user, (
        ConvertTo-SecureString $pass -AsPlainText -Force
    ))
}
