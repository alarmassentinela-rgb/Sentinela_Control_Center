#!/usr/bin/env python3
"""Normaliza el telefono (y email placeholder del header) SOLO en el sitio SentiCar (id=5).
- Header: COW del website.header_text_element (global 2187) -> copia website_id=5.
- Footer 2860 y Contactus 2858 (ya son site-5): reemplazo in-place.
Canonico: display '+52 868-8225875', tel 'tel:+528688225875', email gps@senticar.com.
Idempotente."""
import xmlrpc.client
URL='http://192.168.3.2:8070'; DB='Sentinela_V18'; USER='api_user'; PWD='SentinelaBot2026!'
WID=5
c=xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common'); uid=c.authenticate(DB,USER,PWD,{})
m=xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
def ex(model,meth,args,kw=None): return m.execute_kw(DB,uid,PWD,model,meth,args,kw or {})

TEL='tel:+528688225875'; DISP='+52 868-8225875'; MAIL='gps@senticar.com'
def norm(a):
    for s in ['tel:+1 555-555-5556','tel:+1555-555-5556','tel:+55868-822-5875','tel:+52 868-8225875']:
        a=a.replace(s,TEL)
    for s in ['+1 555-555-5556','+55868-822-5875','868-822-5875','868 8225875','868 822 5875']:
        a=a.replace(s,DISP)
    a=a.replace('info@yourcompany.example.com',MAIL).replace('mailto:'+MAIL,'mailto:'+MAIL)
    return a

# 1) Header COW para website 5
hdr=ex('ir.ui.view','read',[[2187],['arch_db','inherit_id','mode','key']])[0]
new_arch=norm(hdr['arch_db'])
existing=ex('ir.ui.view','search',[[['key','=','website.header_text_element'],['website_id','=',WID]]])
if existing:
    ex('ir.ui.view','write',[existing,{'arch_db':new_arch,'active':True}]); print('[=] header COW actualizado',existing)
else:
    nid=ex('ir.ui.view','create',[{'name':'Header Text element','key':'website.header_text_element',
        'inherit_id':hdr['inherit_id'][0],'mode':'extension','website_id':WID,'arch_db':new_arch,'active':True}])
    print('[+] header COW creado',nid)

# 2) Footer + Contactus (site-5)
for vid in (2860,2858):
    a=ex('ir.ui.view','read',[[vid],['arch_db']])[0]['arch_db']
    na=norm(a)
    if na!=a:
        ex('ir.ui.view','write',[[vid],{'arch_db':na}]); print(f'[=] vista {vid} normalizada')
    else:
        print(f'[ ] vista {vid} sin cambios')
print('OK')
