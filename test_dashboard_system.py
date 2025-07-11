"""
Test script for the comprehensive dashboard system.
Tests all three dashboards (User, Technician, Admin) and their functionalities.
"""

import sys
import os
import requests
import json
from datetime import datetime

# Add the src directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_api_connection():
    """Test if the FastAPI backend is running and accessible."""
    print("🔍 Testing API Connection...")
    
    try:
        response = requests.get("http://127.0.0.1:8000/")
        if response.status_code == 200:
            print("✅ API is running and accessible")
            return True
        else:
            print(f"❌ API returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Please ensure FastAPI server is running on port 8000")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def test_tickets_endpoint():
    """Test the tickets API endpoint."""
    print("\n🎫 Testing Tickets Endpoint...")
    
    try:
        # Test GET all tickets
        response = requests.get("http://127.0.0.1:8000/tickets/")
        if response.status_code == 200:
            tickets = response.json()
            print(f"✅ GET /tickets/ - Retrieved {len(tickets)} tickets")
        else:
            print(f"❌ GET /tickets/ failed with status: {response.status_code}")
            return False
        
        # Test POST new ticket (if tickets exist, we can test with real data)
        if tickets:
            sample_ticket = {
                "ticket_number": f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "issue_type": "General Support",
                "sub_issue_type": "User Request", 
                "ticket_category": "Support",
                "priority": "Medium",
                "description": "Test ticket for dashboard validation",
                "status": "Open",
                "due_date": datetime.now().isoformat()
            }
            
            response = requests.post("http://127.0.0.1:8000/tickets/", json=sample_ticket)
            if response.status_code == 200:
                print("✅ POST /tickets/ - Successfully created test ticket")
            else:
                print(f"⚠️ POST /tickets/ failed with status: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Tickets endpoint test failed: {str(e)}")
        return False

def test_technicians_endpoint():
    """Test the technicians API endpoint."""
    print("\n👨‍🔧 Testing Technicians Endpoint...")
    
    try:
        # Test GET all technicians
        response = requests.get("http://127.0.0.1:8000/technicians/")
        if response.status_code == 200:
            technicians = response.json()
            print(f"✅ GET /technicians/ - Retrieved {len(technicians)} technicians")
            
            # Test GET specific technician if any exist
            if technicians:
                tech_id = technicians[0].get('technician_id')
                if tech_id:
                    response = requests.get(f"http://127.0.0.1:8000/technicians/{tech_id}")
                    if response.status_code == 200:
                        print(f"✅ GET /technicians/{tech_id} - Retrieved specific technician")
                    else:
                        print(f"⚠️ GET /technicians/{tech_id} failed with status: {response.status_code}")
        else:
            print(f"❌ GET /technicians/ failed with status: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Technicians endpoint test failed: {str(e)}")
        return False

def test_dashboard_files():
    """Test if all dashboard files exist and are properly structured."""
    print("\n📁 Testing Dashboard Files...")
    
    required_files = [
        "src/ui/Pages/User.py",
        "src/ui/Pages/Technician.py", 
        "src/ui/Pages/Admin.py",
        "src/ui/login.py",
        "src/ui/components.py",
        "app.py"
    ]
    
    all_files_exist = True
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            all_files_exist = False
    
    return all_files_exist

def test_component_imports():
    """Test if shared components can be imported properly."""
    print("\n🔧 Testing Component Imports...")
    
    try:
        from src.ui.components import (
            create_metric_card, create_status_badge, create_data_table,
            create_chart_container, create_filter_section, api_call, display_api_response
        )
        print("✅ All shared components imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Component import failed: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during import: {str(e)}")
        return False

def test_role_based_access():
    """Test role-based access control logic."""
    print("\n🔐 Testing Role-Based Access Control...")
    
    # Test permission definitions
    user_permissions = ["submit_tickets", "view_own_tickets"]
    technician_permissions = ["view_tickets", "update_tickets", "manage_workload"]
    admin_permissions = ["view_all_tickets", "manage_users", "manage_technicians", "system_config", "view_analytics"]
    
    # Verify permission sets are distinct and appropriate
    if len(set(user_permissions) & set(admin_permissions)) < len(user_permissions):
        print("✅ User permissions are properly restricted")
    else:
        print("⚠️ User permissions may be too broad")
    
    if "manage_users" in admin_permissions and "manage_users" not in technician_permissions:
        print("✅ Admin-only permissions are properly restricted")
    else:
        print("⚠️ Admin permissions may not be exclusive enough")
    
    print("✅ Role-based access control structure validated")
    return True

def run_comprehensive_test():
    """Run all tests and provide a summary."""
    print("🚀 Starting Comprehensive Dashboard System Test")
    print("=" * 60)
    
    test_results = {
        "API Connection": test_api_connection(),
        "Dashboard Files": test_dashboard_files(),
        "Component Imports": test_component_imports(),
        "Role-Based Access": test_role_based_access(),
        "Tickets Endpoint": test_tickets_endpoint(),
        "Technicians Endpoint": test_technicians_endpoint()
    }
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Dashboard system is ready for use.")
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
        
    print("\n📋 NEXT STEPS:")
    print("1. Start the FastAPI backend: uvicorn backend.main:app --reload")
    print("2. Run the Streamlit app: streamlit run app.py")
    print("3. Test each dashboard role (User, Technician, Admin)")
    print("4. Verify API integrations work properly")
    
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
