# Smart Study Planner - Backend API

Production-ready FastAPI backend foundation for the Smart Study Planner application.

## Features

- ✅ **FastAPI Framework** - Modern, fast async web framework
- ✅ **Clean Architecture** - Modular, maintainable structure
- ✅ **MongoDB Integration** - Async database support with Motor
- ✅ **Structured Logging** - JSON logging for production environments
- ✅ **Global Exception Handling** - Consistent error responses
- ✅ **CORS Configuration** - Environment-based CORS setup
- ✅ **Health Check Endpoint** - Database connectivity monitoring
- ✅ **Versioned API** - API v1 routing structure
- ✅ **Environment Configuration** - Pydantic-based settings management

## Project Structure

```
/app
├── main.py                    # Application entry point
├── api/
│   └── v1/
│       └── router.py          # v1 API routes & health check
├── core/
│   ├── config/
│   │   └── settings.py        # Environment configuration
│   ├── database/
│   │   ├── models/            # Pydantic/MongoDB models (step 1)
│   │   └── mongo.py           # MongoDB connection
│   ├── security/
│   │   └── dependencies.py    # FastAPI dependencies
│   ├── logging/
│   │   └── logger.py          # Structured logging
│   ├── exceptions/
│   │   └── handlers.py        # Exception handlers
│   └── responses/
│       └── base.py            # Standard response models
└── shared/
    └── constants.py           # Application constants
```

## Quick Start

### Prerequisites

- Python 3.11+
- MongoDB (local or cloud)
- Virtual environment

### Installation

1. **Clone and navigate to the project**:
   ```bash
   cd /home/lucifer/Desktop/EDTECH
   ```

2. **Activate virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

3. **Install dependencies** (already done):
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   # .env file already created from .env.example
   # Update MongoDB URL if needed
   ```

5. **Start MongoDB** (if local):
   ```bash
   # Make sure MongoDB is running
   sudo systemctl start mongod
   ```

6. **Run the application**:
   ```bash
   uvicorn app.main:app --reload
   ```

   Or using the main.py directly:
   ```bash
   python -m app.main
   ```

7. **Access the API**:
   - API Root: http://localhost:8000
   - Health Check: http://localhost:8000/api/v1/health
   - API Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Environment Configuration

All configuration is managed through environment variables. See `.env.example` for available options.

### Key Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Application environment |
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB connection URL |
| `MONGODB_DB_NAME` | `smart_study_planner` | Database name |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `json` | Log format (json/text) |
| `CORS_ORIGINS` | `localhost:3000,localhost:8000` | Allowed CORS origins |

## API Endpoints

### Health Check

```bash
GET /api/v1/health
```

**Response**:
```json
{
  "success": true,
  "message": "Health check completed",
  "status_code": 200,
  "data": {
    "api": "healthy",
    "database": "healthy",
    "version": "1.0.0"
  }
}
```

### Root

```bash
GET /
```

Returns API information and status.

## Development

### Project Architecture

This project follows **Clean Architecture** principles:

- **API Layer** (`/api`): Route handlers, request/response
- **Core Layer** (`/core`): Business logic, utilities, database
- **Shared** (`/shared`): Constants, common utilities

### Adding New Features

1. Create feature module in `/app/features/`
2. Add routes in `/app/api/v1/endpoints/`
3. Register routes in `/app/api/v1/router.py`
4. Use dependency injection for database access

### Error Handling

All exceptions are handled globally and return standard error format:

```json
{
  "success": false,
  "message": "Error message",
  "status_code": 400,
  "errors": [
    {
      "field": "field_name",
      "message": "Validation error",
      "code": "ERROR_CODE"
    }
  ]
}
```

### Logging

Structured JSON logging is enabled by default in production. Logs include:

- Timestamp
- Log level
- Logger name
- Message
- Request ID (when available)
- Exception details (for errors)

## Testing

MongoDB connection can be tested independently:

```bash
# Check if MongoDB is accessible
python -c "from pymongo import MongoClient; client = MongoClient('mongodb://localhost:27017'); client.admin.command('ping'); print('✓ MongoDB connected')"
```

## Next Steps

**Step 3**: Implement feature modules (Auth, Users, Study Plans, etc.)

This foundation is ready for:
- Authentication & Authorization
- User management
- Study planning features
- AI integration
- Analytics
- Subscription management

## Notes

- **Security**: Change `SECRET_KEY` in production
- **MongoDB**: Ensure MongoDB is running before starting the app
- **CORS**: Update `CORS_ORIGINS` for production domains
- **Logging**: Use JSON format (`LOG_FORMAT=json`) in production
- **Docs**: Disable API docs in production by setting `DOCS_URL=""

## License

Internal project - Smart Study Planner
# edtech
