import requests

def check_syscom_tc():
    client_id = 'AE2U6oagC6BZVCSjASwFBUIGkj8M4Hjg'
    client_secret = 'ERWZPV4vYQfWwDt5QGcYqyZb6Zmzc4p2b7iO4Ld5'
    
    # 1. Obtener Token
    token_url = "https://developers.syscom.mx/oauth/token"
    res = requests.post(token_url, data={
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    })
    token = res.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}'}

    # 2. Consultar Tipo de Cambio
    # Syscom tiene un endpoint específico para esto
    api_url = 'https://developers.syscom.mx/api/v1/tipocambio'
    res_tc = requests.get(api_url, headers=headers)
    
    if res_tc.status_code == 200:
        data = res_tc.json()
        print(f"SYSCOM_TC_DATA: {data}")
    else:
        print(f"ERROR_API: {res_tc.status_code} - {res_tc.text}")

check_syscom_tc()
