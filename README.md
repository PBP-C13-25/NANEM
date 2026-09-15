# Proyek-Tengah-Semester

## NANEM

**Nama aplikasi:** NANEM _(nama sementara)_

**Anggota:**

- Jihan Nabiilah Permata Sukma - 2506549026
- Muhammad Hafidz Muazzam - 2506621812
- Zhafira Richas - 2506540941
- Muhammad Eshan Bobby Bhaskara - 2506546333
- Johannes Nichola Simatupang - 2406495930

---

### DESKRIPSI APLIKASI

**NANEM** merupakan aplikasi yang memberikan rekomendasi tanaman berdasarkan kondisi lahan dan lingkungan pengguna. Aplikasi ini membantu pengguna mengetahui tanaman yang sesuai dengan kondisi tertentu sehingga pemanfaatan lahan dapat dilakukan secara lebih optimal.

Ide utama aplikasi **sudah ditetapkan**, sedangkan detail modul dan pembagian PIC masih dapat berubah menyesuaikan hasil diskusi kelompok, feedback, serta feasibility selama proses pengembangan.

#### Siapa pelanggan?

Target pengguna NANEM adalah:

- Masyarakat yang ingin mulai bercocok tanam.
- Pemilik lahan skala kecil.
- Petani atau pengguna yang ingin mengetahui tanaman yang sesuai dengan kondisi lahannya.
- Pemula yang belum mengetahui tanaman yang cocok dengan kondisi lingkungan tertentu.

#### Apa solusi yang ditawarkan?

NANEM memberikan rekomendasi tanaman berdasarkan kondisi lahan dan lingkungan pengguna. Pengguna dapat memasukkan atau memperoleh data seperti lokasi, kondisi tanah, suhu, kelembapan, dan curah hujan.

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

1. **Input Kondisi Lahan**
   - Pengguna memasukkan informasi kondisi lahan atau lokasi.
   - PIC: Zhafira

2. **Katalog Tanaman**
   - Menampilkan daftar tanaman beserta informasi dan karakteristiknya.
   - PIC: Bobby

3. **Rekomendasi Tanaman**
   - Menghasilkan rekomendasi tanaman berdasarkan kondisi lahan dan lingkungan pengguna.
   - PIC: Jihan

4. **Detail Tanaman**
   - Menampilkan informasi lebih lengkap mengenai tanaman dan kebutuhan tumbuhnya.
   - PIC: Hafidz

5. **Riwayat Rekomendasi**
   - Menyimpan dan menampilkan riwayat rekomendasi yang pernah dilakukan pengguna.
   - PIC: Nicholas

> **Catatan:** Ide utama aplikasi NANEM sudah ditetapkan. Namun, daftar modul dan pembagian PIC di atas masih bersifat sementara dan dapat berubah berdasarkan hasil diskusi, pembagian tugas, serta pertimbangan feasibility proyek.

---

### DAFTAR MODEL DAN PIC

Model yang direncanakan:

| Model             | Deskripsi                                                           | PIC |
| ----------------- | ------------------------------------------------------------------- | --- |
| Plant             | Menyimpan informasi tanaman                                         | TBD |
| PlantRequirement  | Menyimpan kebutuhan lingkungan tanaman                              | TBD |
| SoilData          | Menyimpan data atau karakteristik tanah                             | TBD |
| EnvironmentalData | Menyimpan data lingkungan seperti suhu, kelembapan, dan curah hujan | TBD |
| Recommendation    | Menyimpan hasil rekomendasi tanaman                                 | TBD |
| SearchHistory     | Menyimpan riwayat pencarian atau rekomendasi pengguna               | TBD |

Model dan PIC masih dapat disesuaikan dengan kebutuhan implementasi.

---

### EKSTERNAL API DAN TAUTAN MOCK API

Rencana penggunaan external API:

- **Weather API** untuk memperoleh data suhu, kelembapan, dan curah hujan, seperti Open-Meteo.
- **Location/Geolocation API** untuk memperoleh informasi lokasi pengguna, seperti Google Earth Engine.
- Dataset atau sumber data tanaman untuk memperoleh informasi karakteristik dan kebutuhan tanaman.

**Tautan mock API:** TBD

External API yang digunakan dapat berubah sesuai ketersediaan dan feasibility implementasi.

---

### USER ROLE DAN TARGET USER

#### User

User dapat:

- Memasukkan kondisi lahan.
- Melihat rekomendasi tanaman.
- Melihat katalog dan detail tanaman.
- Melihat riwayat rekomendasi.

#### Admin

Admin dapat:

- Menambahkan data tanaman.
- Mengubah data tanaman.
- Menghapus data tanaman.
- Mengelola informasi kebutuhan tanaman.

#### Target User

Target utama NANEM adalah:

- Pemilik lahan skala kecil.
- Masyarakat yang ingin mulai bercocok tanam.
- Pemula yang belum mengetahui tanaman yang sesuai dengan kondisi lahannya.

---

### TAUTAN DEPLOYMENT PWS

Tautan deployment PWS: https://jihan-nabiilah-proyek_tengah_sms26.pws.cs.ui.ac.id/

---

### TAUTAN DESAIN FIGMA (LOW-FI)

Tautan Figma: https://www.figma.com/design/AwgBPy0JQrH6tXT4aN79Io/Main-Figma?node-id=0-1&p=f&t=HVUroBjAaXXzQvnn-0
