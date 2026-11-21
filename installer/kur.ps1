# Dubzar kurulumu. Çift tıklanan Kur.bat bunu çalıştırır.
# Test için: -InstallRoot, -DesktopDir, -StartMenuDir, -SkipPip, -SkipModels, -Yes, -Gpu

param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "Dubzar"),
    [string]$DesktopDir = [Environment]::GetFolderPath("Desktop"),
    [string]$StartMenuDir = (Join-Path ([Environment]::GetFolderPath("Programs")) "Dubzar"),
    [switch]$SkipPip,
    [switch]$SkipModels,
    [switch]$Yes,
    [switch]$Gpu
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Ask([string]$question) {
    if ($Yes) { return $true }
    $answer = Read-Host "$question [E/H]"
    return ($answer -match '^[eEyY]')
}

function Fail([string]$message) {
    Write-Host ""
    Write-Host "KURULUM DURDU: $message" -ForegroundColor Red
    exit 1
}

function Run([string]$exe, [string[]]$arguments, [string]$what) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { Fail "$what başarısız oldu (kod $LASTEXITCODE)." }
}

Write-Host ""
Write-Host "=== Dubzar kurulumu ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "Dubzar, oyunların İngilizce altyazısını/konuşmasını okuyup Türkçe altyazı gösterir."
Write-Host "Her şey bu bilgisayarda çalışır: ses ve ekran görüntüsü hiçbir yere gönderilmez."
Write-Host "Oyunun dosyalarına ya da belleğine dokunmaz."
Write-Host ""
Write-Host "Kurulum sırasında internetten indirilecekler:"
Write-Host "  - Python paketleri (yaklaşık 600 MB)"
Write-Host "  - Konuşma tanıma ve çeviri modelleri (yaklaşık 550 MB)"
Write-Host "Kurulum yeri: $InstallRoot"
Write-Host ""
if (-not (Ask "Devam edilsin mi?")) { Fail "Kurulum iptal edildi." }

# --- 1. Python 3.12 -----------------------------------------------------------------------------------------
function Find-Python {
    try {
        $path = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $path) { return $path.Trim() }
    } catch { }
    try {
        $version = & python -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $version.Trim() -eq "3.12") {
            return (& python -c "import sys; print(sys.executable)").Trim()
        }
    } catch { }
    return $null
}

$python = Find-Python
if (-not $python) {
    Write-Host ""
    Write-Host "Python 3.12 bulunamadı."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget -and (Ask "Python 3.12 şimdi winget ile kurulsun mu?")) {
        & winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        $python = Find-Python
    }
    if (-not $python) {
        Fail "Python 3.12 gerekli. https://www.python.org/downloads/ adresinden 'Python 3.12' kurun (kurulumda 'Add python.exe to PATH' kutusunu işaretleyin), sonra Kur.bat'ı yeniden çalıştırın."
    }
}
Write-Host "Python bulundu: $python"

# --- 2. Uygulama dosyaları ---------------------------------------------------------------------------------
$appSource = Join-Path $here "app"
$appTarget = Join-Path $InstallRoot "app"
if (-not (Test-Path $appSource)) { Fail "'app' klasörü bulunamadı. Zip'i önce tamamen çıkarın, sonra Kur.bat'ı çalıştırın." }
New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
robocopy $appSource $appTarget /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { Fail "Dosyalar kopyalanamadı (robocopy kodu $LASTEXITCODE)." }
$LASTEXITCODE = 0
Write-Host "Uygulama dosyaları kopyalandı."

# --- 3. Python ortamı ve paketler ---------------------------------------------------------------------------
$venv = Join-Path $InstallRoot "venv"
$venvPython = Join-Path $venv "Scripts\python.exe"
$venvPythonW = Join-Path $venv "Scripts\pythonw.exe"
if (-not $SkipPip) {
    if (-not (Test-Path $venvPython)) {
        Write-Host "Python ortamı oluşturuluyor..."
        Run $python @("-m", "venv", $venv) "Python ortamı oluşturma"
    }
    Write-Host "Paketler indiriliyor ve kuruluyor (birkaç dakika sürebilir)..."
    Run $venvPython @("-m", "pip", "install", "--upgrade", "pip") "pip güncelleme"
    Run $venvPython @("-m", "pip", "install", "-r", (Join-Path $appTarget "requirements.txt")) "Paket kurulumu"
}

# --- 3b. Ekran kartı hızlandırması (isteğe bağlı, yalnızca NVIDIA kartı olanlara sorulur) -------------------
# "Yüksek" hız modu yazıyı ekran kartıyla okur (yaklaşık 6 kat hızlı). Kurulamazsa Dubzar işlemciyle çalışmaya devam eder.
$wantGpu = $false
if (-not $SkipPip -and (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    if ($Gpu) { $wantGpu = $true }
    elseif (-not $Yes) {
        Write-Host ""
        Write-Host "NVIDIA ekran kartı bulundu. 'Yüksek' hız modu yazıyı ekran kartıyla okur: altyazı daha erken çıkar,"
        Write-Host "ama ekran kartını ve işlemciyi daha fazla kullanır (oyun başka cihazdaysa, örn. konsol, önerilir)."
        Write-Host "Bunun için ek paketler indirilir (yaklaşık 1,5 GB)."
        $wantGpu = Ask "Ekran kartı hızlandırması kurulsun mu?"
    }
}
if ($wantGpu) {
    Write-Host "Ekran kartı paketleri indiriliyor..."
    & $venvPython -m pip uninstall -y onnxruntime
    & $venvPython -m pip install onnxruntime-gpu==1.23.2 nvidia-cudnn-cu12 nvidia-cublas-cu12 nvidia-cuda-runtime-cu12 nvidia-cufft-cu12 nvidia-curand-cu12
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Ekran kartı hızlandırması kurulamadı; 'Yüksek' mod işlemciyle çalışacak. (Dubzar yine de çalışır.)" -ForegroundColor Yellow
        & $venvPython -m pip install onnxruntime==1.32.0
        $LASTEXITCODE = 0
    } else {
        Write-Host "Ekran kartı hızlandırması kuruldu. Ayarlar panelinde 'Hız modu'nu 'Yüksek' yapın."
    }
}

# --- 4. Modeller ---------------------------------------------------------------------------------------------
if (-not $SkipModels) {
    Write-Host ""
    Write-Host "Şimdi modeller indirilecek (yaklaşık 550 MB): konuşma tanıma (Whisper tiny, MIT lisanslı) ve"
    Write-Host "çeviri (Helsinki-NLP OPUS-MT, CC-BY-4.0). Bunlar bu bilgisayarda saklanır."
    if (-not (Ask "Modeller indirilsin mi?")) { Fail "Modeller olmadan Dubzar çalışamaz. İstediğinizde Kur.bat'ı yeniden çalıştırın." }
    Push-Location $appTarget
    try { Run $venvPython @("-m", "dubzar", "setup", "--allow-download") "Model indirme" } finally { Pop-Location }
}

# --- 5. Kısayollar (başlatma simgesi: Dubzar'ın D'si) -----------------------------------------------------
function New-Shortcut([string]$path, [string]$target, [string]$arguments, [string]$description) {
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($path)
    $link.TargetPath = $target
    $link.Arguments = $arguments
    $link.WorkingDirectory = $appTarget
    $link.IconLocation = (Join-Path $appTarget "dubzar\ui\dubzar.ico") + ",0"
    $link.Description = $description
    $link.Save()
}

New-Item -ItemType Directory -Force -Path $DesktopDir, $StartMenuDir | Out-Null
New-Shortcut (Join-Path $DesktopDir "Dubzar.lnk") $venvPythonW "-m dubzar run" "Dubzar: oyunlara Türkçe altyazı"
New-Shortcut (Join-Path $StartMenuDir "Dubzar.lnk") $venvPythonW "-m dubzar run" "Dubzar: oyunlara Türkçe altyazı"
New-Shortcut (Join-Path $StartMenuDir "Dubzar (hata ayiklama).lnk") $venvPython "-m dubzar run --debug" "Dubzar, konsol penceresiyle (sorun olursa)"
Write-Host "Kısayollar oluşturuldu (Masaüstü ve Başlat menüsü)."

Write-Host ""
Write-Host "=== Kurulum tamamlandı ===" -ForegroundColor Green
Write-Host ""
Write-Host "Nasıl kullanılır:"
Write-Host "  1. Masaüstündeki Dubzar simgesine çift tıklayın (ekranda kısa bir 'Dubzar' animasyonu çıkar)."
Write-Host "  2. Oyunu açın. Oyunu 'tam ekran' ya da 'pencereli tam ekran' çalıştırabilirsiniz."
Write-Host "  3. Ctrl+Shift+D ile ayarları açın (boyut, konum, renk)."
Write-Host "  4. Çıkmak için ayarlar panelindeki 'Dubzar''dan çık' bağlantısına tıklayın."
Write-Host ""
Write-Host "Sorun olursa: Başlat menüsünden 'Dubzar (hata ayiklama)' ile açıp çıktıyı gönderin,"
Write-Host "ya da $env:APPDATA\Dubzar\dubzar.log dosyasını paylaşın."
