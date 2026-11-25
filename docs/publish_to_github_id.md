# Mengunggah paket ke repository GitHub yang sudah dibuat

Repository tujuan: https://github.com/mbagasartomous17/servo-current-anomaly-detection

Paket ini ditujukan untuk repository di atas. Jangan unggah kode ini ke repository `solagreen-dashboard`.

## Cara yang disarankan: Git dari komputer

1. Unduh dan ekstrak ZIP proyek.
2. Buka terminal di folder `servo-current-anomaly-detection`.
3. Jalankan perintah berikut:

```bash
git init -b main
git add .
git commit -m "Initial public research prototype"
git remote add origin https://github.com/mbagasartomous17/servo-current-anomaly-detection.git
git push -u origin main
```

4. Selesaikan autentikasi GitHub melalui mekanisme resmi Git Credential Manager atau GitHub CLI. GitHub tidak lagi menerima kata sandi akun sebagai autentikasi Git HTTPS. Jangan menempelkan Personal Access Token ke chat atau menyimpannya di skrip.
5. Periksa halaman repository dan pastikan folder `src`, `tests`, `docs`, serta berkas proyek tampil.

## Alternatif: Android dengan Termux

Gunakan Termux dari sumber resminya. Setelah ZIP berada di folder Downloads, jalankan:

```bash
pkg update
pkg install git unzip
termux-setup-storage
cd ~/storage/downloads
unzip servo-current-anomaly-detection.zip
cd servo-current-anomaly-detection
git init -b main
git add .
git commit -m "Initial public research prototype"
git remote add origin https://github.com/mbagasartomous17/servo-current-anomaly-detection.git
git push -u origin main
```

Ikuti instruksi autentikasi GitHub yang muncul. Jangan pernah mengirim token akses GitHub kepada orang lain.

## Pemeriksaan sebelum push

- Pastikan tidak ada telemetri mentah, log produksi, program robot, alamat IP, kredensial, atau identitas perusahaan/operator.
- Pastikan kamu berhak memublikasikan kode dan memberikan lisensi MIT.
- File CSV di tutorial dibuat secara sintetis; jangan menggantinya dengan data produksi tanpa izin tertulis.
- Jangan membuat klaim performa industri dari pengujian sintetis.
