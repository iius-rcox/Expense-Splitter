# Archon Project Management Framework

## Project Overview

**Project Name:** PDF Transaction Matcher & Splitter  
**Project ID:** `4cfa897d-906c-481a-8d7f-6435a634060b`  
**Created:** October 17, 2025

This project has been integrated with the Archon MCP server for comprehensive task management, documentation, and knowledge base integration.

## Quick Start with Archon

### View All Tasks
```bash
# List all tasks
mcp_archon_find_tasks(project_id="4cfa897d-906c-481a-8d7f-6435a634060b")

# Find todo tasks
mcp_archon_find_tasks(filter_by="status", filter_value="todo")

# Search tasks by keyword
mcp_archon_find_tasks(query="PDF")
```

### Update Task Status
```bash
# Start working on a task
mcp_archon_manage_task("update", task_id="<task-id>", status="doing")

# Complete a task
mcp_archon_manage_task("update", task_id="<task-id>", status="done")

# Mark for review
mcp_archon_manage_task("update", task_id="<task-id>", status="review")
```

### View Documentation
```bash
# List all project documents
mcp_archon_find_documents(project_id="4cfa897d-906c-481a-8d7f-6435a634060b")

# Get specific document
mcp_archon_find_documents(project_id="4cfa897d-906c-481a-8d7f-6435a634060b", document_id="<doc-id>")
```

## Project Documents Created

1. **Technical Architecture Specification** (spec)
   - Backend: FastAPI, SQLAlchemy, pdfplumber, PyPDF2
   - Frontend: React 18+, TypeScript, Vite, Tailwind CSS, shadcn/ui
   - Deployment: Electron, PyInstaller, Docker

2. **API Specification** (api)
   - Upload endpoints: `/api/upload/car`, `/api/upload/receipt`
   - Processing: `/api/extract/transactions`, `/api/match/transactions`
   - Export: `/api/split/pdf`, `/api/download/{match_id}`

3. **Project Setup Guide** (guide)
   - Prerequisites and environment setup
   - Backend and frontend installation steps
   - Directory structure overview

## Tasks Created (15 Total)

### Backend Setup & Core (Priority: High)
1. **Setup Backend Environment** - Create venv, install dependencies
2. **Setup Frontend Environment** - Initialize React + TypeScript
3. **Implement Database Models** - SQLAlchemy models for transactions, matches, PDFs
4. **Build PDF Upload Endpoints** - FastAPI endpoints with validation

### PDF Processing (Priority: High)
5. **Implement PDF Text Extraction Service** - pdfplumber for text extraction
6. **Build Transaction Matching Algorithm** - Weighted matching (70% threshold)
7. **Implement PDF Splitting Service** - PyPDF2 for page extraction

### Frontend Development (Priority: Medium)
8. **Build Frontend Upload Component** - Drag & drop with progress tracking
9. **Create Transaction Display & Matching UI** - Side-by-side display with confidence scores
10. **Implement Export & Download Features** - Download UI and batch exports

### Desktop Deployment (Priority: Medium)
11. **Setup Electron Desktop App Wrapper** - Standalone desktop application
12. **Configure PyInstaller for Backend Bundling** - Python executable bundling

### Testing & Quality (Priority: Medium)
13. **Write Unit Tests for Backend Services** - pytest, 80%+ coverage
14. **Write Frontend Component Tests** - React Testing Library

### Deployment (Priority: Low)
15. **Create Docker Deployment Configuration** - Docker + PostgreSQL

## Features Overview

### Core Features
- **PDF Upload & Processing** - Drag & drop upload with validation
- **Transaction Extraction** - Regex-based parsing of CAR and receipt PDFs
- **Intelligent Matching** - Weighted algorithm with confidence scores
- **PDF Splitting** - Extract and combine matched page ranges
- **Export Management** - Individual and batch download capabilities
- **Standalone Deployment** - Desktop application with Electron

### Matching Algorithm
- **Date proximity** (30% weight) - Within 1 day
- **Amount match** (30% weight) - Exact match required
- **Employee ID** (25% weight) - Exact match required
- **Merchant match** (15% weight) - Fuzzy matching
- **Threshold** - 70% minimum confidence

## Development Workflow

### Task-Driven Development Cycle
1. **Get Task** → Find next todo task
2. **Start Work** → Update status to "doing"
3. **Research** → Use Archon knowledge base if needed
4. **Implement** → Write code based on specifications
5. **Review** → Mark as "review" when ready for testing
6. **Complete** → Update to "done" when finished

### Using the Knowledge Base
```bash
# Search for relevant documentation
mcp_archon_rag_search_knowledge_base(query="FastAPI file upload")

# Search for code examples
mcp_archon_rag_search_code_examples(query="React drag drop")

# Get available sources
mcp_archon_rag_get_available_sources()
```

## Next Steps

1. **Start with Backend Setup** - Task ID: `45fe0a99-6d9b-477e-b875-bb3dd5d409eb`
2. **Then Frontend Setup** - Task ID: `135e2a0a-c42e-4506-ba63-4dac8e44db65`
3. **Follow task sequence** - Work through tasks by feature area
4. **Update task status** - Keep Archon system synchronized

## Integration Benefits

✅ **Centralized Task Management** - All tasks tracked in Archon  
✅ **Documentation Hub** - Technical specs and guides in one place  
✅ **Knowledge Base Access** - Search documentation and code examples  
✅ **Version Control** - Track changes to documents and features  
✅ **Progress Tracking** - Monitor project completion status

## Resources

- **Project in Archon:** Use project ID `4cfa897d-906c-481a-8d7f-6435a634060b`
- **GitHub Repository:** https://github.com/user/Expense-Splitter
- **Main README:** See `/README.md` for technical details
- **Architecture Docs:** Available in Archon document system

---

**Last Updated:** October 17, 2025  
**Managed by:** Archon MCP Server

