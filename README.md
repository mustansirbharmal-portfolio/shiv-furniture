# Shiv Furniture ERP - Backend API

Flask-based REST API for Shiv Furniture Budget Accounting System.

## Features

- **Authentication & Authorization**: JWT-based auth with role-based access control
- **Budget Management**: Create, track, and manage furniture project budgets
- **Payment Processing**: Razorpay integration for payments
- **File Storage**: Azure Blob Storage for documents and images
- **Email Notifications**: SMTP-based email system
- **AI Integration**: Azure OpenAI for intelligent features
- **Real-time Data**: MongoDB for fast, scalable data storage

## Tech Stack

- **Framework**: Flask 3.0.0
- **Database**: MongoDB Atlas
- **Storage**: Azure Blob Storage
- **Payment**: Razorpay
- **AI**: Azure OpenAI (GPT-4o-mini)
- **Deployment**: Render.com

## Getting Started

### Prerequisites

- Python 3.11+
- MongoDB Atlas account
- Azure Storage account
- Razorpay account
- SMTP email credentials

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/shiv-furniture-backend.git
   cd shiv-furniture-backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

   The API will be available at `http://localhost:8080`

## Deployment

See [RENDER_DEPLOYMENT.md](../RENDER_DEPLOYMENT.md) for detailed deployment instructions on Render.com.

### Quick Deploy to Render

1. Push code to GitHub
2. Create new Web Service on Render
3. Connect GitHub repository
4. Configure environment variables
5. Deploy!

Your API will be live at: `https://your-service.onrender.com`

## API Documentation

### Base URL
- **Local**: `http://localhost:8080/api`
- **Production**: `https://your-service.onrender.com/api`

### Authentication Endpoints
- `POST /auth/login` - User login
- `POST /auth/register` - User registration  
- `GET /auth/health` - Health check

### Budget Endpoints
- `GET /budgets` - Get all budgets
- `POST /budgets` - Create new budget
- `GET /budgets/:id` - Get budget by ID
- `PUT /budgets/:id` - Update budget
- `DELETE /budgets/:id` - Delete budget

*Full API documentation available in Swagger/OpenAPI format*

## Environment Variables

See `.env.example` for all required variables.

**Critical Variables:**
- `MONGODB_URI` - MongoDB connection string
- `SECRET_KEY` - Flask secret key
- `JWT_SECRET_KEY` - JWT signing key
- `FRONTEND_URL` - Frontend URL for CORS

## Project Structure

```
backend/
├── app/
│   ├── __init__.py          # App factory
│   ├── routes/              # API endpoints
│   ├── models/              # Data models
│   ├── services/            # Business logic
│   ├── utils/               # Helper functions
│   └── database.py          # Database configuration
├── tests/                   # Unit tests
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
├── render.yaml             # Render configuration
└── .env.example            # Environment template
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app tests/
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

Proprietary - © 2026 Shiv Furniture

## Support

For issues and questions:
- Create an issue on GitHub
- Contact: your-email@example.com
