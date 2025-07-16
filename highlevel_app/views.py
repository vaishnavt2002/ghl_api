from django.http import HttpResponse
from django.shortcuts import redirect, render
from urllib.parse import quote_plus
from django.conf import settings
import requests

# Create your views here.
def login(request):
    auth_url = (
        "https://marketplace.gohighlevel.com/oauth/chooselocation"
        f"?response_type=code"
        f"&redirect_uri={quote_plus(settings.HIGHLEVEL_REDIRECT_URI)}"
        f"&client_id={settings.HIGHLEVEL_CLIENT_ID}"
        f"&scope=contacts.readonly%20contacts.write"
    )
    return redirect(auth_url)



def callback(request):
    code = request.GET.get('code')
    if not code:
        return render(request, 'error.html', {'message': 'Authorization code not received'})

    token_url = "https://services.leadconnectorhq.com/oauth/token"

    payload = {
        'client_id': settings.HIGHLEVEL_CLIENT_ID,
        'client_secret': settings.HIGHLEVEL_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.HIGHLEVEL_REDIRECT_URI,
        'user_type': 'Location'  # or 'Agency' depending on your app scope
    }

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(token_url, data=payload, headers=headers)

    if response.status_code != 200:
        print("Token Error:", response.status_code, response.text)
        return render(request, 'error.html', {'message': 'Failed to obtain access token'})

    token_data = response.json()
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')

    print("Access Token:", access_token)
    print("Refresh Token:", refresh_token)

    request.session['access_token'] = access_token
    request.session['refresh_token'] = refresh_token

    return HttpResponse("<h1>Sucess</h1>")



def refresh_access_token(refresh_token):
    url = "https://services.leadconnectorhq.com/oauth/token"
    
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': settings.HIGHLEVEL_CLIENT_ID,
        'client_secret': settings.HIGHLEVEL_CLIENT_SECRET,
        'user_type': 'Location'  # Or 'Agency', depending on your app
    }

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    respone = requests.post(url, data=payload, headers=headers)
    if respone.status_code == 200:
        data = respone.json()
        return {'access_token':data.get('access_token'), 'refresh_token': data.get('refresh_token')}
    
    else:
        return None
    

