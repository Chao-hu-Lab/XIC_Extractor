# ==============================================================================
# 01_extract_xic.ps1  -  Extract MS1 XIC apex (RT + 15G-smoothed intensity)
#                        and MS2 neutral-loss confirmation from Thermo .raw files.
#
# Config : config\settings.csv   (data_dir, dll_dir, smoothing params)
#          config\targets.csv    (per-target mz, RT window, ppm, neutral_loss)
# Output : output\xic_results.csv
#
# Usage  : powershell -ExecutionPolicy Bypass -File .\scripts\01_extract_xic.ps1
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---- Paths -------------------------------------------------------------------
$root      = Resolve-Path "$PSScriptRoot\.."
$configDir = Join-Path $root "config"
$outputDir = Join-Path $root "output"
if (-not (Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir | Out-Null }

# ---- Read settings.csv -------------------------------------------------------
$cfg = @{}
Import-Csv (Join-Path $configDir "settings.csv") | ForEach-Object { $cfg[$_.key] = $_.value }

$DataDir      = $cfg['data_dir']
$DllDir       = $cfg['dll_dir']
$SmoothSigma  = [double]$cfg['smooth_sigma']
$SmoothPoints = [int]$cfg['smooth_points']
$OutputCsv    = Join-Path $outputDir "xic_results.csv"

# ---- Read targets.csv --------------------------------------------------------
$targets    = @(Import-Csv (Join-Path $configDir "targets.csv"))
$nlTargets  = @($targets | Where-Object { $_.neutral_loss_da -ne '' })

# ---- Load DLLs ---------------------------------------------------------------
Add-Type -Path (Join-Path $DllDir "ThermoFisher.CommonCore.Data.dll")
Add-Type -Path (Join-Path $DllDir "ThermoFisher.CommonCore.RawFileReader.dll")

# ---- 15-point Gaussian smooth ------------------------------------------------
# Approximates Xcalibur "SM: 15G" display smoothing (sigma=3 matches NL values).
function Invoke-GaussianSmooth {
    param([double[]]$Data, [int]$Points, [double]$Sigma)
    $half = [int]($Points / 2)
    $weights = foreach ($k in -$half..$half) {
        [Math]::Exp(-($k * $k) / (2 * $Sigma * $Sigma))
    }
    $wSum = 0.0; foreach ($w in $weights) { $wSum += $w }
    $weights = foreach ($w in $weights) { $w / $wSum }

    $result = [double[]]::new($Data.Length)
    for ($i = 0; $i -lt $Data.Length; $i++) {
        $v = 0.0; $wt = 0.0
        for ($k = 0; $k -lt $Points; $k++) {
            $idx = $i - $half + $k
            if ($idx -ge 0 -and $idx -lt $Data.Length) {
                $v  += $Data[$idx] * $weights[$k]
                $wt += $weights[$k]
            }
        }
        $result[$i] = if ($wt -gt 0) { $v / $wt } else { 0.0 }
    }
    return $result
}

# ---- MS1 XIC apex extraction -------------------------------------------------
# Returns @{ RT = double; Intensity = double }
# RT = NaN and Intensity = 0 when no signal is detected.
function Get-MS1Apex {
    param(
        $RawFile,
        [double]$Mz, [double]$RtMin, [double]$RtMax,
        [double]$PpmTol, [int]$SmoothPts, [double]$SmoothSig
    )
    $tol   = $Mz * $PpmTol / 1e6
    $sscan = $RawFile.ScanNumberFromRetentionTime($RtMin)
    $escan = $RawFile.ScanNumberFromRetentionTime($RtMax)

    $ts = [ThermoFisher.CommonCore.Data.Business.ChromatogramTraceSettings]::new(
              [ThermoFisher.CommonCore.Data.Business.TraceType]::MassRange)
    $ts.MassRanges = [ThermoFisher.CommonCore.Data.Business.Range[]]@(
        [ThermoFisher.CommonCore.Data.Business.Range]::new($Mz - $tol, $Mz + $tol))
    $ts.Filter = "ms"

    $cd    = $RawFile.GetChromatogramData(
                 [ThermoFisher.CommonCore.Data.Interfaces.IChromatogramSettings[]]@($ts),
                 $sscan, $escan)
    $pos   = $cd.PositionsArray[0]
    $inten = $cd.IntensitiesArray[0]

    if ($null -eq $inten -or $inten.Length -eq 0) {
        return @{ RT = [double]::NaN; Intensity = 0.0 }
    }

    $smoothed = Invoke-GaussianSmooth -Data $inten -Points $SmoothPts -Sigma $SmoothSig

    $maxI = 0.0; $maxRT = [double]::NaN
    for ($i = 0; $i -lt $smoothed.Length; $i++) {
        if ($smoothed[$i] -gt $maxI) { $maxI = $smoothed[$i]; $maxRT = $pos[$i] }
    }
    return @{ RT = $maxRT; Intensity = $maxI }
}

# ---- MS2 neutral-loss confirmation -------------------------------------------
# Returns "OK"          : precursor triggered, NL product found within nl_ppm_warn
#         "WARN_X.Xppm" : found between nl_ppm_warn and nl_ppm_max (flag for review)
#         "ND"          : not triggered, or NL product beyond nl_ppm_max
function Test-NeutralLoss {
    param(
        $RawFile,
        [double]$PrecursorMz, [double]$RtMin, [double]$RtMax,
        [double]$NeutralLoss,
        [double]$NlPpmWarn, [double]$NlPpmMax
    )
    # DDA stores precursor mass with lower accuracy than Orbitrap MS1 measurement.
    # Use a fixed Da window matching the typical quadrupole isolation width (±0.5 Da),
    # not ppm, to avoid rejecting valid scans due to DDA mass-recording imprecision.
    $preTol    = 0.5
    $sscan     = $RawFile.ScanNumberFromRetentionTime($RtMin)
    $escan     = $RawFile.ScanNumberFromRetentionTime($RtMax)
    $bestPpm   = [double]::MaxValue
    $triggered = $false

    for ($s = $sscan; $s -le $escan; $s++) {
        $filter = $RawFile.GetFilterForScanNumber($s)
        if ($filter.MSOrder -ne [ThermoFisher.CommonCore.Data.FilterEnums.MSOrderType]::Ms2) { continue }

        # Get precursor m/z from Reactions (filter.ToString() returns class name, not text)
        $rxns = $filter.Filter.Reactions
        if ($null -eq $rxns -or $rxns.Count -eq 0) { continue }
        $preMz = $rxns[0].PrecursorMass
        if ([Math]::Abs($preMz - $PrecursorMz) -gt $preTol) { continue }
        $triggered = $true

        # Use theoretical target mz (not DDA-recorded preMz) to compute expected product,
        # because DDA precursor mass has low accuracy while the product ion search needs
        # to match the Orbitrap-measured fragment.
        $expectedProd = $PrecursorMz - $NeutralLoss
        $searchTol    = $expectedProd * $NlPpmMax / 1e6

        $data = $RawFile.GetSimplifiedScan($s)
        for ($i = 0; $i -lt $data.Masses.Length; $i++) {
            $diff = [Math]::Abs($data.Masses[$i] - $expectedProd)
            if ($diff -le $searchTol) {
                $ppm = $diff / $expectedProd * 1e6
                if ($ppm -lt $bestPpm) { $bestPpm = $ppm }
            }
        }
    }

    if (-not $triggered)          { return "ND" }
    if ($bestPpm -gt $NlPpmMax)   { return "ND" }
    if ($bestPpm -gt $NlPpmWarn)  { return ("WARN_{0:F1}ppm" -f $bestPpm) }
    return "OK"
}

# ---- Main loop ---------------------------------------------------------------
$rawFiles = Get-ChildItem -Path $DataDir -Filter "*.raw" | Sort-Object Name
$total    = $rawFiles.Count
$results  = [System.Collections.Generic.List[object]]::new()

Write-Host "Data dir   : $DataDir"
Write-Host "Output     : $OutputCsv"
Write-Host "Targets    : $($targets.Count)  with NL: $($nlTargets.Count)"
Write-Host "Smoothing  : ${SmoothPoints}G  sigma=$SmoothSigma"
Write-Host "Files      : $total"
Write-Host ""

$i = 0
foreach ($file in $rawFiles) {
    $i++
    Write-Host ("  [{0,3}/{1}] {2}" -f $i, $total, $file.Name)

    $rawFile = $null
    try {
        $rawFile = [ThermoFisher.CommonCore.RawFileReader.RawFileReaderAdapter]::FileFactory($file.FullName)
        $rawFile.SelectInstrument([ThermoFisher.CommonCore.Data.Business.Device]::MS, 1)

        $row = [ordered]@{ SampleName = [IO.Path]::GetFileNameWithoutExtension($file.Name) }

        foreach ($t in $targets) {
            $apex = Get-MS1Apex -RawFile $rawFile `
                -Mz ([double]$t.mz) -RtMin ([double]$t.rt_min) -RtMax ([double]$t.rt_max) `
                -PpmTol ([double]$t.ppm_tol) -SmoothPts $SmoothPoints -SmoothSig $SmoothSigma
            $row["$($t.label)_RT"]  = if ([double]::IsNaN($apex.RT)) { "ND" } else { [math]::Round($apex.RT, 4) }
            $row["$($t.label)_Int"] = if ($apex.Intensity -le 0)     { "ND" } else { [math]::Round($apex.Intensity, 0) }

            if ($t.neutral_loss_da -ne '') {
                $row["$($t.label)_NL"] = Test-NeutralLoss -RawFile $rawFile `
                    -PrecursorMz ([double]$t.mz) -RtMin ([double]$t.rt_min) -RtMax ([double]$t.rt_max) `
                    -NeutralLoss ([double]$t.neutral_loss_da) `
                    -NlPpmWarn ([double]$t.nl_ppm_warn) -NlPpmMax ([double]$t.nl_ppm_max)
            }
        }

        $results.Add([PSCustomObject]$row)
    }
    catch {
        Write-Warning ("    Error: {0}" -f $_.Exception.Message)
        $errRow = [ordered]@{ SampleName = [IO.Path]::GetFileNameWithoutExtension($file.Name) }
        foreach ($t in $targets) {
            $errRow["$($t.label)_RT"] = "ERROR"
            $errRow["$($t.label)_Int"] = "ERROR"
            if ($t.neutral_loss_da -ne '') { $errRow["$($t.label)_NL"] = "ERROR" }
        }
        $results.Add([PSCustomObject]$errRow)
    }
    finally {
        if ($null -ne $rawFile) { $rawFile.Dispose() }
    }
}

$results | Export-Csv -Path $OutputCsv -NoTypeInformation -Encoding UTF8
Write-Host ""
Write-Host "Done -> $OutputCsv"
