"""
Test script to validate the Technician API endpoints
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_technician_endpoints():
    """Test all technician CRUD operations"""
    
    # Test data for creating a technician
    technician_data = {
        "technician_id": "TECH-001",
        "name": "John Smith",
        "email": "john.smith@company.com",
        "role": "Senior Technician",
        "skills": "Windows, Linux, Network Troubleshooting, Hardware Repair",
        "availability_status": "Available",
        "current_workload": "5",
        "specializations": "Desktop Support, Network Infrastructure"
    }
    
    print("🧪 Testing Technician API Endpoints")
    print("=" * 50)
    
    # Test 1: GET all technicians
    print("\n1. Testing GET /technicians/")
    try:
        response = requests.get(f"{BASE_URL}/technicians/")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: POST create technician
    print("\n2. Testing POST /technicians/")
    try:
        response = requests.post(
            f"{BASE_URL}/technicians/", 
            json=technician_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"   Created Technician: {response.json()}")
        else:
            print(f"   Error Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: GET specific technician
    print(f"\n3. Testing GET /technicians/{technician_data['technician_id']}")
    try:
        response = requests.get(f"{BASE_URL}/technicians/{technician_data['technician_id']}")
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"   Technician Data: {response.json()}")
        else:
            print(f"   Error Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: PUT update technician
    print(f"\n4. Testing PUT /technicians/{technician_data['technician_id']}")
    update_data = {
        "name": "John Smith Updated",
        "availability_status": "Busy"
    }
    try:
        response = requests.put(
            f"{BASE_URL}/technicians/{technician_data['technician_id']}", 
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"   Updated Technician: {response.json()}")
        else:
            print(f"   Error Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 5: DELETE technician
    print(f"\n5. Testing DELETE /technicians/{technician_data['technician_id']}")
    try:
        response = requests.delete(f"{BASE_URL}/technicians/{technician_data['technician_id']}")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")

def test_tickets_with_company_filter():
    """Test tickets endpoint with company filter"""
    print("\n\n🎫 Testing Tickets API with Company Filter")
    print("=" * 50)
    
    # Test tickets without filter
    print("\n1. Testing GET /tickets/ (no filter)")
    try:
        response = requests.get(f"{BASE_URL}/tickets/")
        print(f"   Status Code: {response.status_code}")
        tickets = response.json()
        print(f"   Number of tickets: {len(tickets)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test tickets with company filter
    print("\n2. Testing GET /tickets/?company_id=4130")
    try:
        response = requests.get(f"{BASE_URL}/tickets/?company_id=4130")
        print(f"   Status Code: {response.status_code}")
        tickets = response.json()
        print(f"   Number of tickets for company 4130: {len(tickets)}")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    print("🚀 Starting API Tests...")
    test_technician_endpoints()
    test_tickets_with_company_filter()
    print("\n✅ Tests completed!")
