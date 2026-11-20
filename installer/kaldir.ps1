# Dubzar'ı kaldırır. Çift tıklanan Kaldir.bat bunu çalıştırır.
# Test için: -InstallRoot, -DesktopDir, -StartMenuDir, -Yes

param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "Dubzar"),
    [string]$DesktopDir = [Environment]::GetFolderPath("Desktop"),
    [string]$StartMenuDir = (Join-Path ([Environment]::GetFolderPath("Programs")) "Dubzar"),
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Ask([string]$question) {
    if ($Yes) { return $true }
    $answer = Read-Host "$question [E/H]"
    return ($answer -match '^[eEyY]')
}

Write-Host ""
Write-Host "=== Dubzar kaldırma ===" -ForegroundColor Yellow
Write-Host ""
if (-not (Ask "Dubzar programı ve kısayolları kaldırılsın mı?")) { Write-Host "İptal edildi."; exit 0 }

# Çalışıyorsa önce kapat (yalnızca bizim ortamımızdaki pythonw/python)
$venvDir = (Join-Path $InstallRoot "venv").ToLower()
Get-Process -Name pythonw, python -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        if ($_.Path -and $_.Path.ToLower().StartsWith($venvDir)) { $_ | Stop-Process -Force }
    } catch { }
}
Start-Sleep -Milliseconds 500

Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $DesktopDir "Dubzar.lnk")
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $StartMenuDir
foreach ($sub in @("app", "venv", "models")) {
    $target = Join-Path $InstallRoot $sub
    if (Test-Path $target) { Remove-Item -Recurse -Force $target }
}
Write-Host "Program ve kısayollar kaldırıldı."

$dataDir = Join-Path $env:APPDATA "Dubzar"
if (Test-Path $dataDir) {
    Write-Host ""
    Write-Host "Ayarlarınız, öğrenilen altyazılar ve günlük dosyası şurada: $dataDir"
    if (Ask "Bunlar da silinsin mi?") { Remove-Item -Recurse -Force $dataDir; Write-Host "Silindi." }
}

$cache = Join-Path $env:USERPROFILE ".cache\huggingface\hub"
$modelDirs = @("models--Helsinki-NLP--opus-mt-tc-big-en-tr", "models--Systran--faster-whisper-tiny") |
    ForEach-Object { Join-Path $cache $_ } | Where-Object { Test-Path $_ }
if ($modelDirs) {
    Write-Host ""
    Write-Host "İndirilen modeller (yaklaşık 550 MB) şurada duruyor: $cache"
    Write-Host "(Başka programlar da aynı modelleri kullanıyor olabilir.)"
    if (Ask "Dubzar'ın indirdiği modeller silinsin mi?") {
        $modelDirs | ForEach-Object { Remove-Item -Recurse -Force $_ }
        Write-Host "Modeller silindi."
    }
}

Write-Host ""
Write-Host "Tamamlandı." -ForegroundColor Green
