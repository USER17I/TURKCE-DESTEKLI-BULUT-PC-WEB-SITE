import http.server, socketserver, os, urllib, html, subprocess

PORT = 8080
KULLANICI = "root"
SIFRE = "root"
BASLANGIC_YOLU = "/home/linuxlite"
session = {"giris": False, "cwd": BASLANGIC_YOLU}

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if not session["giris"]:
            return self.login_sayfasi()
        if self.path.startswith("/logout"):
            session["giris"] = False
            session["cwd"] = BASLANGIC_YOLU
            return self.redirect("/")
        if self.path.startswith("/run"):
            return self.terminal_sayfasi()
        elif self.path.startswith("/file/"):
            filepath = urllib.parse.unquote(self.path[len("/file/"):])
            filepath = os.path.join(session["cwd"], filepath)
            if os.path.isfile(filepath):
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f"attachment; filename={os.path.basename(filepath)}")
                self.end_headers()
                with open(filepath, 'rb') as f:
                    self.wfile.write(f.read())
                return
            elif os.path.isdir(filepath):
                session["cwd"] = filepath
        self.dosya_paneli()

    def do_POST(self):
        if not session["giris"]:
            uzunluk = int(self.headers['Content-Length'])
            veri = self.rfile.read(uzunluk).decode()
            form = urllib.parse.parse_qs(veri)
            if form.get("kadi", [""])[0] == KULLANICI and form.get("sifre", [""])[0] == SIFRE:
                session["giris"] = True
                session["cwd"] = BASLANGIC_YOLU
            return self.redirect("/")

        if self.path == "/upload":
            content_length = int(self.headers['Content-Length'])
            content_type = self.headers.get("Content-Type")
            boundary = content_type.split("boundary=")[1].encode()
            remain = content_length
            line = self.rfile.readline(); remain -= len(line)

            if boundary not in line:
                self.send_error(400, "Form hatalı")
                return

            line = self.rfile.readline(); remain -= len(line)
            if b'filename="' not in line:
                self.send_error(400, "Dosya adı alınamadı")
                return
            filename = line.decode().split('filename="')[1].split('"')[0]
            filename = os.path.basename(filename)

            self.rfile.readline(); remain -= len(line)
            self.rfile.readline(); remain -= len(line)

            dosya_yolu = os.path.join(session["cwd"], filename)
            with open(dosya_yolu, 'wb') as f:
                while True:
                    line = self.rfile.readline()
                    remain -= len(line)
                    if boundary in line:
                        break
                    f.write(line)

            return self.redirect("/")

        if self.path == "/run":
            uzunluk = int(self.headers['Content-Length'])
            veri = self.rfile.read(uzunluk).decode()
            komut = urllib.parse.parse_qs(veri).get("komut", [""])[0].strip()

            cikti = ""
            if komut.startswith("cd "):
                hedef = komut[3:].strip()
                yeni_yol = os.path.abspath(os.path.join(session["cwd"], hedef))
                if os.path.isdir(yeni_yol):
                    session["cwd"] = yeni_yol
                    cikti = f"Dizin değiştirildi: {yeni_yol}"
                else:
                    cikti = f"Dizin bulunamadı: {yeni_yol}"
            else:
                try:
                    sonuc = subprocess.run(komut, shell=True, cwd=session["cwd"], capture_output=True, text=True, timeout=5)
                    cikti = sonuc.stdout + sonuc.stderr
                except subprocess.TimeoutExpired:
                    cikti = "⚠️ Komut zaman aşımına uğradı."

            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(cikti.encode("utf-8"))

    def login_sayfasi(self):
        self.respond("""
        <html><head><title>Giriş</title>
        <style>
        body{background:linear-gradient(to right,#2193b0,#6dd5ed);font-family:sans-serif;color:white;text-align:center;margin-top:100px}
        input{padding:10px;margin:5px;border-radius:10px;border:none}
        .footer{position:fixed;bottom:10px;right:10px;color:white;font-size:12px}
        </style></head><body>
        <h2>🔐 Giriş</h2>
        <form method="post"><input name="kadi" placeholder="Kullanıcı Adı"><br>
        <input name="sifre" type="password" placeholder="Şifre"><br>
        <input type="submit" value="Giriş"></form>
        <div class="footer">TRONIXY TECH TARAFINDAN YAPILMIŞTIR</div>
        </body></html>
        """)

    def dosya_paneli(self):
        yol = session["cwd"]
        try:
            liste = ""
            if os.path.abspath(yol) != "/":
                liste += f'<a href="/file/{urllib.parse.quote("..")}">⬆️ Üst Dizin</a><br>'
            for i in os.listdir(yol):
                tam = os.path.join(yol, i)
                url = f"/file/{urllib.parse.quote(i)}"
                liste += f'<a href="{url}">{"📁" if os.path.isdir(tam) else "📄"} {html.escape(i)}</a><br>'
        except:
            liste = "Erişim yok veya klasör bulunamadı."

        yukle_formu = """
        <form method="post" enctype="multipart/form-data" action="/upload">
            <input type="file" name="dosya">
            <input type="submit" value="📤 Yükle">
        </form><br>
        """

        self.respond(f"""
        <html><head><title>Dosya Paneli</title>
        <style>
        body{{background:linear-gradient(to right,#2193b0,#6dd5ed);font-family:sans-serif;color:white;padding:20px}}
        input{{padding:10px;margin:5px;border-radius:10px;border:none}}
        .footer{{position:fixed;bottom:10px;right:10px;color:white;font-size:12px}}
        </style></head><body>
        <h2>📁 Dosya Paneli</h2>
        Aktif Dizin: {html.escape(session['cwd'])}<br><br>
        {yukle_formu}
        {liste}<br>
        <a href="/run">🖥 Terminal</a> | <a href="/logout">🚪 Çıkış</a>
        <div class="footer">TRONIXY TECH TARAFINDAN YAPILMIŞTIR</div>
        </body></html>
        """)

    def terminal_sayfasi(self):
        self.respond(f"""
        <html><head><title>Terminal</title>
        <script>
        function gonder() {{
            var komut = document.getElementById('komut').value;
            document.getElementById('komut').value = "";
            fetch('/run', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                body: 'komut=' + encodeURIComponent(komut)
            }}).then(r => r.text()).then(data => {{
                let cikti = document.getElementById('sonuc');
                cikti.innerText += '$ ' + komut + '\\n' + data + '\\n';
                cikti.scrollTop = cikti.scrollHeight;
            }});
            return false;
        }}
        </script>
        <style>
        body{{background:#000;color:lime;font-family:monospace;padding:10px}}
        input{{background:#111;color:white;border:none;padding:10px;width:90%}}
        #sonuc{{height:400px;overflow:auto;border:1px solid #444;margin-top:10px;padding:10px;background:#111}}
        .footer{{position:fixed;bottom:10px;right:10px;color:gray;font-size:12px}}
        </style></head><body>
        <h2>🖥 Terminal</h2>
        <form onsubmit="return gonder()">
            <input id="komut" placeholder="Komut yaz">
        </form>
        <pre id="sonuc"></pre>
        <br><a href="/">📁 Dosya Paneli</a>
        <div class="footer">TRONIXY TECH TARAFINDAN YAPILMIŞTIR</div>
        </body></html>
        """)

    def respond(self, html):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

socketserver.TCPServer(("", PORT), Handler).serve_forever()
