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

def callback(request):
    code = request.GET.get('code')
    location_id = request.GET.get('locationId')  # Try to get locationId from URL
    if not code:
        return render(request, 'error.html', {'message': 'Authorization code not received'})

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

    # Check token response for locationId if not in URL
    if not location_id:
        location_id = token_data.get('locationId') or token_data.get('location_id')
        if not location_id:
            print("Token Response:", token_data)
            return render(request, 'error.html', {
                'message': 'Location ID not received in callback URL or token response. Please ensure the OAuth flow prompts for location selection and the app is configured for Location user type.'
            })

    print("Access Token:", access_token)
    print("Refresh Token:", refresh_token)
    print("Location ID:", location_id)
    print("Token Response:", token_data)

    request.session['access_token'] = access_token
    request.session['refresh_token'] = refresh_token
    request.session['location_id'] = location_id

    return redirect('update_contact')

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
        print("Refresh Token Error:", response.status_code, response.text)
        return None

def update_contact(request):
    access_token = request.session.get('access_token')
    refresh_token = request.session.get('refresh_token')
    location_id = request.session.get('location_id')

    if not access_token:
        return render(request, 'error.html', {'message': 'No access token found'})
    if not location_id:
        return render(request, 'error.html', {'message': 'No location ID found. Please re-authenticate and select a location.'})

    # Step 1: Fetch a random contact
    contacts_url = "https://services.leadconnectorhq.com/contacts/"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Version': '2021-04-15',
        'Accept': 'application/json'
    }
    params = {
        'limit': 10,
        'locationId': location_id
    }

    response = requests.get(contacts_url, headers=headers, params=params)
    if response.status_code == 401:  # Token expired
        token_data = refresh_access_token(refresh_token)
        if not token_data:
            return render(request, 'error.html', {'message': 'Failed to refresh access token'})
        access_token = token_data['access_token']
        request.session['access_token'] = access_token
        request.session['refresh_token'] = token_data['refresh_token']
        headers['Authorization'] = f'Bearer {access_token}'
        response = requests.get(contacts_url, headers=headers, params=params)

    if response.status_code == 403:
        print("Contacts Error:", response.status_code, response.text)
        return render(request, 'error.html', {
            'message': 'Access denied: The token does not have access to this location. Please ensure the correct location is selected and the app has the required scopes (contacts.readonly, contacts.write, locations/customFields.readonly).'
        })

    if response.status_code != 200:
        print("Contacts Error:", response.status_code, response.text)
        return render(request, 'error.html', {'message': f'Failed to fetch contacts: {response.text}'})

    contacts_data = response.json()
    contacts = contacts_data.get('contacts', [])
    if not contacts:
        return render(request, 'error.html', {'message': 'No contacts found in this location'})

    random_contact = random.choice(contacts)
    contact_id = random_contact['id']
    contact_email = random_contact.get('email', 'Unknown')

    # Step 2: Fetch custom fields
    custom_fields_url = f"https://services.leadconnectorhq.com/locations/{location_id}/customFields"
    response = requests.get(custom_fields_url, headers=headers)
    if response.status_code != 200:
        print("Custom Fields Error:", response.status_code, response.text)
        return render(request, 'error.html', {'message': f'Failed to fetch custom fields: {response.text}'})

    custom_fields = response.json().get('customFields', [])
    custom_field_id = None
    for field in custom_fields:
        if field.get('name') == "DFS Booking Zoom Link":
            custom_field_id = field['id']
            break

    if not custom_field_id:
        return render(request, 'error.html', {'message': 'Custom field "DFS Booking Zoom Link" not found'})

    # Step 3: Update the contact's custom field
    update_contact_url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
    payload = {
        'customFields': [
            {
                'id': custom_field_id,
                'value': 'TEST'
            }
        ]
    }  # Removed locationId from payload

    response = requests.put(update_contact_url, headers=headers, json=payload)
    if response.status_code != 200:
        print("Update Contact Error:", response.status_code, response.text)
        return render(request, 'error.html', {'message': f'Failed to update contact: {response.text}'})

    return render(request, 'success.html', {
        'message': f'Successfully updated contact {contact_email} with custom field "DFS Booking Zoom Link" set to "TEST"'
    })