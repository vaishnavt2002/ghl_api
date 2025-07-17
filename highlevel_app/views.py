from django.http import HttpResponse
from django.shortcuts import redirect, render
from urllib.parse import quote_plus
from django.conf import settings
import requests
import random

def login(request):
    auth_url = (
        "https://marketplace.gohighlevel.com/oauth/chooselocation"
        f"?response_type=code"
        f"&redirect_uri={quote_plus(settings.HIGHLEVEL_REDIRECT_URI)}"
        f"&client_id={settings.HIGHLEVEL_CLIENT_ID}"
        f"&scope=contacts.readonly%20contacts.write%20locations/customFields.readonly"
    )
    return redirect(auth_url)

def home(request):
    access_token = request.session.get('access_token')
    if access_token:
        return render(request, 'dashboard.html')
    return redirect('login')
def callback(request):
    code = request.GET.get('code')
    if not code:
        return render(request, 'error.html', {'message': 'You can login here to continue....', 'show_login': True,'noError':True})

    token_url = "https://services.leadconnectorhq.com/oauth/token"

    payload = {
        'client_id': settings.HIGHLEVEL_CLIENT_ID,
        'client_secret': settings.HIGHLEVEL_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.HIGHLEVEL_REDIRECT_URI,
        'user_type': 'Location'
    }

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(token_url, data=payload, headers=headers)

    if response.status_code != 200:
        print("Token Error:", response.status_code, response.text)
        return render(request, 'error.html', {'message': f'Failed to obtain access token: {response.text}'})

    token_data = response.json()
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')
    location_id = token_data.get('locationId')

    request.session['access_token'] = access_token
    request.session['refresh_token'] = refresh_token
    request.session['location_id'] = location_id

    return redirect('home')

def refresh_access_token(refresh_token):
    url = "https://services.leadconnectorhq.com/oauth/token"
    
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': settings.HIGHLEVEL_CLIENT_ID,
        'client_secret': settings.HIGHLEVEL_CLIENT_SECRET,
        'user_type': 'Location'
    }

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(url, data=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return {'access_token': data.get('access_token'), 'refresh_token': data.get('refresh_token')}
    else:
        return None

def update_contact(request):
    access_token = request.session.get('access_token')
    refresh_token = request.session.get('refresh_token')
    location_id = request.session.get('location_id')

    if not access_token:
        return render(request, 'error.html', {'message': 'No access token. Please login........', 'show_login': True})
    if not location_id:
        return render(request, 'error.html', {'message': 'No location id. Please login........', 'show_login': True})
    
    #Fetching  contacts
    contacts_url = "https://services.leadconnectorhq.com/contacts/"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Version': '2021-07-28',
        'Accept': 'application/json'
    }
    params = {
        'locationId': location_id
    }

    response = requests.get(contacts_url, headers=headers, params=params)
    if response.status_code == 401:
        token_data = refresh_access_token(refresh_token)
        if not token_data:
            return redirect('login')
        access_token = token_data['access_token']
        request.session['access_token'] = access_token
        request.session['refresh_token'] = token_data['refresh_token']
        headers['Authorization'] = f'Bearer {access_token}'
        response = requests.get(contacts_url, headers=headers, params=params)
    if response.status_code == 401:
        print("Contacts Error:", response.status_code, response.text)
        return render(request, 'error.html', {'message': f'Failed to fetch contacts: {response.text}', 'show_login': True})

    if response.status_code != 200:
        print("Contacts Error:", response.status_code, response.text)
        return render(request, 'error.html', {'message': f'Failed to fetch contacts: {response.text}', 'show_dashboard': True})
    
    

    contacts_data = response.json()
    contacts = contacts_data.get('contacts', [])
    if not contacts:
        return render(request, 'error.html', {'message': 'No contacts found in this location', 'show_dashboard': True})
    
    # Selecting random one from contacts
    random_contact = random.choice(contacts)
    contact_id = random_contact['id']
    contact_email = random_contact.get('email', 'Unknown')

    #Fetching custom fields
    custom_fields_url = f"https://services.leadconnectorhq.com/locations/{location_id}/customFields"
    response = requests.get(custom_fields_url, headers=headers)
    if response.status_code != 200:
        return render(request, 'error.html', {'message': f'Failed to fetch custom fields: {response.text}', 'show_dashboard': True})

    custom_fields = response.json().get('customFields', [])
    custom_field_id = None
    for field in custom_fields:
        if field.get('name') == "DFS Booking Zoom Link":
            custom_field_id = field['id']
            break

    if not custom_field_id:
        return render(request, 'error.html', {'message': 'Custom field "DFS Booking Zoom Link" not found', 'show_dashboard': True})
    
    print(contact_email)
    print(contact_id)

    #Updating the contact's custom field
    update_contact_url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
    payload = {
        'customFields': [
            {
                'id': custom_field_id,
                'value': 'TEST'
            }
        ]
    }

    response = requests.put(update_contact_url, headers=headers, json=payload)
    if response.status_code != 200:
        return render(request, 'error.html', {'message': f'Failed to update contact: {response.text}', 'show_dashboard': True})
    return render(request, 'success.html', {
        'message': f'Successfully updated contact with custom field "DFS Booking Zoom Link" set to "TEST"',
        'contact_email': contact_email,
        'contact_id': contact_id
    })

def logout(request):
    request.session.flush()
    return redirect('callback')