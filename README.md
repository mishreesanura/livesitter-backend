# LiveSitter Backend

RTSP Livestream Overlay Web Application - Flask Backend API

## Project Structure

```
backend/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── .env.example          # Example environment file
├── config/
│   ├── __init__.py
│   ├── database.py       # MongoDB configuration
│   └── settings.py       # Application settings
├── models/
│   ├── __init__.py
│   └── overlay.py        # Overlay model/schema
└── routes/
    ├── __init__.py
    └── overlay_routes.py # Overlay API endpoints
```

## Prerequisites

- Python 3.8+
- MongoDB (running locally on port 27017)

## Installation

1. Navigate to the backend directory:

   ```bash
   cd backend
   ```

2. Create a virtual environment:

   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:

   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Configure environment variables:

   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

6. Start MongoDB (if not already running)

7. Run the application:
   ```bash
   python app.py
   ```

The server will start at `http://localhost:5000`

## API Endpoints

### Health Check

- `GET /api/health` - Check API health status

### Overlays

- `GET /api/overlays` - Get all overlays
- `GET /api/overlays/:id` - Get a specific overlay
- `POST /api/overlays` - Create a new overlay
- `PUT /api/overlays/:id` - Update an overlay
- `DELETE /api/overlays/:id` - Delete an overlay

### Overlay Schema

```json
{
  "content": "string (text or image URL)",
  "type": "text | image",
  "position": {
    "x": "number",
    "y": "number"
  },
  "size": {
    "width": "number",
    "height": "number"
  }
}
```

### Example Requests

**Create Overlay:**

```bash
curl -X POST http://localhost:5000/api/overlays \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello World",
    "type": "text",
    "position": { "x": 100, "y": 50 },
    "size": { "width": 200, "height": 50 }
  }'
```

**Get All Overlays:**

```bash
curl http://localhost:5000/api/overlays
```

**Update Overlay:**

```bash
curl -X PUT http://localhost:5000/api/overlays/<overlay_id> \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Updated Text",
    "position": { "x": 150, "y": 75 }
  }'
```

**Delete Overlay:**

```bash
curl -X DELETE http://localhost:5000/api/overlays/<overlay_id>
```

## Environment Variables

| Variable     | Description                          | Default                    |
| ------------ | ------------------------------------ | -------------------------- |
| FLASK_ENV    | Environment (development/production) | development                |
| SECRET_KEY   | Flask secret key                     | -                          |
| MONGO_URI    | MongoDB connection URI               | mongodb://localhost:27017/ |
| MONGO_DBNAME | Database name                        | livesitter_db              |
| PORT         | Server port                          | 5000                       |
| CORS_ORIGINS | Allowed CORS origins                 | http://localhost:3000      |
