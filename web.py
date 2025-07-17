from flask import Flask, request, send_file, render_template_string, after_this_request
import requests, zipfile, os, re, html
from bs4 import BeautifulSoup

app = Flask(__name__)
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Direcciones base para dl1 y dl2
DL1_BASE = "https://nhentai.net/g"
DL2_BASE = "https://es.3hentai.net/d"

def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', '', name)

def extract_title(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    title_tag = soup.find('title')
    if title_tag:
        return sanitize(html.unescape(title_tag.text.strip()))
    return "SinTítulo"

def render_download_status(filename):
    return render_template_string(f"""
    <html><body style='font-family:sans-serif;text-align:center;margin-top:50px;'>
    <h2 id='status'>Descargando archivo...</h2>
    <script>
        setTimeout(() => {{
            document.getElementById('status').innerText = "Archivo descargado exitosamente, acepte la descarga en su navegador para guardar.";
            window.location.href = "/get/{filename}";
        }}, 2000);
    </script>
    </body></html>
    """)

def fetch_images(base_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
                      "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    try:
        res = requests.get(base_url, headers=headers)
        if res.status_code == 404:
            return None, []

        title = extract_title(res.text)
        images = []
        index = 1

        while True:
            page_url = f"{base_url}/{index}/"
            res = requests.get(page_url, headers=headers)
            if res.status_code == 404:
                break
            soup = BeautifulSoup(res.content, "html.parser")
            found = re.findall(r'https?://[^"\']+\.(?:jpg|jpeg|png|webp)', str(soup))
            images.extend(found)
            index += 1

        return title, images
    except Exception as e:
        print(f"Error al acceder {base_url}: {e}")
        return None, []

def create_cbz(title, code, images):
    filename = f"{code} - {title}.cbz"
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    with zipfile.ZipFile(path, "w") as zipf:
        for i, url in enumerate(images):
            try:
                img = requests.get(url).content
                ext = url.split('.')[-1].split('?')[0]
                fname = f"{i+1}.{ext}"
                temp_path = os.path.join(DOWNLOAD_FOLDER, fname)
                with open(temp_path, "wb") as f: f.write(img)
                zipf.write(temp_path, fname)
                os.remove(temp_path)
            except: continue
    return path

from flask import send_file
import os

def serve_and_clean(filepath):
    filename = os.path.basename(filepath)

    @after_this_request
    def cleanup(resp):
        try:
            os.remove(filepath)
        except:
            pass
        return resp

    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,  # Usado en Flask 2.x+
        mimetype="application/vnd.comicbook+zip"
    )


@app.route("/")
def index():
    html = """
    <html><body style="font-family:sans-serif;text-align:center;margin-top:50px;">
    <h1>Pagina web simple para descargara Mangas Hentai como CBZ</h1>
    <h2>Nhentai</h2>
    <form action="/dl1"><input name="code" placeholder="Código"><input type="submit" value="Descargar"></form>
    <h2>3Hentai DL</h2>
    <form action="/dl2"><input name="code" placeholder="Código"><input type="submit" value="Descargar"></form>
    <h2>NHentai DL (Split ",")</h2>
    <form action="/dl1m"><input name="codes" placeholder="123,456"><input type="submit" value="Descargar múltiple"></form>
    <h2>3Hentai DL (Split ",")</h2>
    <form action="/dl2m"><input name="codes" placeholder="789,321"><input type="submit" value="Descargar múltiple"></form>
    <p>Codigo: <a>https://github.com/nakigeplayer/hentai-dl-web/</a></p>
    </body></html>
    """
    return render_template_string(html)

@app.route("/dl1")
@app.route("/dl1/<code>")
def dl1(code=None):
    # Si el código no viene por parámetro de ruta, lo buscamos en query string
    if code is None:
        code = request.args.get("code", "").strip()
    else:
        code = code.strip()

    if not code:
        return "No se especificó ningún código."

    url = f"{DL1_BASE}/{code}"
    title, images = fetch_images(url)
    if not images:
        return f"No se encontraron imágenes en {url}"
    cbz_path = create_cbz(title, code, images)
    return render_download_status(os.path.basename(cbz_path))

@app.route("/dl1m")
@app.route("/dl1m/<codes>")
def dl1m(codes=None):
    if codes is None:
        codes = request.args.get("codes", "")
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return "No se especificó ningún código."

    links = []
    for code in code_list:
        url = f"{DL1_BASE}/{code}"
        title, images = fetch_images(url)
        if images:
            cbz = create_cbz(title, code, images)
            links.append(os.path.basename(cbz))

    if not links:
        return "No se generó ningún archivo."
    
    return render_template_string(f"""
    <html><body style='font-family:sans-serif;text-align:center;margin-top:50px;'>
    <h2>Archivos listos:</h2>
    <ul>
    {''.join(f"<li><a href='/get/{f}'>{f}</a></li>" for f in links)}
    </ul>
    </body></html>
    """)

@app.route("/dl2")
@app.route("/dl2/<code>")
def dl2(code=None):
    if code is None:
        code = request.args.get("code", "").strip()
    else:
        code = code.strip()

    if not code:
        return "No se especificó ningún código."

    url = f"{DL2_BASE}/{code}"
    title, images = fetch_images(url)
    if not images:
        return f"No se encontraron imágenes en {url}"
    cbz_path = create_cbz(title, code, images)
    return render_download_status(os.path.basename(cbz_path))

@app.route("/dl2m")
@app.route("/dl2m/<codes>")
def dl2m(codes=None):
    if codes is None:
        codes = request.args.get("codes", "")
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return "No se especificó ningún código."

    links = []
    for code in code_list:
        url = f"{DL2_BASE}/{code}"
        title, images = fetch_images(url)
        if images:
            cbz = create_cbz(title, code, images)
            links.append(os.path.basename(cbz))

    if not links:
        return "No se generó ningún archivo."
    
    return render_template_string(f"""
    <html><body style='font-family:sans-serif;text-align:center;margin-top:50px;'>
    <h2>Archivos listos:</h2>
    <ul>
    {''.join(f"<li><a href='/get/{f}'>{f}</a></li>" for f in links)}
    </ul>
    </body></html>
    """)


@app.route("/direct/<source>/<codes>")
def direct_download(source, codes):
    # Define base según la fuente
    if source == "dl1":
        base_url = DL1_BASE
    elif source == "dl2":
        base_url = DL2_BASE
    else:
        return f"Fuente inválida: {source}"

    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return "No se especificó ningún código."

    # Si es solo uno, descarga directa
    if len(code_list) == 1:
        code = code_list[0]
        url = f"{base_url}/{code}"
        title, images = fetch_images(url)
        if not images:
            return f"No se encontraron imágenes en {url}"
        cbz = create_cbz(title, code, images)
        return serve_and_clean(cbz)

    # Si son varios, mostrar enlaces de descarga
    links = []
    for code in code_list:
        url = f"{base_url}/{code}"
        title, images = fetch_images(url)
        if images:
            cbz = create_cbz(title, code, images)
            links.append(f"<li><a href='/get/{os.path.basename(cbz)}'>{os.path.basename(cbz)}</a></li>")

    if not links:
        return "No se generó ningún archivo."
    return render_template_string(f"<html><body><h3>Descargas múltiples:</h3><ul>{''.join(links)}</ul></body></html>")


@app.route("/get/<filename>")
def get_cbz(filename):
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(path):
        return serve_and_clean(path)
    return "Archivo no encontrado"

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

