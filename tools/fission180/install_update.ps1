# Fission 180 quick update (Windows).
#
# Replaces the Fission 180 module inside an existing Fission 180 with the version from this
# download, so you do not have to wait for a full rebuild. It works on every layout:
# the installed Fission 180 (C:\Program Files\Fission180, found through the registry key the
# installer writes), the portable build unzipped anywhere (bin\Fission180.exe), and a build
# or FreeCAD from before the branding pass (bin\FreeCAD.exe): the folder only needs
# 'bin' and 'Mod' inside.
# A copy of your old version is kept in <Fission 180>\Fission180-backups\<date> (outside Mod,
# because FreeCAD loads every folder inside Mod).
#
# Easiest: double-click install_update.cmd (it starts this script and keeps the
# window open). Everything that happens is also written to install_update.log.
#
# The update copies files over the old ones instead of renaming the Fission 180 folder:
# Windows refuses to rename a folder while anything (an Explorer window, antivirus,
# OneDrive) is looking inside it, but overwriting the files still works then.
#
# "Update now" inside Fission 180 (fission180/update_ui.py) starts this script by itself, after
# Fission 180 quit, with:  -Target <Fission 180 folder> -WaitPid <Fission 180's process id> -Restart -Quiet
#   -WaitPid N      wait (up to 15 minutes) until process N has ended before touching anything
#   -Restart        start Fission 180 again when the update is in
#   -Quiet          never ask anything (no folder picker, no Enter); a failure puts the old version
#                   back and shows one message box with the log's path; implies -NoPause
#   -RunInstaller X after -WaitPid, start the installer X (a full-installer update) and stop
#   -NoDialog       with -Quiet: no message box (the Windows check job of fission180-tests.yml)
# Without these the script behaves exactly as before (the interactive quick update).
param([string]$Target = "", [switch]$NoPause, [switch]$Elevated,
    [int]$WaitPid = 0, [switch]$Restart, [switch]$Quiet, [string]$RunInstaller = "", [switch]$NoDialog)

$ErrorActionPreference = "Stop"
if ($Quiet) { $NoPause = $true }
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$log = Join-Path $here "install_update.log"
try { Start-Transcript -Path $log -Force -Append:$Elevated | Out-Null } catch { }

function Finish($ok, $msg) {
    Write-Host ""
    if ($ok) { Write-Host "[Fission 180] $msg" -ForegroundColor Green }
    else { Write-Host "[Fission 180] $msg" -ForegroundColor Red; Write-Host "[Fission 180] Details: $log" }
    try { Stop-Transcript | Out-Null } catch { }
    # Quiet: nobody is looking at this window, so a failure is told in a message box (the
    # elevated copy leaves that to the one that started it).
    if ((-not $ok) -and $Quiet -and (-not $NoDialog) -and (-not $Elevated)) { Show-Failure $msg }
    if (-not $NoPause) { Read-Host "Press Enter to close" | Out-Null }
    if ($ok) { exit 0 } else { exit 1 }
}

function Show-Failure($msg) {
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [void][System.Windows.Forms.MessageBox]::Show(
            "Fission 180 could not be updated. Your old version was put back.`n`n$msg`n`nDetails: $log",
            "Fission 180 update", "OK", "Warning")
    } catch { }
}

function Wait-ForProcess($id) {
    # Until process $id has ended (Fission 180 quitting after "Update now"), at most 15 minutes.
    $deadline = (Get-Date).AddSeconds(900)
    while ((Get-Process -Id $id -ErrorAction SilentlyContinue) -and ((Get-Date) -lt $deadline)) {
        Start-Sleep -Milliseconds 500
    }
    if (Get-Process -Id $id -ErrorAction SilentlyContinue) { return $false }
    Start-Sleep -Seconds 1  # let Windows let go of the files
    return $true
}

function Start-Program($folder, $name) {
    $bin = Join-Path $folder "bin"
    Start-Process -FilePath (Join-Path $bin $name) -WorkingDirectory $bin
}

function Pick-Folder {
    # A normal Windows folder picker; falls back to typing/dragging the path.
    try {
        Add-Type -AssemblyName System.Windows.Forms
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = "Pick your Fission 180 folder (the one with 'bin' and 'Mod' inside)"
        $dialog.ShowNewFolderButton = $false
        if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { return $dialog.SelectedPath }
        return ""
    } catch {
        Write-Host "Drag your Fission 180 folder (the one with 'bin' and 'Mod' inside) here, then press Enter:"
        return (Read-Host).Trim().Trim('"')
    }
}

function Find-Installed {
    # The Fission 180 installer writes HKLM (all users) or HKCU (current user)
    # \SOFTWARE\Fission180<version> with the install folder as its default value
    # (package/WindowsInstaller/include/declarations.nsh, APP_REGKEY). Returns the folders
    # that still exist. A FreeCAD installation uses SOFTWARE\FreeCAD<version>: not matched.
    $found = @()
    foreach ($hive in @("HKLM:\SOFTWARE", "HKCU:\SOFTWARE")) {
        try {
            $keys = @(Get-ChildItem -Path $hive -ErrorAction SilentlyContinue |
                Where-Object { $_.PSChildName -match '^Fission180\d*$' })
            foreach ($key in $keys) {
                $dir = (Get-ItemProperty -LiteralPath $key.PSPath -ErrorAction SilentlyContinue).'(default)'
                if ($dir -and (Test-Path (Join-Path $dir "bin")) -and (Test-Path (Join-Path $dir "Mod")) -and
                    ($found -notcontains $dir)) {
                    $found += $dir
                }
            }
        } catch { }
    }
    return $found
}

function Program-Name($folder) {
    # The program inside: Fission180.exe since the branding pass, FreeCAD.exe before it.
    foreach ($name in @("Fission180.exe", "FreeCAD.exe", "freecad.exe")) {
        if (Test-Path (Join-Path (Join-Path $folder "bin") $name)) { return $name }
    }
    return ""
}

function Is-Admin {
    try {
        $id = [Security.Principal.WindowsIdentity]::GetCurrent()
        return (New-Object Security.Principal.WindowsPrincipal $id).IsInRole(
            [Security.Principal.WindowsBuiltInRole]::Administrator)
    } catch { return $false }
}

function Can-Write($folder) {
    $probe = Join-Path $folder (".fission180-write-test-" + [guid]::NewGuid().ToString("N"))
    try {
        [IO.File]::WriteAllText($probe, "x")
        Remove-Item -LiteralPath $probe -Force
        return $true
    } catch { return $false }
}

function Copy-Tree($from, $to, [switch]$Tolerant) {
    # Copies every file from $from into $to, overwriting (also read-only files). Tolerant (the
    # put-back after a failed update): a file that cannot be written is told and skipped.
    $count = 0
    $fromFull = (Resolve-Path -LiteralPath $from).Path.TrimEnd('\', '/')
    foreach ($item in Get-ChildItem -LiteralPath $fromFull -Recurse -Force) {
        $rel = $item.FullName.Substring($fromFull.Length).TrimStart('\', '/')
        $dest = Join-Path $to $rel
        if ($item.PSIsContainer) {
            if (-not (Test-Path -LiteralPath $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
            continue
        }
        $parent = Split-Path -Parent $dest
        if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
        if (Test-Path -LiteralPath $dest) {
            $old = Get-Item -LiteralPath $dest -Force
            if ($old.IsReadOnly) { $old.IsReadOnly = $false }
        }
        try {
            Copy-Item -LiteralPath $item.FullName -Destination $dest -Force
        } catch {
            if ($Tolerant) { Write-Host "[Fission 180] could not put back $dest ($($_.Exception.Message))"; continue }
            throw "Could not write $dest. $($_.Exception.Message)"
        }
        $count++
    }
    return $count
}

function Remove-Leftovers($newRoot, $installed) {
    # Deletes files that the new version no longer has (old .py files, __pycache__).
    $installedFull = (Resolve-Path -LiteralPath $installed).Path.TrimEnd('\', '/')
    $removed = 0
    $files = @(Get-ChildItem -LiteralPath $installedFull -Recurse -Force -File)
    foreach ($file in $files) {
        $rel = $file.FullName.Substring($installedFull.Length).TrimStart('\', '/')
        if (-not (Test-Path -LiteralPath (Join-Path $newRoot $rel))) {
            try {
                if ($file.IsReadOnly) { $file.IsReadOnly = $false }
                Remove-Item -LiteralPath $file.FullName -Force
                $removed++
            } catch { Write-Host "[Fission 180] could not remove old file $($file.FullName) (harmless)" }
        }
    }
    # Empty folders left behind, deepest first.
    $dirs = @(Get-ChildItem -LiteralPath $installedFull -Recurse -Force -Directory |
        Sort-Object { $_.FullName.Length } -Descending)
    foreach ($dir in $dirs) {
        if (@(Get-ChildItem -LiteralPath $dir.FullName -Force).Count -eq 0) {
            try { Remove-Item -LiteralPath $dir.FullName -Force } catch { }
        }
    }
    return $removed
}

$accessHelp = ("Windows did not allow Fission 180's files to be changed. Try this: (1) close Fission 180 " +
    "(also check Task Manager for 'Fission180' or 'FreeCAD'), (2) close every File Explorer window " +
    "showing the Fission 180 folder, (3) right-click install_update.cmd > 'Run as administrator'. " +
    "An installed Fission 180 (C:\Program Files\Fission180) always needs the administrator step; " +
    "the portable build in a normal folder such as C:\Fission180 does not.")

$script:backup = ""  # the copy of the old version, once made (Quiet puts it back on a failure)
$script:current = ""
try {
    Write-Host "[Fission 180] quick update, PowerShell $($PSVersionTable.PSVersion)"
    if ($WaitPid -gt 0) {
        Write-Host "[Fission 180] waiting for Fission 180 (process $WaitPid) to close..."
        if (-not (Wait-ForProcess $WaitPid)) {
            Finish $false "Fission 180 did not close (process $WaitPid is still running), so nothing was changed."
        }
        Write-Host "[Fission 180] Fission 180 has closed"
    }
    if ($RunInstaller -ne "") {
        # A full-installer update: Fission 180 has quit, the person sees the normal installer.
        if (-not (Test-Path -LiteralPath $RunInstaller)) { Finish $false "The installer is not there: $RunInstaller" }
        Write-Host "[Fission 180] starting the installer $RunInstaller"
        Start-Process -FilePath $RunInstaller
        Finish $true "The installer was started."
    }
    $source = Join-Path $here "Fission180"
    if (-not (Test-Path (Join-Path $source "InitGui.py"))) {
        Finish $false ("The 'Fission180' folder is not next to this script. Unzip the whole download first " +
            "(right-click the .zip > Extract All), then run install_update.cmd from the unzipped folder.")
    }

    if ($Target -eq "" -and $Quiet) { Finish $false "No -Target given; nothing changed." }
    if ($Target -eq "") {
        # An installed Fission 180 is found by itself; the picker is for the portable build.
        $installed = @(Find-Installed)
        if ($installed.Count -eq 1) {
            Write-Host "[Fission 180] found the installed Fission 180 in $($installed[0])"
            $answer = Read-Host "Update it? (Enter = yes, n = pick another folder)"
            if ($answer -notmatch '^[nN]') { $Target = $installed[0] }
        } elseif ($installed.Count -gt 1) {
            Write-Host "[Fission 180] several Fission 180 installations found; pick the one to update:"
            $installed | ForEach-Object { Write-Host "    $_" }
        }
    }
    if ($Target -eq "") { $Target = Pick-Folder }
    if ($Target -eq "") { Finish $false "No folder picked; nothing changed." }
    # Accept the Mod folder, the bin folder or Mod\Fission180 too, and go up to the Fission 180 folder.
    $Target = $Target.TrimEnd('\', '/')
    $leaf = Split-Path -Leaf $Target
    if ($leaf -eq "Fission180" -and (Split-Path -Leaf (Split-Path -Parent $Target)) -eq "Mod") {
        $Target = Split-Path -Parent $Target
        $leaf = "Mod"
    }
    if ($leaf -eq "Mod" -or $leaf -eq "bin") { $Target = Split-Path -Parent $Target }
    Write-Host "[Fission 180] Fission 180 folder: $Target"

    $mod = Join-Path $Target "Mod"
    $current = Join-Path $mod "Fission180"
    if (-not (Test-Path (Join-Path $Target "bin"))) {
        Finish $false "No 'bin' folder in $Target. Pick the Fission 180 folder itself (it contains 'bin' and 'Mod')."
    }
    if (-not (Test-Path $mod)) { Finish $false "No 'Mod' folder in $Target." }
    $program = Program-Name $Target
    if ($program -eq "") {
        Finish $false ("No Fission180.exe or FreeCAD.exe in $Target\bin. Pick the Fission 180 folder " +
            "(installed: C:\Program Files\Fission180; portable: the unzipped folder).")
    }
    Write-Host "[Fission 180] program: bin\$program"

    $running = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
        try { $_.Path -and $_.Path.StartsWith($Target, [System.StringComparison]::OrdinalIgnoreCase) } catch { $false }
    })
    # Fission 180's own python.exe running alone is the AI connector (fission180_mcp.py): Claude
    # Desktop, Gemini CLI or Claude Code start it and keep it while they run, Fission 180 closed
    # or not. Stopping it is harmless: the AI app starts it again when it is opened again.
    $helpers = @($running | Where-Object { $_.ProcessName -like "python*" })
    if ($running.Count -gt 0 -and $helpers.Count -eq $running.Count) {
        Write-Host ("[Fission 180] Fission 180's AI connector is running ($($helpers.Count) python): an AI " +
            "app you set up (Claude Desktop, Gemini CLI, Claude Code) started it.")
        $answer = "y"
        if (-not $NoPause) {
            $answer = Read-Host "Stop it now? The AI app starts it again next time. (Enter = yes, n = no)"
        }
        if ($answer.Trim().ToLower() -ne "n") {
            foreach ($p in $helpers) {
                try { Stop-Process -Id $p.Id -Force -ErrorAction Stop } catch { }
            }
            Start-Sleep -Seconds 1
            $running = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
                try { $_.Path -and $_.Path.StartsWith($Target, [System.StringComparison]::OrdinalIgnoreCase) } catch { $false }
            })
        }
    }
    if ($running.Count -gt 0) {
        $what = $running[0].ProcessName
        if ($what -like "python*") {
            Finish $false ("Fission 180's AI connector is still running (python): quit Claude Desktop " +
                "(right-click its icon by the clock > Quit), Gemini CLI or Claude Code, then run this again.")
        }
        Finish $false ("Fission 180 is still running ($what). Close it, then run this again.")
    }

    # Folders such as C:\Program Files need administrator rights: ask Windows for them once.
    if (-not ((Can-Write $mod) -and (Can-Write $Target))) {
        if (-not $Elevated -and -not (Is-Admin)) {
            Write-Host "[Fission 180] this folder needs administrator rights; Windows will ask for permission..."
            try { Stop-Transcript | Out-Null } catch { }
            $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$($MyInvocation.MyCommand.Path)`"",
                "-Target", "`"$Target`"", "-Elevated")
            if ($Quiet) {
                # The elevated copy does the work and tells its result by its exit code; this one
                # (not an administrator) starts Fission 180 again, so Fission 180 does not run elevated.
                $argList += @("-Quiet", "-NoDialog")
                try {
                    $child = Start-Process -FilePath "powershell.exe" -ArgumentList $argList -Verb RunAs -Wait -PassThru -WindowStyle Hidden
                } catch {
                    try { Start-Transcript -Path $log -Append | Out-Null } catch { }
                    Finish $false ("Administrator permission was not given. " + $accessHelp)
                }
                try { Start-Transcript -Path $log -Append | Out-Null } catch { }
                if ($child.ExitCode -ne 0) {
                    Finish $false "The update could not be installed (see the log); the old version was put back."
                }
                if ($Restart) { Start-Program $Target $program; Write-Host "[Fission 180] Fission 180 started again" }
                Finish $true "Update installed."
            }
            try {
                Start-Process -FilePath "powershell.exe" -ArgumentList $argList -Verb RunAs -Wait
                Write-Host "[Fission 180] the administrator window has finished; its result is in $log"
                if (-not $NoPause) { Read-Host "Press Enter to close" | Out-Null }
                exit 0
            } catch {
                try { Start-Transcript -Path $log -Append | Out-Null } catch { }
                Finish $false ("Administrator permission was not given. " + $accessHelp)
            }
        }
        Finish $false $accessHelp
    }

    if (Test-Path $current) {
        # Keep a copy of the old version (copying works even when renaming the folder is blocked).
        $backups = Join-Path $Target "Fission180-backups"
        if (-not (Test-Path -LiteralPath $backups)) { New-Item -ItemType Directory -Path $backups -Force | Out-Null }
        $backup = Join-Path $backups (Get-Date -Format "yyyyMMdd-HHmmss")
        Write-Host "[Fission 180] keeping a copy of the old version in $backup ..."
        Copy-Item -LiteralPath $current -Destination $backup -Recurse -Force
        if ($Quiet) {
            # The put-back after a failure trusts this copy: it must be complete (a partly made
            # one would make it delete files that were never saved).
            $have = @(Get-ChildItem -LiteralPath $current -Recurse -Force -File).Count
            $kept = @(Get-ChildItem -LiteralPath $backup -Recurse -Force -File).Count
            if ($have -ne $kept) {
                throw "The copy of the old version is not complete ($kept of $have files), so nothing was changed."
            }
        }
        $script:backup = $backup
        $script:current = $current
    } else {
        New-Item -ItemType Directory -Path $current -Force | Out-Null
    }

    $copied = Copy-Tree $source $current
    $removed = Remove-Leftovers $source $current
    Write-Host "[Fission 180] $copied files installed, $removed old files removed"

    $info = Join-Path $current "fission180\build_info.py"
    if (Test-Path $info) { Get-Content $info | Select-String "COMMIT|DATE" | ForEach-Object { Write-Host "[Fission 180] $_" } }
    if ($Restart -and -not $Elevated) {
        try {
            Start-Program $Target $program
            Write-Host "[Fission 180] Fission 180 started again"
        } catch { Write-Host "[Fission 180] could not start Fission 180 again: $($_.Exception.Message)" }
        Finish $true "Update installed. Fission 180 is starting again."
    }
    Finish $true "Update installed. Start Fission 180 again."
} catch {
    $msg = $_.Exception.Message
    $line = $_.InvocationInfo.ScriptLineNumber
    if ($Quiet -and $script:backup -ne "") {
        # Nobody is watching: put the old version back before telling what went wrong.
        try {
            Write-Host "[Fission 180] putting the old version back from $($script:backup) ..."
            $back = Copy-Tree $script:backup $script:current -Tolerant
            $gone = Remove-Leftovers $script:backup $script:current
            Write-Host "[Fission 180] old version back: $back files restored, $gone new files removed"
        } catch { Write-Host "[Fission 180] could not put the old version back: $($_.Exception.Message)" }
    }
    if ($_.Exception -is [UnauthorizedAccessException] -or $msg -match "denied|being used by another process") {
        Finish $false ("Something went wrong: $msg (line $line). " + $accessHelp)
    }
    Finish $false ("Something went wrong: $msg (line $line)")
}
