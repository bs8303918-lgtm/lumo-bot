import sqlite3

conn = sqlite3.connect("lumo.db")
cur = conn.cursor()
try:
    cur.execute(
        "SELECT COUNT(*) FROM promo_campaign_deliveries WHERE campaign_slug=?",
        ("kbtu_startup_camp",),
    )
    print("deliveries:", cur.fetchone()[0])
except Exception as e:
    print("deliveries table:", e)
try:
    cur.execute(
        "SELECT event_type, COUNT(*) FROM events "
        "WHERE metadata_json LIKE '%kbtu_startup_camp%' GROUP BY event_type"
    )
    for row in cur.fetchall():
        print(row)
except Exception as e:
    print("events:", e)
conn.close()
