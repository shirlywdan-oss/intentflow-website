from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse


SEARCH_PAGE = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Demo Store - Search</title>
</head>
<body>
    <header>
        <form role="search" action="/search" method="get">
            <input type="search" name="q" value="{query}">
            <button type="submit">Cari</button>
        </form>
    </header>
    <main>
        <h1>Hasil pencarian untuk "{query}"</h1>
        {content}
    </main>
    <footer>
        <p>© 2024 Demo Store. All rights reserved.</p>
    </footer>
</body>
</html>
"""

RESULTS_CONTENT = """
<p class="results-count">Menampilkan 8 produk ditemukan</p>
<div class="search-results">
    <article class="product-card">
        <a href="/produk/item-1">
            <img src="https://demo-cdn.com/item1.jpg" alt="Demo Product 1">
            <h3 class="product-title">Demo Product 1</h3>
        </a>
        <span class="price">Rp 100.000</span>
    </article>
</div>
"""

NO_RESULTS_CONTENT = """
<div class="no-results">
    <p>Maaf, produk tidak ditemukan. Silakan coba kata kunci lain.</p>
</div>
"""

HOME_PAGE = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Demo Beauty Store</title>
</head>
<body>
    <header>
        <a href="/"><img src="/logo.png" alt="DemoBeauty"></a>
        <form role="search" action="/search" method="get">
            <input type="search" name="q">
            <button type="submit">Cari</button>
        </form>
    </header>
    <main>
        <h1>Selamat datang di Demo Beauty Store</h1>
        <section class="featured-products">
            <article class="product-card">
                <a href="/produk/somethinc-serum">
                    <img src="https://demo-cdn.com/somethinc.jpg" alt="Somethinc Serum">
                    <h3 class="product-title">Somethinc Niacinamide Serum</h3>
                </a>
                <span class="price">Rp 149.000</span>
            </article>
            <article class="product-card">
                <a href="/produk/wardah-sunscreen">
                    <img src="https://demo-cdn.com/wardah.jpg" alt="Wardah Sunscreen">
                    <h3 class="product-title">Wardah UV Shield SPF 50</h3>
                </a>
                <span class="price">Rp 79.000</span>
            </article>
        </section>
    </main>
    <footer>
        <p>© 2024 DemoBeauty. All rights reserved.</p>
    </footer>
</body>
</html>
"""

FOUND_KEYWORDS = [
    "somethinc", "wardah", "emina", "make over", "pixy",
    "serum", "moisturizer", "toner", "sunscreen", "cleanser",
]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)
        query = query_params.get("q", [""])[0].lower()

        if path == "/" or path == "/index.html":
            self._respond(200, HOME_PAGE)
        elif path == "/search":
            if any(k in query for k in FOUND_KEYWORDS):
                content = RESULTS_CONTENT
            else:
                content = NO_RESULTS_CONTENT
            html = SEARCH_PAGE.format(query=query, content=content)
            self._respond(200, html)
        elif path.startswith("/produk/"):
            self._respond(200, f"<html><head><title>{path}</title></head><body><h1>Product Detail</h1></body></html>")
        else:
            self._respond(404, "<html><body>Not Found</body></html>")

    def do_HEAD(self):
        self.send_response(200 if self.path in ["/", "/index.html"] else 404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def _respond(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 9002), Handler)
    print("Report test server running on http://127.0.0.1:9002")
    server.serve_forever()
