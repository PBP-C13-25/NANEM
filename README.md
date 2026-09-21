# Proyek-Tengah-Semester

## NANEM

**Nama aplikasi:** NANEM

**Anggota:**

- Jihan Nabiilah Permata Sukma - 2506549026
- Muhammad Hafidz Muazzam - 2506621812
- Zhafira Richas - 2506540941
- Muhammad Eshan Bobby Bhaskara - 2506546333
- Johannes Nichola Simatupang - 2406495930

---

### DESKRIPSI APLIKASI

**NANEM** merupakan aplikasi yang memberikan rekomendasi tanaman berdasarkan kondisi lahan dan lingkungan pengguna. Aplikasi ini membantu pengguna mengetahui tanaman yang sesuai dengan kondisi tertentu sehingga pemanfaatan lahan dapat dilakukan secara lebih optimal.

#### Siapa pelanggan?

Target pengguna NANEM adalah:

- Masyarakat yang ingin mulai bercocok tanam.
- Pemilik lahan skala kecil.
- Petani atau pengguna yang ingin mengetahui tanaman yang sesuai dengan kondisi lahannya.
- Pemula yang belum mengetahui tanaman yang cocok dengan kondisi lingkungan tertentu.
- Pengguna yang tertarik pada urban farming dengan media tanam terbatas, termasuk hidroponik.

#### Apa solusi yang ditawarkan?

NANEM memberikan rekomendasi tanaman berdasarkan kondisi lahan dan lingkungan pengguna. Pengguna memasukkan lokasi (latitude dan longitude) beserta media tanam yang digunakan (tanah, hidroponik, atau media lainnya). Pengguna juga dapat secara opsional menambahkan informasi luas lahan dan paparan cahaya matahari untuk hasil rekomendasi yang lebih akurat.

Sistem mengambil data lingkungan (suhu, kelembapan, dan curah hujan) berdasarkan koordinat lokasi melalui Open-Meteo API, kemudian mencocokkannya dengan karakteristik tanaman yang tersedia di dalam database menggunakan rule-based recommendation engine (bukan machine learning).

Berdasarkan data tersebut, sistem akan memberikan rekomendasi tanaman yang memiliki tingkat kecocokan dengan kondisi yang diberikan, disertai informasi mengenai karakteristik dan kebutuhan tanaman.

#### Apa hasil atau manfaat spesifik yang didapat?

- Membantu pengguna menentukan tanaman yang sesuai dengan kondisi lahannya.
- Mengurangi risiko memilih tanaman yang tidak sesuai dengan kondisi lingkungan.
- Mempermudah pengguna mendapatkan informasi mengenai kebutuhan suatu tanaman.
- Membantu pemanfaatan lahan secara lebih optimal.
- Meningkatkan pemahaman pengguna mengenai hubungan antara kondisi lingkungan dan pertumbuhan tanaman.

#### Mengapa produk Anda lebih baik dari kompetitor?

NANEM menggabungkan data kondisi lingkungan dengan rekomendasi tanaman dalam satu aplikasi. Pengguna tidak perlu mencari informasi mengenai setiap tanaman secara terpisah karena sistem memberikan rekomendasi berdasarkan kondisi yang dimasukkan pengguna.

Keunggulan dan perbandingan dengan kompetitor akan divalidasi lebih lanjut melalui proses benchmarking.

#### Mengapa harus sekarang?

Pemanfaatan lahan secara optimal menjadi semakin penting seiring dengan keterbatasan lahan dan perubahan kondisi lingkungan. Di sisi lain, perkembangan teknologi memungkinkan data lingkungan, data cuaca, dan informasi tanaman dimanfaatkan untuk membantu pengguna menentukan tanaman yang lebih sesuai.

---

### BENCHMARKING

Benchmarking dilakukan terhadap beberapa aplikasi atau platform yang memiliki fitur terkait rekomendasi tanaman, identifikasi tanaman, maupun manajemen kondisi lahan pertanian.

**1. Plantix**
Aplikasi yang berfokus pada deteksi penyakit tanaman melalui foto serta memberikan rekomendasi pupuk dan perawatan. Kekuatan utamanya terletak pada komunitas petani yang aktif dan fitur forum tanya-jawab. Namun, aplikasi ini lebih berfokus pada diagnosa penyakit tanaman, bukan pada rekomendasi jenis tanaman yang sesuai dengan kondisi lahan.

**2. PlantNet**
Aplikasi identifikasi jenis tanaman berbasis foto dengan database spesies yang sangat luas dan akurasi identifikasi yang tinggi. Namun, PlantNet tidak menyediakan fitur rekomendasi tanaman berdasarkan kondisi lingkungan atau lahan pengguna.

**3. Planta**
Aplikasi yang berfokus pada perawatan tanaman hias, seperti pengingat penyiraman dan pemupukan. Memiliki UI/UX yang rapi serta personalisasi jadwal perawatan. Target penggunanya lebih ke tanaman hias rumahan, bukan lahan pertanian atau kebun skala kecil.

**4. CropIn**
Platform agri-tech yang berfokus pada manajemen lahan pertanian skala besar, memanfaatkan data satelit untuk analisis lingkungan dan prediksi hasil panen. Kekuatannya ada pada analitik data yang mendalam, tetapi sistemnya cukup kompleks dan ditujukan untuk petani profesional, bukan pemula.

**Kesimpulan Benchmarking:**
Berdasarkan hasil benchmarking, kombinasi fitur "input kondisi lahan → rekomendasi tanaman yang sesuai" masih jarang ditemukan sebagai fitur utama pada aplikasi yang ada. Sebagian besar kompetitor berfokus pada identifikasi atau diagnosa tanaman (Plantix, PlantNet) maupun manajemen pertanian skala besar (CropIn). Hal ini menjadi peluang diferensiasi bagi NANEM untuk menyasar pengguna pemula dan pemilik lahan skala kecil dengan alur penggunaan yang lebih sederhana.

---

### DAFTAR MODUL DAN PIC

Modul yang direncanakan dalam aplikasi NANEM:

1. **Autentikasi, Rekomendasi, dan Riwayat**
   Modul ini menangani autentikasi pengguna (register, login, logout), sistem rekomendasi tanaman berbasis rule-based menggunakan data lingkungan dari Open-Meteo API, serta riwayat rekomendasi yang pernah dilakukan pengguna.

   **CRUD:**
   - Create: generate rekomendasi berdasarkan input lokasi, media tanam, serta luas lahan dan paparan cahaya (opsional); hasil disimpan sebagai snapshot riwayat.
   - Read: melihat daftar riwayat rekomendasi beserta detail satu riwayat.
   - Update: mengubah nama lahan pada riwayat (hasil rekomendasi tidak dapat diubah secara manual).
   - Delete: menghapus riwayat rekomendasi.

   PIC: Jihan

2. **Profil Pengguna**
   Modul ini mengelola data profil pengguna yang terhubung dengan akun Django (User).

   **CRUD:**
   - Create: profil dibuat otomatis saat pengguna melakukan registrasi.
   - Read: melihat profil sendiri maupun profil pengguna lain.
   - Update: mengubah nama, username, foto profil, dan kata sandi.
   - Delete: menghapus akun.

   PIC: Hafidz

3. **Koleksi Tanaman**
   Modul ini berfungsi sebagai jurnal pribadi pengguna untuk mendokumentasikan tanaman yang mereka miliki atau tanam.

   **CRUD:**
   - Create: menambahkan tanaman ke koleksi pribadi beserta foto, judul, dan deskripsi.
   - Read: melihat koleksi tanaman milik sendiri.
   - Update: mengubah judul dan deskripsi (foto tidak dapat diganti setelah dibuat).
   - Delete: menghapus tanaman dari koleksi.

   PIC: Zhafira

4. **Katalog Tanaman**
   Modul ini merupakan master data tanaman yang digunakan bersama oleh modul Rekomendasi, Koleksi Tanaman, dan Panduan Budidaya.

   **CRUD:**
   - Create: admin menambahkan data tanaman baru (nama, kebutuhan cahaya, kebutuhan air, ukuran, gambar, dan atribut lain).
   - Read: pengguna dapat melihat, mencari, dan memfilter katalog tanaman; admin dapat melihat seluruh data.
   - Update: admin memperbarui data tanaman.
   - Delete: admin menghapus data tanaman dari katalog.

   PIC: Bobby

5. **Panduan Budidaya**
   Modul ini menyediakan informasi praktis mengenai cara membudidayakan tanaman, seperti cara menanam, media tanam, kebutuhan air, frekuensi penyiraman, kebutuhan cahaya, pemupukan, dan waktu panen.

   **CRUD:**
   - Create: admin menambahkan panduan budidaya untuk suatu tanaman.
   - Read: pengguna dapat melihat panduan budidaya dan memfilter sesuai kebutuhan.
   - Update: admin memperbarui panduan budidaya.
   - Delete: admin menghapus panduan budidaya.

   PIC: Nicholas

> **Catatan:** Modul Katalog Tanaman dan Panduan Budidaya tetap merupakan dua modul terpisah dengan ownership berbeda, meskipun pada sisi pengguna keduanya ditampilkan sebagai satu halaman Plant Detail. Modul CRUD Admin (Katalog Tanaman dan Panduan Budidaya) diimplementasikan menggunakan Views, Template, dan Form khusus, bukan Django Admin bawaan, agar memenuhi definisi modul pada ketentuan tugas.
>
> Setiap modul dikembangkan pada branch Git terpisah sesuai PIC masing-masing, misalnya `module/auth-recommendation-history`, `module/user-profile`, `module/plant-collection`, `module/plant-catalog`, dan `module/cultivation-guide`.
>
> Ide utama aplikasi NANEM sudah ditetapkan. Namun, daftar modul dan pembagian PIC di atas masih bersifat sementara dan dapat berubah berdasarkan hasil diskusi, pembagian tugas, serta pertimbangan feasibility proyek.

---

### DAFTAR MODEL DAN PIC

Model yang direncanakan:

| Model                  | Deskripsi                                                                      | PIC      |
|-------------------------|-------------------------------------------------------------------------------|----------|
| User                    | Model bawaan Django untuk autentikasi (username, password)                    | Jihan    |
| UserProfile             | Data profil tambahan pengguna (nama, foto profil), relasi 1:1 dengan User     | Hafidz   |
| Plant                   | Data master tanaman (nama, nama ilmiah, deskripsi, gambar, dll)               | Bobby    |
| CultivationGuide        | Panduan budidaya suatu tanaman, relasi 1:1 dengan Plant                       | Nicholas |
| PlantCollection         | Koleksi tanaman pribadi pengguna (foto, judul, deskripsi)                     | Zhafira  |
| RecommendationHistory   | Snapshot hasil rekomendasi pengguna (termasuk semua datanya)                  | Jihan    |

Model dan PIC masih dapat disesuaikan dengan kebutuhan implementasi.

---

### EKSTERNAL API DAN TAUTAN MOCK API

Rencana penggunaan external API:

- **Open-Meteo API** — digunakan untuk memperoleh data lingkungan (suhu, kelembapan, dan curah hujan) berdasarkan koordinat lokasi pengguna, sebagai input untuk rule-based recommendation engine. Tidak memerlukan API key.
  Sumber: https://open-meteo.com/en/docs

- **Perenual API** — digunakan sebagai sumber data awal (seed) untuk Plant Catalog, mencakup informasi kebutuhan cahaya (sunlight), kebutuhan air (watering), dan ukuran tanaman (dimensions). Data diambil satu kali untuk mengisi database lokal, bukan dipanggil pada setiap request, mengikuti batasan free tier (akses ke 3.000 spesies pertama dan 100 request/hari).
  Sumber: https://perenual.com/docs/api

**Tautan mock API:** Tidak diperlukan untuk saat ini, karena kebutuhan data tanaman telah terpenuhi melalui Perenual API sebagai sumber seed data.

External API yang digunakan dapat berubah sesuai ketersediaan dan feasibility implementasi.

---

### USER ROLE DAN TARGET USER

#### Guest

Guest dapat:

- Menggunakan fitur Rekomendasi Tanaman.

Hasil rekomendasi untuk Guest tidak disimpan, dan Guest tidak dapat mengakses Katalog Tanaman, Detail Tanaman, Panduan Budidaya, Riwayat Rekomendasi, Profil, maupun Koleksi Tanaman.

#### User

User dapat:

- Menggunakan fitur Rekomendasi Tanaman (hasil dapat disimpan sebagai riwayat).
- Melihat, mencari, dan memfilter Katalog Tanaman.
- Melihat Detail Tanaman beserta Panduan Budidaya.
- CRUD Riwayat Rekomendasi (kecuali mengubah hasil rekomendasi secara manual).
- CRUD Profil Pengguna.
- CRUD Koleksi Tanaman.

#### Admin

Admin dapat:

- Menggunakan seluruh fitur User.
- CRUD Katalog Tanaman.
- CRUD Panduan Budidaya.

#### Target User

Target utama NANEM adalah:

- Pemilik lahan skala kecil.
- Masyarakat yang ingin mulai bercocok tanam.
- Pemula yang belum mengetahui tanaman yang sesuai dengan kondisi lahannya.

---

### TAUTAN DEPLOYMENT PWS

Tautan deployment PWS: https://jihan-nabiilah-proyektengahsms.pws.cs.ui.ac.id/

---

### TAUTAN DESAIN FIGMA (LOW-FI)

Tautan Figma: https://www.figma.com/design/AwgBPy0JQrH6tXT4aN79Io/Main-Figma?node-id=0-1&p=f&t=HVUroBjAaXXzQvnn-0
