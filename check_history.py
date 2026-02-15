import sys
from src.db import get_connection

def check_history(external_id):
    print(f"Checking history for patient: {external_id}")
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get internal ID
    cursor.execute("SELECT id, name FROM patients_new WHERE external_id = %s", (external_id,))
    pat = cursor.fetchone()
    if not pat:
        print("❌ Patient not found in DB.")
        return

    print(f"✅ Found patient: ID={pat['id']}, Name={pat['name']}")
    
    # Get reports
    cursor.execute("SELECT id, report_date FROM reports WHERE patient_id = %s ORDER BY report_date DESC", (pat['id'],))
    reports = cursor.fetchall()
    print(f"📊 Found {len(reports)} reports:")
    for r in reports:
        print(f"   - ID: {r['id']}, Date: {r['report_date']}")
        
        # Get count of results for this report
        cursor.execute("SELECT count(*) as cnt FROM test_results WHERE report_id = %s", (r['id'],))
        row = cursor.fetchone()
        print(f"     -> {row['cnt']} test results")
        
        # Show a few sample tests
        cursor.execute("SELECT code, value, unit FROM test_results WHERE report_id = %s LIMIT 3", (r['id'],))
        tests = cursor.fetchall()
        for t in tests:
            print(f"        * {t['code']}: {t['value']} {t['unit']}")

    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_history.py <patient_id>")
        sys.exit(1)
    check_history(sys.argv[1])
