# SepsiCore

## Türkçe

SepsiCore, acil servis ve yoğun bakım için hazırlanmış Türkçe/İngilizce arayüzlü bir klinik erken uyarı ve sepsis risk değerlendirme prototipidir. Tanı koymaz; vital bulgular ve laboratuvar değerleri üzerinden risk skoru, klinik uyum skoru, gerekçeler ve önerilen aksiyonları gösterir.

### Klasör Yapısı

```text
SepsiCore/
  main.py              Uygulama giriş noktası
  sepsicore/           Ana Python paketi
  assets/              Ses ve yazı tipi dosyaları
  data/                Demo ve örnek CSV verileri
  docs/                Proje görselleri/belgeleri
  notes/               Çalışma sırasında oluşan doktor notları
  records/             Çalışma sırasında oluşan hasta kayıtları
  reports/             Çalışma sırasında oluşan PDF/TXT raporlar
  run_windows.bat      Windows hızlı başlatıcı
  run_linux.sh         Linux/macOS hızlı başlatıcı
  build_windows.bat    Windows masaüstü build scripti
  build_linux.sh       Linux/macOS masaüstü build scripti
```

### Çalıştırma

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Alternatifler:

```bash
python -m sepsicore
run_windows.bat
```

Linux/macOS için:

```bash
source .venv/bin/activate
./run_linux.sh
```

`run_windows.bat` ve `run_linux.sh` sadece uygulamayı hızlı başlatan yardımcı dosyalardır.

### Masaüstü Build

Windows:

```bash
build_windows.bat
```

Komut tamamlanınca çıktı burada oluşur:

```text
dist/SepsiCore/SepsiCore.exe
```

Linux/macOS:

```bash
./build_linux.sh
```

---

## English

SepsiCore is a Turkish/English clinical early warning and sepsis risk assessment prototype for emergency and intensive care settings. It does not diagnose; it shows risk score, clinical match score, supporting findings, and recommended actions based on vital signs and lab values.

### Project Structure

```text
SepsiCore/
  main.py              Application entry point
  sepsicore/           Main Python package
  assets/              Sound and font assets
  data/                Demo and sample CSV data
  docs/                Project images/documents
  notes/               Runtime physician notes
  records/             Runtime patient record outputs
  reports/             Runtime PDF/TXT reports
  run_windows.bat      Windows quick launcher
  run_linux.sh         Linux/macOS quick launcher
  build_windows.bat    Windows desktop build script
  build_linux.sh       Linux/macOS desktop build script
```

### Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Alternatives:

```bash
python -m sepsicore
run_windows.bat
```

For Linux/macOS:

```bash
source .venv/bin/activate
./run_linux.sh
```

`run_windows.bat` and `run_linux.sh` are small launcher helpers.

### Desktop Build

Windows:

```bash
build_windows.bat
```

Output:

```text
dist/SepsiCore/SepsiCore.exe
```

Linux/macOS:

```bash
./build_linux.sh
```
