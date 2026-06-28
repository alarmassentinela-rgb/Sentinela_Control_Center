#!/usr/bin/env python3
"""Cliente CLI de la Catalog Public Interface (consumidor de PRUEBA, independiente de Odoo).
Demuestra que la API se consume solo con HTTP + la API key, leyendo la documentación.

Uso:
  python3 catalog_cli.py --base http://host:8075 --key <APIKEY> health
  python3 catalog_cli.py --base ... --key ... search --q camara --page 1
  python3 catalog_cli.py --base ... --key ... get <ref>
  python3 catalog_cli.py --base ... --key ... promote <ref> --idem abc123
"""
import argparse, json, sys, urllib.parse, urllib.request

def call(base, path, key=None, method="GET", params=None, headers=None):
    url = base.rstrip("/") + path + (("?" + urllib.parse.urlencode(params)) if params else "")
    req = urllib.request.Request(url, method=method)
    if key:
        req.add_header("X-API-Key", key)
    req.add_header("Accept-Encoding", "gzip")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                import gzip; raw = gzip.decompress(raw)
            return r.status, r.headers.get("X-Request-ID"), json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("X-Request-ID"), json.loads(e.read().decode("utf-8") or "{}")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True); p.add_argument("--key")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health"); sub.add_parser("openapi")
    s = sub.add_parser("search"); s.add_argument("--q"); s.add_argument("--brand"); s.add_argument("--page", default="1"); s.add_argument("--sort", default="id")
    g = sub.add_parser("get"); g.add_argument("ref")
    pr = sub.add_parser("promote"); pr.add_argument("ref"); pr.add_argument("--idem")
    a = p.parse_args()
    if a.cmd == "health":
        st, rid, body = call(a.base, "/catalog/api/v1/health")
    elif a.cmd == "openapi":
        st, rid, body = call(a.base, "/catalog/api/v1/openapi.json")
    elif a.cmd == "search":
        params = {k: v for k, v in {"q": a.q, "brand": a.brand, "page": a.page, "sort": a.sort}.items() if v}
        st, rid, body = call(a.base, "/catalog/api/v1/products", a.key, params=params)
    elif a.cmd == "get":
        st, rid, body = call(a.base, "/catalog/api/v1/products/%s" % a.ref, a.key)
    elif a.cmd == "promote":
        st, rid, body = call(a.base, "/catalog/api/v1/products/%s/promote" % a.ref, a.key,
                             method="POST", headers={"Idempotency-Key": a.idem} if a.idem else None)
    print("HTTP", st, "| X-Request-ID", rid)
    print(json.dumps(body, indent=2, ensure_ascii=False)[:1500])
    sys.exit(0 if st < 400 else 1)

if __name__ == "__main__":
    main()
