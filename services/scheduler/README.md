# Scheduler-Vertrag

Interactive Playback nutzt Priorität `0`; Hintergrundaufträge einen höheren
Wert. Die Entwicklungsimplementierung verarbeitet jeweils einen Auftrag. Bei
Redis/PostgreSQL-Einsatz bleibt PostgreSQL die maßgebliche Auftragsquelle und
Worker müssen wiederholte Zustellungen idempotent behandeln.
