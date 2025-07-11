#!/usr/bin/env python3
"""
Test script to verify all imports work correctly after restructuring.
"""

def test_imports():
    """Test all the main imports."""
    print("🧪 Testing imports after restructuring...")
    print("=" * 50)
    
    try:
        print("1. Testing config import...")
        from config import *
        print(f"   ✅ Config loaded - Data file: {DATA_REF_FILE}")
        
        print("2. Testing agents import...")
        from src.agents import IntakeClassificationAgent
        print("   ✅ IntakeClassificationAgent imported")
        
        print("3. Testing data manager import...")
        from src.data import DataManager
        print("   ✅ DataManager imported")
        
        print("4. Testing UI components import...")
        from src.ui import apply_custom_css
        print("   ✅ UI components imported")
        
        print("5. Testing processors import...")
        from src.processors import AIProcessor
        print("   ✅ Processors imported")
        
        print("6. Testing database import...")
        from src.database import SnowflakeConnection
        print("   ✅ Database imported")
        
        print("\n" + "=" * 50)
        print("🎉 All imports successful! The restructuring is working correctly.")
        print("✅ You can now run: streamlit run app.py")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        print("🔧 Need to fix import issues...")
        return False

if __name__ == "__main__":
    test_imports()
