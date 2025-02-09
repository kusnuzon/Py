import customtkinter as ctk
from tkinter import filedialog, messagebox
from itertools import product
import os
import pyzipper
import rarfile
import threading
import time
import py7zr

# Variabel global untuk kontrol thread
stop_event = threading.Event()

# Fungsi untuk mengonversi detik ke format waktu detail (hari, jam, menit, detik)
def format_time(seconds: float) -> str:
    days = seconds // (24 * 3600)
    remainder = seconds % (24 * 3600)
    hours = remainder // 3600
    remainder %= 3600
    minutes = remainder // 60
    seconds = remainder % 60
    return f"{int(days)} hari, {int(hours)} jam, {int(minutes)} menit, {seconds:.2f} detik"

# Fungsi umum untuk mengekstrak file berdasarkan ekstensi
def extract_file(file_path: str, password: str, ext: str) -> bool:
    try:
        if ext == '.zip':
            with pyzipper.AESZipFile(file_path) as zf:
                zf.extractall(pwd=password.encode('utf-8'))
        elif ext == '.rar':
            rarfile.UNRAR_TOOL = r"C:\Program Files\WinRAR\unrar.exe"
            with rarfile.RarFile(file_path) as rf:
                rf.extractall(path=os.getcwd(), pwd=password)
        elif ext == '.7z':
            with py7zr.SevenZipFile(file_path, mode='r', password=password) as szf:
                szf.extractall(path=os.getcwd())
        return True
    except Exception as e:
        print(f"Error extracting {ext}: {e}")
        return False

# Fungsi untuk memuat token dari file .txt
def load_tokens_from_file() -> list[str]:
    token_file = filedialog.askopenfilename(
        title="Pilih File Token (.txt)",
        filetypes=[("Text files", "*.txt")]
    )
    if not token_file:
        return []
    with open(token_file, 'r', encoding='utf-8') as f:
        loaded_tokens = [line.strip() for line in f.readlines() if line.strip()]
    return loaded_tokens

# Fungsi untuk mencoba semua kombinasi token
def try_combinations(file_path: str, local_tokens: list[str], progress_widget: ctk.CTkProgressBar, min_length: int, max_length: int):
    total_combinations = sum(len(local_tokens) ** length for length in range(min_length, max_length + 1))
    progress_step = 100 / total_combinations if total_combinations > 0 else 0
    combination_count = 0
    start_time = time.time()
    last_time = start_time
    moving_average_times = []
    MOVING_AVERAGE_WINDOW = 10
    estimated_total_time = None

    for length in range(min_length, max_length + 1):
        for combination in product(local_tokens, repeat=length):
            if stop_event.is_set():
                result_label.configure(text="Proses Dihentikan", text_color="#FFA500")
                return None
            password = ''.join(combination)
            combination_count += 1
            current_combination_label.configure(text=f"Kombinasi Saat Ini: {password}")
            count_label.configure(text=f"Jumlah Kombinasi Dicoba: {combination_count}")
            elapsed_time = time.time() - start_time
            elapsed_time_label.configure(text=f"Waktu Berjalan: {format_time(elapsed_time)}")

            current_time = time.time()
            if combination_count > 1:
                time_per_combination = current_time - last_time
                moving_average_times.append(time_per_combination)
                if len(moving_average_times) > MOVING_AVERAGE_WINDOW:
                    moving_average_times.pop(0)
                average_time_per_combination = sum(moving_average_times) / len(moving_average_times)
                if estimated_total_time is None and len(moving_average_times) >= MOVING_AVERAGE_WINDOW:
                    estimated_total_time = average_time_per_combination * total_combinations
                    total_time_label.configure(text=f"Waktu Total Estimasi: {format_time(estimated_total_time)}")
            else:
                average_time_per_combination = 0

            last_time = current_time
            if estimated_total_time is not None:
                remaining_time = max(0, estimated_total_time - elapsed_time)
                remaining_time_label.configure(text=f"Waktu Tersisa: {format_time(remaining_time)}")
            else:
                remaining_time_label.configure(text="Waktu Tersisa: Menghitung...")

            ext = os.path.splitext(file_path)[1].lower()
            success = extract_file(file_path, password, ext)
            if success:
                result_label.configure(text=f"Password Ditemukan: {password}", text_color="#00FF00")
                return password

            progress_widget.set(min(combination_count * progress_step / 100, 1))
            root.update_idletasks()

    result_label.configure(text="Password Tidak Ditemukan", text_color="#FF0000")
    return None

# Fungsi untuk menjalankan proses ekstraksi di thread terpisah
def run_extraction(file_path: str, local_tokens: list[str], progress_widget: ctk.CTkProgressBar, min_length: int, max_length: int):
    def task():
        try:
            result = try_combinations(file_path, local_tokens, progress_widget, min_length, max_length)
            if result:
                messagebox.showinfo("Sukses", f"File berhasil dibuka! Password: {result}")
            else:
                messagebox.showerror("Gagal", "Tidak dapat membuka file dengan kombinasi token yang diberikan.")
        except Exception as e:
            messagebox.showerror("Error", f"Terjadi kesalahan: {e}")

    threading.Thread(target=task).start()

# Fungsi untuk menghentikan proses pencarian password
def stop_process():
    confirm = messagebox.askyesno("Konfirmasi", "Apakah Anda yakin ingin menghentikan proses?")
    if confirm:
        stop_event.set()
        result_label.configure(text="Proses Dihentikan", text_color="#FFA500")

# Fungsi untuk membuka file ZIP/RAR/7z
def open_file():
    file_path = filedialog.askopenfilename(
        title="Pilih File",
        filetypes=[("ZIP files", "*.zip"), ("RAR files", "*.rar"), ("7z files", "*.7z")]
    )
    if not file_path:
        return
    if not tokens:
        messagebox.showwarning("Peringatan", "Tidak ada token yang dimuat! Muat token terlebih dahulu.")
        return
    try:
        min_length = int(min_length_entry.get()) if min_length_entry.get() else 1
        max_length = int(max_length_entry.get()) if max_length_entry.get() else 5
        if min_length <= 0 or max_length <= 0 or min_length > max_length:
            raise ValueError
    except ValueError:
        messagebox.showerror("Error", "Masukkan angka valid untuk panjang minimal dan maksimal kombinasi token.")
        return

    progress_bar.set(0)
    result_label.configure(text="Mencari Password...", text_color="#FFFFFF")
    current_combination_label.configure(text="Kombinasi Saat Ini: ")
    count_label.configure(text="Jumlah Kombinasi Dicoba: 0")
    elapsed_time_label.configure(text="Waktu Berjalan: 0 hari, 0 jam, 0 menit, 0.00 detik")
    remaining_time_label.configure(text="Waktu Tersisa: Menghitung...")
    total_time_label.configure(text="Waktu Total Estimasi: Menghitung...")
    stop_event.clear()
    run_extraction(file_path, tokens, progress_bar, min_length, max_length)

# Fungsi untuk memuat token
def load_tokens():
    global tokens
    loaded_tokens = load_tokens_from_file()
    tokens = loaded_tokens
    if tokens:
        messagebox.showinfo("Info", f"{len(tokens)} token berhasil dimuat!")
    else:
        messagebox.showwarning("Peringatan", "Tidak ada token yang dimuat!")

# Variabel global untuk menyimpan token
tokens: list[str] = []

# Konfigurasi customtkinter
ctk.set_appearance_mode("dark")  # Mode gelap
ctk.set_default_color_theme("blue")  # Tema biru

# Membuat GUI dengan customtkinter
root = ctk.CTk()
root.title("ZIP/RAR/7z Password Finder")
root.geometry("600x700")

# Menambahkan ikon dengan penanganan kesalahan
try:
    # Coba gunakan ikon kustom
    root.iconbitmap("icon.ico")  # Ganti dengan path ikon Anda
except Exception as e:
    print(f"Icon not found: {e}")
    # Jika gagal, biarkan CustomTkinter menggunakan ikon defaultnya
    pass

# Header
header_label = ctk.CTkLabel(root, text="ZIP/RAR/7z Password Finder", font=("Segoe UI", 20, "bold"))
header_label.pack(pady=20)

# Tombol untuk memuat token dari file .txt
load_button = ctk.CTkButton(root, text="Muat Token dari File .txt", command=load_tokens, corner_radius=10)
load_button.pack(pady=10)

# Input untuk panjang minimal kombinasi token
min_length_label = ctk.CTkLabel(root, text="Panjang Minimal:", font=("Segoe UI", 12))
min_length_label.pack(pady=5)
min_length_entry = ctk.CTkEntry(root, width=100, corner_radius=10)
min_length_entry.pack(pady=5)

# Input untuk panjang maksimal kombinasi token
max_length_label = ctk.CTkLabel(root, text="Panjang Maksimal:", font=("Segoe UI", 12))
max_length_label.pack(pady=5)
max_length_entry = ctk.CTkEntry(root, width=100, corner_radius=10)
max_length_entry.pack(pady=5)

# Progress Bar
progress_bar = ctk.CTkProgressBar(root, orientation="horizontal", mode="determinate", corner_radius=10)
progress_bar.pack(pady=20)
progress_bar.set(0)

# Label untuk menampilkan informasi
current_combination_label = ctk.CTkLabel(root, text="Kombinasi Saat Ini: ", font=("Segoe UI", 12))
current_combination_label.pack(pady=5)
count_label = ctk.CTkLabel(root, text="Jumlah Kombinasi Dicoba: 0", font=("Segoe UI", 12))
count_label.pack(pady=5)
elapsed_time_label = ctk.CTkLabel(root, text="Waktu Berjalan: 0 hari, 0 jam, 0 menit, 0.00 detik", font=("Segoe UI", 12))
elapsed_time_label.pack(pady=5)
remaining_time_label = ctk.CTkLabel(root, text="Waktu Tersisa: Menghitung...", font=("Segoe UI", 12))
remaining_time_label.pack(pady=5)
total_time_label = ctk.CTkLabel(root, text="Waktu Total Estimasi: Menghitung...", font=("Segoe UI", 12))
total_time_label.pack(pady=5)

# Label untuk menampilkan hasil proses ekstraksi
result_label = ctk.CTkLabel(root, text="Hasil: Menunggu...", font=("Segoe UI", 14, "bold"))
result_label.pack(pady=10)

# Tombol untuk membuka file ZIP/RAR/7z
open_button = ctk.CTkButton(root, text="Buka File ZIP/RAR/7z", command=open_file, corner_radius=10)
open_button.pack(pady=10)

# Tombol untuk menghentikan proses pencarian password
stop_button = ctk.CTkButton(root, text="Stop", command=stop_process, corner_radius=10, fg_color="#FF4500", hover_color="#FF6347")
stop_button.pack(pady=10)

# Footer
footer_label = ctk.CTkLabel(root, text="© 2025 ZON", font=("Segoe UI", 10), text_color="white")
footer_label.pack(side="bottom", pady=10)

# Animasi footer saat startup
def show_footer():
    footer_label.configure(text="© 2025 ZON", text_color="white")
root.after(1000, show_footer)

# Menjalankan GUI
root.mainloop()