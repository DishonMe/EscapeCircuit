<#
================================================================================
 run_tests.ps1 — run the full EscapeCircuit test suite (backend + frontend)
 with coverage, stream the console output, and print a designed summary.
 Windows companion to run_tests.sh.

   .\run_tests.ps1            run everything
   .\run_tests.ps1 backend    backend (pytest + coverage) only
   .\run_tests.ps1 frontend   frontend (vitest + types + lint) only

 Exit code is non-zero if any step fails.
================================================================================
#>
param(
  [ValidateSet('all', 'backend', 'frontend')]
  [string]$Mode = 'all'
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Pick a Python launcher that exists on this machine.
$Py = 'python'
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  if (Get-Command py -ErrorAction SilentlyContinue) { $Py = 'py' }
}

function Banner($title) {
  Write-Host ''
  Write-Host ('+' + ('-' * 68) + '+') -ForegroundColor Cyan
  Write-Host ('| ' + $title.PadRight(66) + '|') -ForegroundColor Cyan
  Write-Host ('+' + ('-' * 68) + '+') -ForegroundColor Cyan
}

function Human($sec) {
  if ($sec -ge 60) { '{0}m {1:d2}s' -f [int]($sec / 60), ($sec % 60) } else { "${sec}s" }
}

# ---- result holders ----------------------------------------------------------
$res = [ordered]@{
  BackendRun = $false; BackendOk = $false; BackendPass = '-'; BackendFail = '0'; BackendCov = 'n/a'; BackendTime = 0
  FrontendRun = $false; FrontendOk = $false; FrontendPass = '-'; FrontendCov = 'n/a'; FrontendTime = 0
  TypeRun = $false; TypeOk = $false
  LintRun = $false; LintOk = $false
}

function Invoke-Step {
  # Runs a script block in a directory, streams + captures output, returns @{ Ok; Text; Seconds }
  param([string]$Dir, [scriptblock]$Cmd)
  $start = Get-Date
  Push-Location $Dir
  $captured = $null
  try {
    # Tee-Object -Variable captures every line into $captured while Out-Host
    # still streams it live to the console (assigning to a var would swallow it).
    & $Cmd 2>&1 | Tee-Object -Variable captured | Out-Host
    $ok = ($LASTEXITCODE -eq 0)
  } finally { Pop-Location }
  $secs = [int]((Get-Date) - $start).TotalSeconds
  $text = if ($captured) { ($captured | ForEach-Object { "$_" }) -join "`n" } else { '' }
  return @{ Ok = $ok; Text = $text; Seconds = $secs }
}

function Match1($text, $pattern) {
  $m = [regex]::Match($text, $pattern)
  if ($m.Success) { return $m.Groups[1].Value } else { return $null }
}

function Draw-Bar($pct, $done, $name) {
  if ($pct -gt 100) { $pct = 100 }
  if ($pct -lt 0) { $pct = 0 }
  $width = 28
  $filled = [int]($pct * $width / 100)
  $bar = ('#' * $filled) + ('.' * ($width - $filled))
  if (-not $name) { $name = '' }
  $short = if ($name.Length -gt 38) { $name.Substring(0, 38) } else { $name.PadRight(38) }
  Write-Host ("`r  running [{0}] {1,3}%  {2,4}  {3}" -f $bar, $pct, $done, $short) -NoNewline -ForegroundColor Cyan
}

function Invoke-PytestWithBar($Dir, $PyExe, $PyArgs, $Log) {
  # Runs pytest into a log file and shows a live progress bar (no per-test spam).
  $start = Get-Date
  $errLog = "$Log.err"
  $proc = Start-Process -FilePath $PyExe -ArgumentList $PyArgs -WorkingDirectory $Dir `
    -RedirectStandardOutput $Log -RedirectStandardError $errLog -NoNewWindow -PassThru
  $done = 0
  while (-not $proc.HasExited) {
    Start-Sleep -Milliseconds 250
    $txt = Get-Content $Log -Raw -ErrorAction SilentlyContinue
    if ($txt) {
      $pcts = [regex]::Matches($txt, '\[\s*(\d+)%\]')
      $pct = if ($pcts.Count) { [int]$pcts[$pcts.Count - 1].Groups[1].Value } else { 0 }
      $done = ([regex]::Matches($txt, '(?m)\[\s*\d+%\]\s*$')).Count
      $names = [regex]::Matches($txt, '::([\w\[\]\.\-]+)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)')
      $name = if ($names.Count) { $names[$names.Count - 1].Groups[1].Value } else { 'collecting...' }
      Draw-Bar $pct $done $name
    }
  }
  Draw-Bar 100 $done 'done'
  Write-Host ''
  # Fold stderr into the log so parsing + the readable dump see everything.
  if (Test-Path $errLog) { Get-Content $errLog -ErrorAction SilentlyContinue | Add-Content $Log }
  $secs = [int]((Get-Date) - $start).TotalSeconds
  return @{ Ok = ($proc.ExitCode -eq 0); Seconds = $secs }
}

# ------------------------------------------------------------------ backend ---
function Run-Backend {
  $res.BackendRun = $true
  Banner 'BACKEND  -  pytest + coverage'
  $log = Join-Path ([System.IO.Path]::GetTempPath()) ("ec_backend_{0}.log" -f $PID)
  $r = Invoke-PytestWithBar (Join-Path $Root 'src') $Py @('-m', 'pytest', '--cov=Backend', '--cov-report=term-missing') $log
  $res.BackendOk = $r.Ok
  $res.BackendTime = $r.Seconds
  $text = Get-Content $log -Raw -ErrorAction SilentlyContinue
  if (-not $text) { $text = '' }
  # Print the parts worth reading (coverage table, warnings, summary, any
  # failures) — the per-test lines are already represented by the bar.
  ($text -split "`r?`n") |
    Where-Object { $_ -notmatch '::.*(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s*\[\s*\d+%\]\s*$' } |
    ForEach-Object { Write-Host $_ }
  $summaryLine = ($text -split "`r?`n" | Where-Object { $_ -match 'passed|failed|error' } | Select-Object -Last 1)
  $p = Match1 $summaryLine '(\d+) passed'; if ($p) { $res.BackendPass = $p } else { $res.BackendPass = '0' }
  $f = Match1 $summaryLine '(\d+) failed'; if ($f) { $res.BackendFail = $f } else { $res.BackendFail = '0' }
  $totalLine = ($text -split "`r?`n" | Where-Object { $_ -match '^TOTAL' } | Select-Object -Last 1)
  $c = Match1 $totalLine '(\d+%)'; if ($c) { $res.BackendCov = $c }
  Remove-Item $log, "$log.err" -ErrorAction SilentlyContinue
}

# ----------------------------------------------------------------- frontend ---
function Run-Frontend {
  $app = Join-Path $Root 'apps/nextjs-app'

  Banner 'FRONTEND  -  vitest'
  $res.FrontendRun = $true
  $hasCov = Test-Path (Join-Path $app 'node_modules/@vitest/coverage-v8')
  if ($hasCov) {
    $r = Invoke-Step $app { yarn test --coverage }
  } else {
    Write-Host '(coverage provider @vitest/coverage-v8 not installed - running without coverage)' -ForegroundColor DarkGray
    $r = Invoke-Step $app { yarn test }
  }
  $res.FrontendOk = $r.Ok
  $res.FrontendTime = $r.Seconds
  # Match the vitest "Tests  N passed" line specifically (case-sensitive, and
  # requiring "passed" so the trailing "Duration ... tests 11ms" line is ignored).
  $p = Match1 $r.Text '(?m)Tests\s+(\d+) passed'; if ($p) { $res.FrontendPass = $p } else { $res.FrontendPass = '0' }
  $allLine = ($r.Text -split "`n" | Where-Object { $_ -match '^All files' } | Select-Object -Last 1)
  if ($allLine) { $cov = ($allLine -split '\|')[1].Trim(); if ($cov) { $res.FrontendCov = "$cov%" } }

  Banner 'FRONTEND  -  type-check'
  $res.TypeRun = $true
  $res.TypeOk = (Invoke-Step $app { yarn check-types }).Ok

  Banner 'FRONTEND  -  lint'
  $res.LintRun = $true
  $res.LintOk = (Invoke-Step $app { yarn lint }).Ok
}

switch ($Mode) {
  'backend'  { Run-Backend }
  'frontend' { Run-Frontend }
  'all'      { Run-Backend; Run-Frontend }
}

# -------------------------------------------------------------------- summary --
function Row($label, $state, $detail) {
  # $state: $true / $false / $null (skip)
  Write-Host ('  | ' + $label.PadRight(26)) -NoNewline -ForegroundColor Blue
  if ($null -eq $state)   { Write-Host ' --   ' -NoNewline -ForegroundColor DarkGray }
  elseif ($state)         { Write-Host ' [PASS]' -NoNewline -ForegroundColor Green }
  else                    { Write-Host ' [FAIL]' -NoNewline -ForegroundColor Red }
  Write-Host ('   ' + $detail) -ForegroundColor DarkGray
}

Write-Host ''
Write-Host ('=============================== SUMMARY ' + ('=' * 31)) -ForegroundColor Blue

if ($res.BackendRun) {
  Row 'Backend  (pytest)' $res.BackendOk ("{0} passed - {1} failed - cov {2} - {3}" -f $res.BackendPass, $res.BackendFail, $res.BackendCov, (Human $res.BackendTime))
}
if ($res.FrontendRun) {
  Row 'Frontend (vitest)'   $res.FrontendOk ("{0} passed - {1}" -f $res.FrontendPass, (Human $res.FrontendTime))
  Row 'Frontend type-check' $res.TypeOk ''
  Row 'Frontend lint'       $res.LintOk ''
}

$overallFail = $false
foreach ($pair in @(@($res.BackendRun, $res.BackendOk), @($res.FrontendRun, $res.FrontendOk), @($res.TypeRun, $res.TypeOk), @($res.LintRun, $res.LintOk))) {
  if ($pair[0] -and -not $pair[1]) { $overallFail = $true }
}

Write-Host ('-' * 70) -ForegroundColor Blue
if (-not $overallFail) {
  $parts = @()
  if ($res.BackendRun)  { $parts += "backend ($($res.BackendPass))" }
  if ($res.FrontendRun) { $parts += "frontend ($($res.FrontendPass))"; $parts += 'types'; $parts += 'lint' }
  if ($res.BackendRun -and $res.BackendCov -ne 'n/a') { $parts += "cov $($res.BackendCov)" }
  Write-Host '   ALL GREEN' -ForegroundColor Green -NoNewline
  Write-Host (' — ' + ($parts -join ' · '))
  Write-Host ''
  exit 0
} else {
  Write-Host '   SOME CHECKS FAILED' -ForegroundColor Red -NoNewline
  Write-Host ' - see the console output above.'
  Write-Host ''
  exit 1
}
