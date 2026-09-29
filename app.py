import streamlit as st
import sqlite3
from PIL import Image
import pytesseract
import re
from datetime import datetime, timedelta

# Konfigurasi halaman modern
st.set_page_config(page_title="Portal Absensi & Gaji", page_icon="💼", layout="wide")

# Styling CSS tambahan
st.markdown("""
    <style>
        .main {
            background-color: #0e1117;
        }
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
        }
        div.stMetric {
            background-color: #1f2937;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# Fungsi koneksi database SQLite (membuat file database.db otomatis)
def get_connection():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    return conn

# Inisialisasi tabel database SQLite
def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT,
            kontak TEXT UNIQUE,
            password TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS riwayat_absen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tanggal TEXT,
            jam_masuk TEXT,
            jam_keluar TEXT,
            total_jam REAL,
            estimasi_gaji INTEGER,
            UNIQUE(user_id, tanggal)
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

# --- SISTEM SESSION STATE LOGIN ---
if 'user_logged_in' not in st.session_state:
    st.session_state['user_logged_in'] = False
    st.session_state['user_id'] = None
    st.session_state['user_nama'] = ""

if not st.session_state['user_logged_in']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔐 Portal Masuk Absensi")
        st.write("Silakan masuk atau daftar akun terlebih dahulu.")
        
        tab1, tab2 = st.tabs(["Masuk Akun", "Daftar Baru"])
        
        with tab1:
            login_kontak = st.text_input("Email / No. Telepon", key="login_kontak")
            login_pass = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Masuk Sekarang", use_container_width=True):
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, nama, kontak, password FROM users WHERE kontak = ? AND password = ?", (login_kontak, login_pass))
                    user = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    
                    if user:
                        st.session_state['user_logged_in'] = True
                        st.session_state['user_id'] = user[0]
                        st.session_state['user_nama'] = user[1]
                        st.success(f"Selamat datang kembali, {user[1]}!")
                        st.rerun()
                    else:
                        st.error("Kontak atau password salah!")
                except Exception as e:
                    st.error(f"Error database: {e}")
                    
        with tab2:
            reg_nama = st.text_input("Nama Lengkap")
            reg_kontak = st.text_input("Email / No. Telepon Unik")
            reg_pass = st.text_input("Buat Password Aman", type="password")
            
            if st.button("Daftar Akun", use_container_width=True):
                if reg_nama and reg_kontak and reg_pass:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO users (nama, kontak, password) VALUES (?, ?, ?)", (reg_nama, reg_kontak, reg_pass))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        st.success("Akun berhasil dibuat! Silakan pindah ke tab Masuk Akun.")
                    except Exception as e:
                        st.error(f"Gagal mendaftar (Kontak mungkin sudah terdaftar): {e}")
                else:
                    st.warning("Semua kolom wajib diisi!")

else:
    st.sidebar.markdown(f"### Halo, **{st.session_state['user_nama']}** 👋")
    if st.sidebar.button("Keluar Akun", use_container_width=True):
        st.session_state['user_logged_in'] = False
        st.session_state['user_id'] = None
        st.session_state['user_nama'] = ""
        st.rerun()

    st.title("💼 Dashboard Rekap Absen & Gaji Mingguan")
    st.write("Sistem otomatis mencatat kehadiran, mencegah duplikasi, serta memisahkan rekapitulasi per pekan (Cut-off Jumat).")

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Pengaturan Tarif")
    tarif_per_jam = st.sidebar.number_input("Tarif per Jam (Rp)", value=12000, step=1000)
    st.sidebar.markdown("---")
    st.sidebar.info("💡 **Info Sistem:**\n- Jam istirahat dipotong (12.00-13.00 & 18.00-19.00)\n- Rekapitulasi otomatis dikelompokkan per pekan kerja.")

    if 'file_uploader_key' not in st.session_state:
        st.session_state['file_uploader_key'] = 0

    col_up1, col_up2 = st.columns([3, 1])
    with col_up1:
        uploaded_file = st.file_uploader("Pilih file screenshot absensi...", type=["png", "jpg", "jpeg"], key=st.session_state['file_uploader_key'])
    
    with col_up2:
        st.markdown("<br>", unsafe_allow_html=True)
        if uploaded_file is not None:
            if st.button("🗑️ Batalkan Gambar", use_container_width=True):
                st.session_state['file_uploader_key'] += 1
                st.rerun()

    if uploaded_file is not None:
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🖼️ Preview Bukti Absen")
            image = Image.open(uploaded_file)
            st.image(image, caption="Screenshot Terunggah", use_container_width=True)

        with col2:
            st.subheader("⚙️ Hasil Ekstraksi & Form")
            
            try:
                text = pytesseract.image_to_string(image)
                in_match = re.search(r'In[:\s]*(\d{2}:\d{2}:\d{2})', text, re.IGNORECASE)
                out_match = re.search(r'Out[:\s]*(\d{2}:\d{2}:\d{2})', text, re.IGNORECASE)
                date_match = re.search(r'([A-Za-z]+,\s+[A-Za-z]+\s+\d{1,2})', text)
                
                default_date = date_match.group(1) if date_match else "Tuesday, September 29"
                default_in = in_match.group(1) if in_match else "07:52:37"
                default_out = out_match.group(1) if out_match else "17:05:51"
            except Exception:
                default_date = "Tuesday, September 29"
                default_in = "07:52:37"
                default_out = "17:05:51"

            with st.form("form_absen"):
                tgl_input = st.text_input("Tanggal Absen (Sesuai Gambar)", value=default_date)
                jam_masuk_input = st.text_input("Jam Masuk (HH:MM:SS)", value=default_in)
                jam_keluar_input = st.text_input("Jam Keluar (HH:MM:SS)", value=default_out)
                
                submitted = st.form_submit_button("🚀 Hitung & Simpan Data", use_container_width=True)
                
                if submitted:
                    try:
                        fmt = "%H:%M:%S"
                        t_in = datetime.strptime(jam_masuk_input.strip(), fmt)
                        t_out = datetime.strptime(jam_keluar_input.strip(), fmt)
                        
                        selisih_detik = (t_out - t_in).total_seconds()
                        total_jam_kotor = selisih_detik / 3600.0
                        
                        jam_istirahat = 0
                        if t_in.hour <= 12 and t_out.hour >= 13:
                            jam_istirahat += 1
                        if t_in.hour <= 18 and t_out.hour >= 19:
                            jam_istirahat += 1
                            
                        total_jam_bersih = max(0, total_jam_kotor - jam_istirahat)
                        estimasi_gaji = int(total_jam_bersih * tarif_per_jam)
                        
                        conn = get_connection()
                        cursor = conn.cursor()
                        query = """
                            INSERT INTO riwayat_absen (user_id, tanggal, jam_masuk, jam_keluar, total_jam, estimasi_gaji) 
                            VALUES (?, ?, ?, ?, ?, ?)
                        """
                        cursor.execute(query, (st.session_state['user_id'], tgl_input, jam_masuk_input, jam_keluar_input, round(total_jam_bersih, 2), estimasi_gaji))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        
                        st.success(f"Berhasil disimpan! Jam Bersih: {round(total_jam_bersih, 2)} jam | Gaji: Rp {estimasi_gaji:,}")
                        
                        st.session_state['file_uploader_key'] += 1
                        st.rerun()
                        
                    except sqlite3.IntegrityError:
                        st.error(f"Gagal: Absensi untuk tanggal **{tgl_input}** sudah pernah di-input sebelumnya!")
                    except Exception as err:
                        st.error(f"Terjadi kesalahan format waktu: {err}")

    # Bagian bawah: Rekapitulasi Mingguan Otomatis & Total Keseluruhan
    st.markdown("---")
    st.subheader("📊 Rekapitulasi & Prediksi Gaji Mingguan")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, tanggal, jam_masuk, jam_keluar, total_jam, estimasi_gaji FROM riwayat_absen WHERE user_id = ? ORDER BY id DESC", (st.session_state['user_id'],))
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if data:
            total_akumulasi_gaji = sum(row[5] for row in data)
            
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric(label="Total Hari Masuk Tercatat", value=f"{len(data)} Hari")
            with col_m2:
                st.metric(label="Total Akumulasi Gaji Keseluruhan", value=f"Rp {total_akumulasi_gaji:,}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- PENGELOMPOKAN MINGGUAN DENGAN RENTANG TANGGAL (CUT-OFF JUMAT) ---
            st.markdown("### 🗓️ Rincian per Periode Pekan (Pencairan Jumat)")
            
            pengelompokan_minggu = {}
            for row in data:
                tgl_str = row[1]
                
                try:
                    clean_date_str = re.sub(r'^[A-Za-z]+,\s+', '', tgl_str) + " 2026"
                    dt = datetime.strptime(clean_date_str, "%B %d %Y")
                    
                    start_of_week = dt - timedelta(days=dt.weekday())
                    end_of_week = start_of_week + timedelta(days=4)
                    
                    kelompok = f"Periode: {start_of_week.strftime('%d %b')} - {end_of_week.strftime('%d %b %Y')}"
                except Exception:
                    kelompok = "Periode Lainnya"
                
                if kelompok not in pengelompokan_minggu:
                    pengelompokan_minggu[kelompok] = []
                pengelompokan_minggu[kelompok].append(row)
            
            for kelompok_nama, rows_in_group in pengelompokan_minggu.items():
                sub_total_gaji = sum(r[5] for r in rows_in_group)
                
                with st.expander(f"📁 {kelompok_nama} — Total Gaji: Rp {sub_total_gaji:,} ({len(rows_in_group)} Hari Kerja)", expanded=True):
                    for row in rows_in_group:
                        row_id = row[0]
                        tgl = row[1]
                        j_in = row[2]
                        j_out = row[3]
                        durasi = row[4]
                        gaji = row[5]
                        
                        cols_data = st.columns([5, 1])
                        with cols_data[0]:
                            st.markdown(f"✨ **{tgl}** &nbsp;|&nbsp; Masuk: `{j_in}` &nbsp;|&nbsp; Keluar: `{j_out}` &nbsp;|&nbsp; Durasi: **{durasi} jam** &nbsp;|&nbsp; 💰 Gaji: **Rp {gaji:,}**")
                        with cols_data[1]:
                            if st.button("Hapus", key=f"del_{row_id}", use_container_width=True):
                                try:
                                    conn_del = get_connection()
                                    cur_del = conn_del.cursor()
                                    cur_del.execute("DELETE FROM riwayat_absen WHERE id = ? AND user_id = ?", (row_id, st.session_state['user_id']))
                                    conn_del.commit()
                                    cur_del.close()
                                    conn_del.close()
                                    st.success(f"Data tanggal {tgl} berhasil dihapus!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal menghapus: {e}")
        else:
            st.info("Belum ada riwayat absen tersimpan. Silakan unggah screenshot absensimu di atas.")
    except Exception as e:
        st.error(f"Gagal memuat data dari database: {e}")