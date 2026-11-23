# API tanaman

API memakai model `Plant` dan session login bersama (`/api/auth/login/`).
Kirim cookie `sessionid` pada request berikutnya. User aktif dapat membaca;
hanya staff aktif (`is_staff=True`) dapat menambah, mengubah, atau menghapus.
Guest mendapat 401; user biasa yang mencoba menulis mendapat 403.

| Method | URL | Hasil |
| --- | --- | --- |
| GET | `/api/plants/` | 200, daftar dengan pagination |
| GET | `/api/plants/<id>/` | 200, objek tanaman; 404 jika tidak ada |
| POST | `/api/plants/` | 201, objek tanaman baru (admin) |
| PUT/PATCH | `/api/plants/<id>/` | 200, objek tanaman setelah diubah (admin) |
| DELETE | `/api/plants/<id>/` | 204 tanpa body (admin) |

## Daftar dan filter

Respons daftar berbentuk `{"count": 51, "next": "...", "previous": null,
"results": [...]}`. Maksimal 6 tanaman per halaman; gunakan `?page=2` atau
URL `next`/`previous`. Respons detail/tambah/edit berupa satu objek langsung.

Parameter dapat dikombinasikan:

| Parameter | Nilai |
| --- | --- |
| `q` | Cari nama atau nama ilmiah, tanpa membedakan kapital |
| `category` | `sayur`, `buah`, `herbal`, `hias` |
| `medium` | `soil`, `hydroponic` |
| `sunlight` | `full_sun`, `partial_shade`, `shade` (anggota list tanaman) |
| `space` | `small`, `medium`, `large` |
| `sort` | `name` (default), `name_desc`, `category`, `updated` |
| `page` | Nomor halaman, mulai dari 1 |

Nilai filter yang tidak dikenal diabaikan; sort tidak dikenal kembali ke nama.
Halaman yang tidak tersedia mendapat 404. Contoh:
`/api/plants/?category=sayur&medium=hydroponic&sort=name&page=1`.

## Input admin

Gunakan JSON. Minimal POST: `name`, `category`, `space_needed`.
Field opsional yang tidak dikirim memakai default model (termasuk tanah=true).
Nama harus unik tanpa membedakan kapital. `id`, `perenual_id`, `created_at`,
dan `updated_at` hanya dapat dibaca; input pada field itu diabaikan.

```json
{
  "name": "Tanaman Demo",
  "category": "sayur",
  "space_needed": "small",
  "supports_soil": true,
  "supports_hydroponic": false,
  "sunlight": ["full_sun", "partial_shade"],
  "watering": "Average",
  "care_level": "Low",
  "indoor": null,
  "drought_tolerant": false,
  "temp_min": 18,
  "temp_max": 30
}
```

`watering`: `Minimum`/`Average`/`Frequent` atau string kosong.
`care_level`: `Low`/`Medium`/`High` atau string kosong.
Boolean dikirim sebagai JSON true/false; `indoor` dan `drought_tolerant`
juga menerima null. Angka lingkungan menerima null jika belum diketahui.
`sunlight` harus list pilihan yang valid; list kosong diperbolehkan.

PATCH mempertahankan field yang tidak dikirim. Semua perubahan divalidasi
dengan `PlantForm` yang sama dengan CRUD web, termasuk rentang min/max,
RH 0-100, curah hujan nonnegatif, dan minimal satu media tanam.
Error input mendapat 400 dengan bentuk `{"errors": {"field": ["pesan"]}}`;
error lintas field dapat berada di `__all__` atau `non_field_errors`.

`rainfall_min/max` tetap ekuivalen harian dari curah hujan optimal tahunan,
bukan jadwal/kebutuhan penyiraman. Metadata riset seperti `sources` dan
`humidity_basis` tidak disimpan pada model atau dikirim oleh API ini.

API mengubah database environment aktif; tidak mengubah JSON seed/riset.
DELETE mengikuti relasi model yang sudah ada: panduan tanaman ikut terhapus.
Tidak ada perubahan model/migration atau logika rekomendasi dalam API ini.

## Verifikasi

```bash
python manage.py test apps.plants.tests_api
python manage.py check
```
