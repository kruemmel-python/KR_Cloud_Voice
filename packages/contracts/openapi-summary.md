# API-Vertrag V1

Alle geschützten Routen benötigen `Authorization: Bearer <access token>`.

| Methode | Route | Zweck |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | Konto anlegen |
| POST | `/api/v1/auth/login` | Zugriffstoken ausstellen |
| GET/POST | `/api/v1/projects` | Projekte lesen/anlegen |
| POST | `/api/v1/documents` | TXT/MD hochladen und segmentieren |
| GET | `/api/v1/projects/{id}/segments` | eigene Segmente lesen |
| POST | `/api/v1/generations` | Segment generieren |
| GET | `/api/v1/events` | SSE-Fortschritt |
| GET | `/api/v1/playback/{id}` | erzeugtes Audio ausliefern |
| POST | `/api/v1/exports/{project_id}` | ZIP-Export anfordern |
