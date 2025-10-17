# PDF Transaction Matcher & Splitter

A comprehensive system that extracts transactions from CAR and receipt PDFs, matches them based on date/amount/employee criteria, and splits PDFs into matching pairs for export.

## Project Structure

```
Expense-Splitter/
├── backend/                 # FastAPI backend application
│   ├── api/                # API route handlers
│   ├── app/                # FastAPI app configuration
│   ├── models/             # Database models (SQLAlchemy)
│   ├── services/           # Business logic services
│   └── utils/              # Utility functions
├── frontend/               # React + TypeScript frontend
│   ├── public/             # Static assets
│   └── src/                # Source code
│       ├── components/     # React components
│       ├── pages/          # Page components
│       ├── hooks/          # Custom React hooks
│       ├── services/       # API service functions
│       ├── types/          # TypeScript type definitions
│       └── utils/          # Utility functions
├── docs/                   # Documentation
├── tests/                  # Test files
├── scripts/                # Build and deployment scripts
├── data/                   # Database files and sample data
├── uploads/                # Temporary PDF upload storage
└── exports/                # Generated PDF exports
```

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Database ORM
- **SQLite** - Development database
- **PostgreSQL** - Production database
- **pdfplumber** - PDF text extraction
- **PyPDF2** - PDF manipulation
- **Pydantic** - Data validation

### Frontend
- **React 18+** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Query** - Data fetching
- **shadcn/ui** - UI components

### Deployment
- **Electron** - Desktop app wrapper
- **PyInstaller** - Python executable bundling
- **Docker** - Containerization (optional)

## Features

- **PDF Upload & Processing** - Drag & drop PDF upload with progress tracking
- **Transaction Extraction** - Automatic extraction using regex patterns
- **Intelligent Matching** - Match CAR transactions with receipt transactions
- **PDF Splitting** - Extract specific page ranges for matched pairs
- **Export Management** - Download individual or batch PDFs
- **Standalone Deployment** - Single executable desktop application

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

- `POST /api/upload/car` - Upload CAR PDF
- `POST /api/upload/receipt` - Upload receipt PDF
- `POST /api/extract/transactions` - Extract transactions from PDFs
- `POST /api/match/transactions` - Match transactions
- `GET /api/matches` - Get all matches
- `POST /api/split/pdf` - Split PDFs for matched pairs
- `GET /api/download/{match_id}` - Download split PDF

## Matching Algorithm

Transactions are matched based on:
- **Date** (within 1 day) - Weight: 30%
- **Amount** (exact match) - Weight: 30%
- **Employee ID** (exact match) - Weight: 25%
- **Merchant** (fuzzy match) - Weight: 15%

Confidence threshold: 70%

## License

Private - Internal use only
