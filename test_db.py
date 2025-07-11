#!/usr/bin/env python3
"""
Test script to check Snowflake database connection and see what tickets exist
"""

import sys
import os
sys.path.append('backend')

from backend.database import connect_snowflake, execute_query

def test_connection():
    """Test the Snowflake connection and show available tickets"""
    try:
        print("Testing Snowflake connection...")
        conn = connect_snowflake()
        print("✓ Connection successful!")

        # First, count total tickets
        print("\nCounting total tickets...")
        count_query = "SELECT COUNT(*) as total FROM TEST_DB.PUBLIC.COMPANY_4130_DATA"
        count_result = execute_query(count_query)
        if count_result:
            print(f"✓ Total tickets in database: {count_result[0]['TOTAL']}")

        # Get all tickets
        print("\nFetching all tickets...")
        query = """
        SELECT TICKETNUMBER, TITLE, STATUS, PRIORITY, CREATEDATE
        FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
        ORDER BY CREATEDATE DESC
        LIMIT 10
        """
        tickets = execute_query(query)
        
        if tickets:
            print(f"✓ Found {len(tickets)} tickets:")
            print("-" * 80)
            for ticket in tickets:
                print(f"Ticket: {ticket.get('TICKETNUMBER', 'N/A')}")
                print(f"Title: {ticket.get('TITLE', 'N/A')}")
                print(f"Status: {ticket.get('STATUS', 'N/A')}")
                print(f"Priority: {ticket.get('PRIORITY', 'N/A')}")
                print(f"Created: {ticket.get('CREATEDATE', 'N/A')}")
                print("-" * 80)
        else:
            print("✗ No tickets found")
            
        # Test specific ticket search
        print(f"\nSearching for ticket 'T20240916.0051'...")
        specific_query = """
        SELECT * FROM TEST_DB.PUBLIC.COMPANY_4130_DATA 
        WHERE TICKETNUMBER = %s
        """
        specific_ticket = execute_query(specific_query, ('T20240916.0051',))
        
        if specific_ticket:
            print("✓ Found the specific ticket!")
            print(specific_ticket[0])
        else:
            print("✗ Specific ticket not found")
            
            # Try case-insensitive search
            print("\nTrying case-insensitive search...")
            case_insensitive_query = """
            SELECT TICKETNUMBER FROM TEST_DB.PUBLIC.COMPANY_4130_DATA 
            WHERE UPPER(TICKETNUMBER) = UPPER(%s)
            """
            case_result = execute_query(case_insensitive_query, ('T20240916.0051',))
            
            if case_result:
                print("✓ Found with case-insensitive search!")
                print(case_result[0])
            else:
                print("✗ Still not found with case-insensitive search")
                
                # Show tickets that contain similar pattern
                print("\nSearching for tickets containing '20240916'...")
                pattern_query = """
                SELECT TICKETNUMBER FROM TEST_DB.PUBLIC.COMPANY_4130_DATA 
                WHERE TICKETNUMBER LIKE '%20240916%'
                LIMIT 5
                """
                pattern_results = execute_query(pattern_query)
                
                if pattern_results:
                    print("✓ Found tickets with similar pattern:")
                    for result in pattern_results:
                        print(f"  - {result['TICKETNUMBER']}")
                else:
                    print("✗ No tickets found with similar pattern")
        
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_connection()
