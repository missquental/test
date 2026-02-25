import os
import re
import time
import requests
from urllib.parse import urlencode, urlparse, parse_qs
from bs4 import BeautifulSoup
from pathlib import Path
from random import uniform

def get_bing_image_urls(keyword, max_images=50, delay_range=(1, 3)):
    """
    Ambil daftar URL gambar dari halaman pencarian Bing Images berdasarkan keyword.

    Args:
        keyword (str): Kata kunci pencarian.
        max_images (int): Jumlah maksimal URL gambar yang diambil.
        delay_range (tuple): Rentang waktu tunggu (detik) antar request (untuk hindari rate limit).

    Returns:
        list[str]: List URL gambar.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }

    # URL Bing Images dengan parameter query
    base_url = "https://www.bing.com/images/async"
    image_urls = []

    # Parameters awal (pencarian pertama)
    params = {
        "q": keyword,
        "first": 1,
        "count": max_images,  # Max 35 per request (Bing batas)
        "mmasync": 1,
    }

    # Kita lakukan multiple request untuk mendapatkan lebih banyak gambar
    # Bing hanya mengembalikan 35 gambar per request
    page_count = 1
    while len(image_urls) < max_images:
        params["first"] = page_count * 35 + 1
        if params["first"] > max_images + 5:
            break  # jangan ambil lebih dari yang dibutuhkan

        try:
            query_url = f"{base_url}?{urlencode(params)}"
            print(f"[Info] Fetching page: {query_url}")
            resp = requests.get(query_url, headers=headers, timeout=10)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            img_tags = soup.find_all("img", src=re.compile(r"^https://[^&]*\.(?:jpg|jpeg|png|gif|webp)", re.I))

            for img in img_tags:
                src = img.get("src")
                if src and not src.startswith("data:"):
                    # Bing sering memuat gambar kecil (thumbnail), kita ambil versi original dari URL
                    # Coba ganti ukuran ke "h" (high-res) jika ada kode tertentu
                    if "form=li" in src:
                        src = re.sub(r"size=\w+", "size=o", src)
                    image_urls.append(src)
                    if len(image_urls) >= max_images:
                        break

            # Stop loop jika tidak ada gambar baru
            if len(img_tags) == 0:
                print("[Info] No more images found.")
                break

            page_count += 1

            # Delay random (hindari rate limiting)
            delay = uniform(*delay_range)
            print(f"[Info] Waiting {delay:.2f}s before next request...")
            time.sleep(delay)

        except requests.exceptions.RequestException as e:
            print(f"[Error] Request failed: {e}")
            break

    return image_urls[:max_images]


def download_images(image_urls, keyword, output_dir="downloaded_images"):
    """
    Download gambar dari daftar URL ke folder lokal.

    Args:
        image_urls (list[str]): List URL gambar.
        keyword (str): Kata kunci untuk menyimpan ke folder bernama keyword.
        output_dir (str): Direktori dasar tempat menyimpan gambar.
    """
    folder = Path(output_dir) / keyword.replace(" ", "_")
    folder.mkdir(parents=True, exist_ok=True)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }

    for i, url in enumerate(image_urls):
        try:
            print(f"[Download] {i+1}/{len(image_urls)}: {url[:60]}...")
            resp = requests.get(url, headers=headers, timeout=15, stream=True)
            resp.raise_for_status()

            # Cek tipe konten
            content_type = resp.headers.get("Content-Type", "").lower()
            if "image" not in content_type:
                print(f"[Skip] Not an image: {url}")
                continue

            ext = content_type.split("/")[-1] or "jpg"
            filename = folder / f"image_{i+1:03d}.{ext}"

            with open(filename, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

        except Exception as e:
            print(f"[Error] Failed to download {url}: {e}")
            continue

    print(f"[✅ Done] Downloaded {len(image_urls)} images to '{folder}'")


# === CONTOH PENGGUNAAN ===
if __name__ == "__main__":
    keyword = input("Masukkan kata kunci pencarian (misal: 'mountain landscape'): ").strip()
    if not keyword:
        keyword = "mountain landscape"

    print(f"[Search] Mencari gambar untuk: '{keyword}'")

    # Ambil URL gambar
    urls = get_bing_image_urls(keyword, max_images=30, delay_range=(1.5, 2.5))

    if not urls:
        print("[❌ Gagal] Tidak ada gambar ditemukan.")
    else:
        print(f"[Found] Ditemukan {len(urls)} gambar.")
        # Download gambar
        download_images(urls, keyword, output_dir="bing_images")
