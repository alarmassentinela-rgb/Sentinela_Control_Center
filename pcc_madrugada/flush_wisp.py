import routeros_api, time
pool = routeros_api.RouterOsApiPool('192.168.10.254', username='gemini_api', password='gemini_api2113', plaintext_login=True)
api=pool.get_api()
CN=api.get_resource('/ip/firewall/connection')
total=0
for rnd in range(6):
    ids=[c['id'] for c in CN.get() if (c.get('src-address','') or '').startswith('192.168.10.50')]
    if not ids: break
    for i in ids:
        try: CN.remove(id=i); total+=1
        except Exception: pass
    time.sleep(1)
print('FLUSH total removidas:', total)
pool.disconnect()
