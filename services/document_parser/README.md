# Dokumentparser-Adapter

V1 akzeptiert TXT und Markdown direkt im API-Prozess. Dieses Verzeichnis ist
die klare Integrationsgrenze für sichere EPUB-, PDF- und DOCX-Adapter. Jeder
Adapter muss MIME-/Signaturprüfung, Größenlimits, Archivbombenschutz und einen
normalisierten Kapitelbaum liefern, bevor er an `services/segmenter` übergibt.
