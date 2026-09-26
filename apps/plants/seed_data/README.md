# Seeding tanaman: cari, review, lalu impor

Command ini memiliki dua mode terpisah. Pemanggilan tanpa mode, termasuk
`seed_plants --limit 10` yang lama, akan ditolak agar tidak langsung mengimpor
hasil pertama. Jalankan command dari root project `NANEM` dengan environment aktif.

## 1. Siapkan daftar pencarian

Edit `apps/plants/seed_data/plant_seed_names.json`:

- `nama_id`: nama Indonesia untuk ditampilkan; harus unik dalam daftar.
- `query`: kata pencarian Perenual, sebaiknya nama ilmiah yang sudah diverifikasi.
- `category`: `sayur`, `buah`, `herbal`, atau `hias`.

Jangan menebak kecocokan hanya dari urutan hasil pencarian API.

## 2. Ambil kandidat ke file lokal

Pastikan `PERENUAL_API_KEY` terbaca dari environment atau `.env`, lalu:

```bash
python manage.py seed_plants --fetch --limit 10
```

Ini membaca **10 entri pertama** dari daftar, bukan 10 entri baru setelah cache
dilewati. Hilangkan `--limit` untuk memproses seluruh daftar.

Hasil disimpan ke `apps/plants/seed_data/plant_candidates.json`. File baru dibuat
saat fetch; tidak perlu membuatnya sendiri. Database tanaman tidak diubah.
Setiap pencarian baru menggunakan satu request API, dengan jeda 0,75 detik.

Setiap respons fetch menampilkan kuota dari header, misalnya
`Perenual HTTP 200 | Sisa kuota: 91 / 100 request (menurut respons ini)`.
Angka tersebut adalah sisa kuota pada saat respons diterima, bukan jumlah yang
sudah terpakai. Header yang tidak disediakan ditampilkan sebagai `tidak tersedia`.
Tidak ada request tambahan untuk memeriksa kuota; entri yang memakai cache dan
mode impor offline tidak menampilkan pembaruan kuota.

Semua kandidat pada **halaman pertama** respons disimpan beserta data yang
diberikan API dan metadata pagination. Halaman berikutnya dan endpoint detail
tidak diambil otomatis. Jika `pagination.last_page` lebih dari 1, kandidat di file
belum mencakup seluruh hasil pencarian; persempit query jika belum ada yang tepat.
Deskripsi atau sunlight yang tidak tersedia tetap kosong saat diimpor.

Progres disimpan setelah setiap respons. Saat command diulang:

- Query yang sama dan sudah selesai memakai cache, termasuk hasil kosong.
- Query yang berubah dicari ulang; pilihan ID sebelumnya dibatalkan.
- Koneksi gagal/timeout atau proses terputus dapat dicoba lagi dari entri yang
  belum selesai, tanpa mengulang pencarian yang sudah tersimpan.
- Error auth/rate limit menghentikan fetch. Perbaiki akses/tunggu kuota sebelum
  mencoba lagi; command tidak melakukan retry otomatis.

Untuk sengaja mencari ulang 10 entri pertama:

```bash
python manage.py seed_plants --fetch --refresh --limit 10
```

`--refresh` mengganti kandidat dan mengosongkan pilihan lama untuk entri yang
diproses, sehingga perlu review ulang. Cache entri lain tetap disimpan.

## 3. Pilih kandidat di file lokal

Buka `plant_candidates.json` setelah fetch selesai. Periksa nama ilmiah, nama
umum, dan data kandidat lain. Edit hanya `selected_perenual_id` untuk pilihan.

Contoh bentuk record (ID dan nama kandidat di bawah **hanya ilustrasi**):

```json
{
  "nama_id": "Nama tanaman lokal",
  "query": "kata pencarian",
  "category": "sayur",
  "source_url": "https://perenual.com/api/v2/species-list",
  "status": "needs_review",
  "fetched_at": "2026-01-01T00:00:00+00:00",
  "candidates": [
    {"id": 123, "common_name": "Nama dari API", "scientific_name": ["Nama ilmiah"]}
  ],
  "selected_perenual_id": 123,
  "pagination": {"current_page": 1, "last_page": 1}
}
```

Gunakan ID dari kandidat asli sebagai angka (tanpa tanda kutip). Biarkan `null`
jika belum yakin atau tidak ada yang cocok. Jangan mengarang ID atau mengubah
data kandidat, query, maupun status di file hasil; ubah query di file seed, lalu
fetch ulang. Jangan edit file kandidat saat fetch sedang berjalan, dan jangan
menjalankan dua proses fetch/import sekaligus.

`needs_review` berarti hasil fetch tersedia; pilihan ditentukan oleh
`selected_perenual_id`, bukan dengan mengubah status. `no_results` berarti
pencarian selesai tanpa hasil; `pending`/`failed` akan dicoba lagi saat fetch.

## 4. Impor pilihan tanpa request API

```bash
python manage.py seed_plants --import-selected
```

Mode ini tidak memerlukan API key. Hanya pilihan untuk entri yang masih ada pada
daftar seed yang diproses. Nama dan kategori menggunakan daftar seed terkini.
Pilihan dari query yang sudah berubah, ID yang tidak ada pada kandidat, dan satu
ID yang dipilih untuk beberapa nama akan ditolak sebelum menulis database.

Record cocok berdasarkan ID Perenual atau nama akan diperbarui, bukan ditambah
duplikat. Jika dua record database berbeda cocok, impor dihentikan agar konflik
diselesaikan manual. Seluruh batch impor menggunakan transaksi: jika gagal,
perubahan batch itu dibatalkan. Nilai iklim, ruang, dan dukungan media pada record
lama tidak ditimpa. Field API yang kosong dapat mengosongkan field API lama.

Tanaman yang sudah masuk dari command versi sebelumnya tidak otomatis dihapus
atau diperiksa ulang. Review record tersebut juga; memilih `null` tidak menghapus
data tanaman yang sebelumnya sudah tersimpan.

Kedua mode mencetak laporan dan mengganti `seed_report.txt` dengan laporan
terbaru. File ini bukan sumber progres; sumber progres adalah file kandidat.
Simpan salinan file kandidat/database sebelum perubahan besar bila perlu.

## Test offline

Tanpa API sungguhan, tanpa membuat database test, dan tanpa migration:

```bash
DJANGO_SETTINGS_MODULE=config.settings python - <<'PY'
import django
import unittest

django.setup()
suite = unittest.defaultTestLoader.loadTestsFromNames([
    "apps.plants.test_seeding",
    "apps.plants.test_seed_workflow",
])
result = unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(not result.wasSuccessful())
PY
```
