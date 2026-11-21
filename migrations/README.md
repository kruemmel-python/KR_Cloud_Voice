# Datenbankmigrationen

Die lauffähige V1 verwendet SQLite ausschließlich für die lokale Entwicklung;
das Startschema befindet sich in `apps/api/app/db.py`. Vor einem Wechsel auf
PostgreSQL wird jede Schemaänderung hier als geordnete, reversible SQL-Datei
abgelegt. Mandantenbezogene Tabellen benötigen dabei `tenant_id`, passende
Indizes und PostgreSQL Row-Level-Security zusätzlich zur API-Prüfung.
