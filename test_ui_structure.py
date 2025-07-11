"""
Test script to verify the new UI structure works correctly.
"""

import sys
import os

# Add the src directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all UI modules can be imported successfully."""
    try:
        print("Testing login import...")
        from src.ui.login import main as login_main
        print("✅ Login import successful")
        
        print("Testing User page import...")
        from src.ui.Pages.User import main as user_main
        print("✅ User page import successful")
        
        print("Testing Technician page import...")
        from src.ui.Pages.Technician import main as technician_main
        print("✅ Technician page import successful")
        
        print("\n🎉 All imports successful! The new UI structure is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

if __name__ == "__main__":
    test_imports()
