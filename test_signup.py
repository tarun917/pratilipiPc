import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pratilipiPc.settings')
django.setup()

from authDesk.serializers import UserSerializer
from rest_framework.test import APIRequestFactory
from authDesk.views import SignupView
import json

# Test data
data = {
    "username": "testuser123",
    "email": "testuser123@example.com",
    "password": "test123",
    "full_name": "Test User",
    "mobile_number": "",
    "terms_accepted": "true"
}

print("=" * 50)
print("Testing Signup Endpoint")
print("=" * 50)

# Test 1: Serializer validation
print("\n1. Testing Serializer:")
serializer = UserSerializer(data=data)
print(f"   Valid: {serializer.is_valid()}")
if not serializer.is_valid():
    print(f"   Errors: {serializer.errors}")
else:
    print(f"   Validated data: {serializer.validated_data}")

# Test 2: View with APIRequestFactory
print("\n2. Testing View:")
try:
    factory = APIRequestFactory()
    request = factory.post('/api/auth/signup/', data, format='json')
    view = SignupView.as_view()
    response = view(request)
    print(f"   Status Code: {response.status_code}")
    print(f"   Response Data: {response.data}")
except Exception as e:
    print(f"   ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
