# PDF Transaction Matcher - User Workflow Map

This document maps out the complete end-to-end user journey for the PDF Transaction Matcher & Splitter application.

---

## 🎯 **Application Purpose**

Match Corporate American Express Report (CAR) transactions with their corresponding receipt PDFs, then generate combined PDF files for accounting/expense reporting.

---

## 👤 **User Persona**

**Primary User**: Accounting/Finance staff member processing employee expense reports

**Typical Scenario**: Monthly expense reconciliation where employees submit:
- CAR PDF (Corporate AmEx statement with multiple transactions)
- Receipt PDFs (Individual receipts for each purchase)

**Goal**: Match each CAR transaction with its receipt and export matched pairs as single PDF files for filing/approval.

---

## 🗺️ **Complete User Journey**

### **Step 1: Access Application**

**URL**: http://localhost:5173 (or your deployed URL)

**Landing Page**: Upload Page

```
┌─────────────────────────────────────────────────────────┐
│         PDF Transaction Matcher                          │
│  Upload your CAR and receipt PDFs to begin matching     │
│                                                          │
│  ┌─────────────────┐    ┌─────────────────┐            │
│  │  Upload CAR PDF │    │ Upload Receipt  │            │
│  │                 │    │      PDF        │            │
│  │  [Drag & Drop]  │    │  [Drag & Drop]  │            │
│  │   or Click      │    │   or Click      │            │
│  └─────────────────┘    └─────────────────┘            │
│                                                          │
│         [Continue to Extract Transactions]               │
└─────────────────────────────────────────────────────────┘
```

**User Actions**:
1. Drag CAR PDF file to left upload zone OR click to browse
2. Wait for upload progress (file validation happens automatically)
3. See success message with file info (filename, page count, size)
4. Drag receipt collection PDF to right upload zone
5. Wait for upload progress
6. See success message

**What Happens Behind the Scenes**:
- File uploaded to backend via `POST /api/upload/car` or `/api/upload/receipt`
- Backend validates:
  - File is actually a PDF
  - File size < 300MB
  - PDF is not encrypted
  - PDF contains extractable text (not just images)
  - Page count between 1-500 pages
- File saved to `uploads/car/` or `uploads/receipt/` with UUID filename
- Database record created in `pdfs` table with metadata
- Response sent back to frontend with PDF ID

**Possible Errors**:
- ❌ "Only PDF files accepted" - Wrong file type
- ❌ "File size exceeds 300MB" - File too large
- ❌ "PDF is password-protected" - Encrypted PDF
- ❌ "No parseable transactions found" - Scanned image PDF

---

### **Step 2: Extract Transactions**

**Trigger**: Click "Continue to Extract Transactions" button

**Navigation**: Redirects to `/matching` page

**What Happens Behind the Scenes**:
1. Frontend calls `POST /api/extract/pdf/{car_pdf_id}`
2. Backend extracts transactions from CAR PDF:
   - Opens PDF with pdfplumber
   - Searches for employee info header on each page
   - Finds transaction section (between header and totals)
   - Parses each transaction line with regex:
     - Date (MM/DD/YYYY format)
     - Amount ($XXX.XX)
     - Merchant name
     - Employee ID, name, card number (from header)
   - Saves each transaction to `transactions` table
3. Frontend calls `POST /api/extract/pdf/{receipt_pdf_id}`
4. Backend extracts transactions from receipt PDF:
   - Each page typically = one receipt
   - Searches for:
     - Employee info (name, ID)
     - Transaction date
     - Total amount
     - Merchant name (usually at top)
   - Saves each transaction to `transactions` table
5. Page loads showing extracted transactions

**Expected Results**:
- CAR PDF: Multiple transactions extracted (one per expense line)
- Receipt PDF: One transaction per page (one per receipt)

**Possible Issues**:
- ❌ "No transactions extracted" - PDF format not recognized
- ⚠️ Some fields missing (date, amount, merchant) - Partial extraction
- ⚠️ Low confidence scores - Extraction uncertain

---

### **Step 3: Review Extracted Transactions**

**Page**: Matching Page (`/matching`)

**UI Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│                  Transaction Matching                            │
│   Review extracted transactions and run matching algorithm       │
│                                                                  │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐                        │
│  │  50  │  │  25  │  │  25  │  │   0  │                        │
│  │Total │  │ CAR  │  │Receipt│  │Matches│                       │
│  └──────┘  └──────┘  └──────┘  └──────┘                        │
│                                                                  │
│        [Run Matching Algorithm]                                  │
│                                                                  │
│  Unmatched Transactions (50)                                     │
│  ┌─────────────────────┐    ┌─────────────────────┐            │
│  │   CAR (25)          │    │   Receipt (25)      │            │
│  ├─────────────────────┤    ├─────────────────────┤            │
│  │ 10/15/25 - $123.45  │    │ 10/15/25 - $123.45  │            │
│  │ ACME CORP           │    │ ACME CORPORATION    │            │
│  ├─────────────────────┤    ├─────────────────────┤            │
│  │ 10/16/25 - $45.67   │    │ 10/16/25 - $45.67   │            │
│  │ OFFICE DEPOT        │    │ OFFICE SUPPLY CO    │            │
│  └─────────────────────┘    └─────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

**User Actions**:
1. Review extracted transactions in two columns
2. Verify data looks correct (dates, amounts, merchants)
3. Click "Run Matching Algorithm" button

**What Happens Behind the Scenes**:
- Frontend calls `POST /api/match/run?min_confidence=0.70`
- Backend runs matching algorithm:
  1. Gets all unmatched CAR transactions
  2. Gets all unmatched receipt transactions
  3. Compares each CAR transaction with each receipt transaction
  4. Calculates weighted confidence score:
     - **Date proximity (30%)**: Same day = 1.0, 1 day apart = 0.5, >1 day = 0.0
     - **Exact amount (30%)**: $123.45 = $123.45 → 1.0, otherwise → 0.0
     - **Employee ID (25%)**: "12345" = "12345" → 1.0, otherwise → 0.0
     - **Fuzzy merchant (15%)**: "ACME CORP" ≈ "ACME CORPORATION" → 0.85
  5. Overall confidence = (0.30 × date_score) + (0.30 × amount_score) + (0.25 × employee_score) + (0.15 × merchant_score)
  6. Only keeps matches with confidence ≥ 70%
  7. Uses greedy algorithm: highest confidence matches first, each transaction matched once max
  8. Saves matches to `matches` table
  9. Marks transactions as `is_matched = True`
- Frontend receives match results and displays them

---

### **Step 4: Review Matches**

**UI Updates**: Matches section appears at top of page

```
┌─────────────────────────────────────────────────────────────────┐
│  Matches (15)                                    ▼ Confidence   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Confidence: 95.2%                      [Approve] Status: │  │
│  │  Status: pending                                          │  │
│  │                                                            │  │
│  │  CAR Transaction            Receipt Transaction           │  │
│  │  ├─ Date: 10/15/2025       ├─ Date: 10/15/2025          │  │
│  │  ├─ Amount: $123.45        ├─ Amount: $123.45           │  │
│  │  ├─ Employee: 12345        ├─ Employee: 12345           │  │
│  │  └─ Merchant: ACME CORP    └─ Merchant: ACME CORPORATION│  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Confidence: 87.3%                      [Approve]         │  │
│  │  Status: pending                                          │  │
│  │                                                            │  │
│  │  CAR Transaction            Receipt Transaction           │  │
│  │  ├─ Date: 10/16/2025       ├─ Date: 10/16/2025          │  │
│  │  ├─ Amount: $45.67         ├─ Amount: $45.67            │  │
│  │  ├─ Employee: 12345        ├─ Employee: 12345           │  │
│  │  └─ Merchant: OFFICE DEPOT └─ Merchant: OFFICE SUPPLY   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**User Actions**:
1. Review each match
2. Check confidence score (higher = better match)
3. Verify CAR and receipt data matches logically
4. Click **[Approve]** button for valid matches

**Confidence Score Guide**:
- **90-100%**: Excellent match (exact date, amount, employee, similar merchant)
- **80-89%**: Good match (likely correct, minor merchant name difference)
- **70-79%**: Acceptable match (meets threshold but review carefully)
- **<70%**: No match shown (below confidence threshold)

**What Happens on Approve**:
- Frontend calls `PATCH /api/match/matches/{match_id}` with `status: "approved"`
- Backend updates match status
- Match becomes eligible for export

---

### **Step 5: Export Matched PDFs**

**UI Updates**: Export button appears on approved matches

```
┌──────────────────────────────────────────────────────────┐
│  Confidence: 95.2%                    [Export PDF]       │
│  Status: approved                                        │
│  ...                                                     │
└──────────────────────────────────────────────────────────┘
```

**User Actions**:
1. Click **[Export PDF]** button on an approved match

**What Happens Behind the Scenes**:
- Frontend calls `POST /api/export/match/{match_id}`
- Backend splitting service:
  1. Gets match record from database
  2. Retrieves car_transaction and receipt_transaction
  3. Gets source PDF file paths from database
  4. Opens CAR PDF, extracts the specific page with this transaction
  5. Opens receipt PDF, extracts the specific page with this receipt
  6. Combines pages: CAR page(s) first, then receipt page(s)
  7. Saves to `exports/match_{match_id}_{timestamp}.pdf`
  8. Updates match record:
     - `exported = True`
     - `export_path = /path/to/file.pdf`
     - `exported_at = timestamp`
     - `status = 'exported'`
- Frontend receives success response
- Button changes to **[Exported]** (greyed out)

**Export File Structure**:
```
exports/
├── match_550e8400-e29b-41d4-a716-446655440000_20251017_093045.pdf
│   ├── Page 1: CAR transaction (from CAR PDF page 5)
│   └── Page 2: Receipt (from receipt PDF page 3)
├── match_660e8400-e29b-41d4-a716-446655440001_20251017_093047.pdf
│   ├── Page 1: CAR transaction (from CAR PDF page 7)
│   └── Page 2: Receipt (from receipt PDF page 8)
└── ...
```

---

### **Step 6: Download Exported PDFs**

**Option A: Single Match Download**

Currently: Export files are saved to `exports/` directory on the server

**Future Enhancement**: Click match to download via `GET /api/export/download/{match_id}`

**Option B: Batch Download** (Future)

Export all approved matches at once:
- Click "Export All" button
- Calls `POST /api/export/matches/batch` with list of match IDs
- Downloads multiple PDFs

**Option C: All-in-One PDF** (Future)

Combine ALL matches into single PDF:
- Click "Export All-in-One" button
- Calls `POST /api/export/matches/all-in-one`
- Downloads single PDF with all matched pairs sequentially

---

## 📊 **Complete Flow Diagram**

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER WORKFLOW                              │
└─────────────────────────────────────────────────────────────────────┘

1. UPLOAD PHASE
   ┌──────────┐
   │  User    │
   └────┬─────┘
        │ Opens http://localhost:5173
        ▼
   ┌────────────────┐
   │ Upload Page    │
   │ /upload        │
   └────┬───────────┘
        │ Drags CAR.pdf
        ▼
   ┌────────────────┐      POST /api/upload/car
   │ Frontend       │──────────────────────────────┐
   └────────────────┘                              ▼
                                            ┌─────────────┐
                                            │  Backend    │
                                            │  Validates  │
                                            │  Saves to   │
                                            │  uploads/   │
                                            │  Returns ID │
                                            └──────┬──────┘
   ┌────────────────┐                              │
   │ Upload Zone    │◀─────────────────────────────┘
   │ Shows Success  │       Response: {pdf_id, filename, page_count}
   └────┬───────────┘
        │ User drags receipt.pdf
        ▼
   (Repeat for receipt upload)
        │
        ▼
   ┌────────────────┐
   │ Both Uploaded  │
   │ Button Enabled │
   └────┬───────────┘
        │ Clicks "Continue to Extract Transactions"
        ▼

2. EXTRACTION PHASE
   ┌────────────────┐
   │ Frontend       │
   │ Calls Extract  │
   └────┬───────────┘
        │ POST /api/extract/pdf/{car_pdf_id}
        │ POST /api/extract/pdf/{receipt_pdf_id}
        ▼
   ┌─────────────────────────────┐
   │  Backend Extraction Service │
   │  ┌─────────────────────┐    │
   │  │ 1. Open CAR PDF     │    │
   │  │ 2. Find employee    │    │
   │  │    info header      │    │
   │  │ 3. Find transaction │    │
   │  │    section          │    │
   │  │ 4. Parse each line: │    │
   │  │    - Date regex     │    │
   │  │    - Amount regex   │    │
   │  │    - Merchant name  │    │
   │  │ 5. Save to DB       │    │
   │  └─────────────────────┘    │
   └────────┬────────────────────┘
            │ Returns list of transactions
            ▼
   ┌────────────────┐
   │ Matching Page  │
   │ Shows:         │
   │ - 25 CAR txns  │
   │ - 25 Receipts  │
   │ - 0 Matches    │
   └────────────────┘

3. MATCHING PHASE
   ┌────────────────┐
   │  User          │
   └────┬───────────┘
        │ Clicks "Run Matching Algorithm"
        ▼
   ┌────────────────┐      POST /api/match/run
   │ Frontend       │──────────────────────────────┐
   └────────────────┘                              ▼
                                            ┌──────────────────┐
                                            │  Matching        │
                                            │  Service         │
                                            └──────┬───────────┘
                                                   │
   ┌───────────────────────────────────────────────┼─────────────┐
   │  For each CAR transaction:                    │             │
   │    For each Receipt transaction:              │             │
   │      ┌─────────────────────────────────────┐  │             │
   │      │ Calculate Scores:                   │  │             │
   │      │ ┌─────────────────────────────────┐ │  │             │
   │      │ │ Date Score (30% weight)         │ │  │             │
   │      │ │ 10/15 vs 10/15 → 1.0           │ │  │             │
   │      │ │ 10/15 vs 10/16 → 0.5           │ │  │             │
   │      │ │ 10/15 vs 10/18 → 0.0           │ │  │             │
   │      │ └─────────────────────────────────┘ │  │             │
   │      │ ┌─────────────────────────────────┐ │  │             │
   │      │ │ Amount Score (30% weight)       │ │  │             │
   │      │ │ $123.45 = $123.45 → 1.0        │ │  │             │
   │      │ │ $123.45 ≠ $123.50 → 0.0        │ │  │             │
   │      │ └─────────────────────────────────┘ │  │             │
   │      │ ┌─────────────────────────────────┐ │  │             │
   │      │ │ Employee Score (25% weight)     │ │  │             │
   │      │ │ "12345" = "12345" → 1.0        │ │  │             │
   │      │ │ "12345" ≠ "54321" → 0.0        │ │  │             │
   │      │ └─────────────────────────────────┘ │  │             │
   │      │ ┌─────────────────────────────────┐ │  │             │
   │      │ │ Merchant Score (15% weight)     │ │  │             │
   │      │ │ Fuzzy match: "ACME CORP" vs     │ │  │             │
   │      │ │ "ACME CORPORATION" → 0.85      │ │  │             │
   │      │ └─────────────────────────────────┘ │  │             │
   │      │                                     │  │             │
   │      │ Overall = 0.3×1.0 + 0.3×1.0 +     │  │             │
   │      │           0.25×1.0 + 0.15×0.85    │  │             │
   │      │         = 0.9775 (97.75%)         │  │             │
   │      └─────────────────────────────────────┘  │             │
   │                                                │             │
   │      If confidence ≥ 70%: Keep match          │             │
   │      If confidence < 70%: Discard              │             │
   └────────────────────────────────────────────────┘             │
                                                                  │
   Greedy matching (highest confidence first):                    │
   - Match #1: CAR-txn-1 ↔ Receipt-txn-5 (97.75%)               │
   - Match #2: CAR-txn-2 ↔ Receipt-txn-3 (89.50%)               │
   - CAR-txn-3 already matched to Receipt-txn-5? Skip.          │
   - ...continue until all processed                             │
                                                                  │
   Save to matches table, return to frontend                      │
                                                   ▼
                                            ┌──────────────────┐
                                            │ Frontend Updates │
                                            │ Shows Matches    │
                                            └──────────────────┘

4. APPROVAL PHASE
   ┌────────────────────────────────────────┐
   │  Matches (15)                          │
   │  ┌──────────────────────────────────┐  │
   │  │ ✓ 97.75% Match     [Approve]    │  │
   │  │   CAR: $123.45 ACME CORP        │  │
   │  │   Receipt: $123.45 ACME CORP    │  │
   │  └──────────────────────────────────┘  │
   └────────────────────────────────────────┘
        │ User clicks [Approve]
        ▼
   PATCH /api/match/matches/{id} {status: "approved"}
        │
        ▼
   Database: match.status = "approved"
        │
        ▼
   UI updates: [Export PDF] button appears

5. EXPORT PHASE
   ┌────────────────────────────────────────┐
   │  ✓ 97.75% Match     [Export PDF]      │
   │  Status: approved                      │
   └────────────────────────────────────────┘
        │ User clicks [Export PDF]
        ▼
   POST /api/export/match/{match_id}
        │
        ▼
   ┌─────────────────────────────────────┐
   │  Backend Splitting Service          │
   │  ┌──────────────────────────────┐   │
   │  │ 1. Get match from DB         │   │
   │  │ 2. Get CAR PDF path          │   │
   │  │ 3. Get receipt PDF path      │   │
   │  │ 4. Open CAR PDF              │   │
   │  │ 5. Extract page 5            │   │
   │  │ 6. Open receipt PDF          │   │
   │  │ 7. Extract page 3            │   │
   │  │ 8. Create new PDF:           │   │
   │  │    - Add CAR page 5          │   │
   │  │    - Add receipt page 3      │   │
   │  │ 9. Save to exports/          │   │
   │  │ 10. Update match:            │   │
   │  │     exported=True            │   │
   │  │     export_path=...          │   │
   │  │     status='exported'        │   │
   │  └──────────────────────────────┘   │
   └─────────────────────────────────────┘
        │ Returns: {export_path, total_pages}
        ▼
   ┌────────────────────────────────────────┐
   │  UI updates: [Exported] (greyed out)   │
   └────────────────────────────────────────┘

6. DOWNLOAD PHASE (Current: Manual)
   User navigates to exports/ folder on server
   Finds: match_550e8400...20251017_093045.pdf
   Opens PDF → 2 pages:
     Page 1: CAR transaction from original CAR PDF
     Page 2: Receipt from original receipt PDF

   (Future: Click to download via browser)
```

---

## 🔄 **Data Flow Through the System**

### **Flow 1: Upload to Storage**

```
User's Computer                     Docker Container
┌──────────────┐                    ┌─────────────────────┐
│  CAR.pdf     │                    │  Backend Container  │
│  (5.2 MB)    │                    │  ┌────────────────┐ │
└──────┬───────┘                    │  │ FastAPI        │ │
       │                            │  │ PDFService     │ │
       │ HTTP POST (multipart)      │  └────────────────┘ │
       │ /api/upload/car            │         │           │
       └────────────────────────────┼─────────┤           │
                                    │         ▼           │
                                    │  ┌────────────────┐ │
                                    │  │ Validate:      │ │
                                    │  │ - Is PDF?      │ │
                                    │  │ - Size OK?     │ │
                                    │  │ - Encrypted?   │ │
                                    │  │ - Has text?    │ │
                                    │  └────────────────┘ │
                                    │         │           │
                                    │         ▼           │
                                    │  ┌────────────────┐ │
Mounted Volume                      │  │ Save to        │ │
┌──────────────┐                    │  │ /uploads/car/  │ │
│  uploads/    │◀────────────────────┼──│ UUID.pdf       │ │
│  └─car/      │                    │  └────────────────┘ │
│    └─550e...│                    │         │           │
│      .pdf    │                    │         ▼           │
└──────────────┘                    │  ┌────────────────┐ │
                                    │  │ SQLite DB:     │ │
Mounted Volume                      │  │ INSERT INTO    │ │
┌──────────────┐                    │  │ pdfs (id,      │ │
│  data/       │◀────────────────────┼──│ filename,      │ │
│  expense_    │                    │  │ file_path,     │ │
│  matcher.db  │                    │  │ pdf_type,      │ │
└──────────────┘                    │  │ page_count)    │ │
                                    │  └────────────────┘ │
                                    │         │           │
                                    │         ▼           │
                                    │  ┌────────────────┐ │
                                    │  │ Return JSON    │ │
                                    │  │ {pdf_id: ...}  │ │
                                    │  └────────────────┘ │
                                    └────────┬────────────┘
                                             │ HTTP 201 Created
┌──────────────┐                             │
│  Frontend    │◀────────────────────────────┘
│  Shows       │
│  ✓ Uploaded  │
└──────────────┘
```

### **Flow 2: Extraction to Database**

```
Frontend                        Backend                      Database
┌────────┐                     ┌──────────────┐            ┌─────────┐
│ Click  │                     │ Extraction   │            │ SQLite  │
│Continue│──POST /api/extract──▶│ Service      │            │         │
└────────┘  /pdf/{id}          └──────┬───────┘            └─────────┘
                                      │
                                      ▼
                               ┌──────────────────┐
                               │ 1. Get PDF from  │
Mounted Volume                 │    DB by id      │
┌──────────────┐               └─────┬────────────┘
│  uploads/    │                     │
│  car/        │                     ▼
│  550e...pdf  │◀────────────┌───────────────────┐
└──────────────┘             │ 2. Open file with │
                             │    pdfplumber     │
                             └─────┬─────────────┘
                                   │
                                   ▼
                             ┌─────────────────────────┐
                             │ 3. For each page:       │
                             │    - Extract text       │
                             │    - Regex: Employee ID │
                             │    - Regex: Date        │
                             │    - Regex: Amount      │
                             │    - Regex: Merchant    │
                             └─────┬───────────────────┘
                                   │
                                   ▼
                             ┌─────────────────────────┐
                             │ 4. Create Transaction   │
                             │    objects:             │
                             │    {                    │
                             │      pdf_id: "550e...", │
                             │      date: "10/15/25",  │
                             │      amount: 123.45,    │
                             │      employee_id: "123",│
                             │      merchant: "ACME",  │
                             │      page_number: 5     │
                             │    }                    │
                             └─────┬───────────────────┘
                                   │
                                   ▼
                             ┌─────────────────────────┐
┌─────────────┐              │ 5. Bulk insert to DB:   │
│ transactions│◀─────────────│    INSERT INTO          │
│ table       │              │    transactions (...)   │
│ ┌─────────┐ │              │    VALUES (...×25)      │
│ │ txn-1   │ │              └─────────────────────────┘
│ │ txn-2   │ │                     │
│ │ ...     │ │                     │
│ │ txn-25  │ │                     │ Return count
│ └─────────┘ │                     ▼
└─────────────┘              ┌─────────────────────────┐
                             │ Response:               │
                             │ {                       │
                             │   transactions: [...],  │
                             │   total_count: 50,      │
                             │   car_count: 25,        │
                             │   receipt_count: 25     │
                             │ }                       │
                             └─────┬───────────────────┘
                                   │
                                   ▼
                             ┌─────────────────────────┐
                             │ Frontend displays       │
                             │ all transactions        │
                             └─────────────────────────┘
```

### **Flow 3: Matching Algorithm**

```
Database                    Matching Service                    Database
┌─────────────┐            ┌────────────────────┐            ┌─────────┐
│transactions │            │ 1. Load unmatched: │            │ matches │
│ ┌─────────┐ │            │    CAR: 25 txns    │            └─────────┘
│ │CAR txns │ │───GET────▶│    Receipt: 25     │
│ │ is_match│ │ unmatched │                    │
│ │ ed=False│ │            └────┬───────────────┘
│ └─────────┘ │                 │
│ ┌─────────┐ │                 ▼
│ │Receipt  │ │            ┌────────────────────────┐
│ │txns     │ │───GET────▶│ 2. Compare all pairs:  │
│ │is_match │ │ unmatched │    25 × 25 = 625       │
│ │ed=False │ │            │    comparisons         │
│ └─────────┘ │            └────┬───────────────────┘
└─────────────┘                 │
                                ▼
                          ┌─────────────────────────────┐
                          │ 3. For each comparison:     │
                          │    ┌────────────────────┐   │
                          │    │ CAR txn #1:        │   │
                          │    │ Date: 10/15/25     │   │
                          │    │ Amount: $123.45    │   │
                          │    │ Employee: 12345    │   │
                          │    │ Merchant: ACME     │   │
                          │    └────────────────────┘   │
                          │           vs                │
                          │    ┌────────────────────┐   │
                          │    │ Receipt txn #5:    │   │
                          │    │ Date: 10/15/25     │   │
                          │    │ Amount: $123.45    │   │
                          │    │ Employee: 12345    │   │
                          │    │ Merchant: ACME INC │   │
                          │    └────────────────────┘   │
                          │                             │
                          │    Scores:                  │
                          │    Date:     1.0 × 0.30 = 0.30 │
                          │    Amount:   1.0 × 0.30 = 0.30 │
                          │    Employee: 1.0 × 0.25 = 0.25 │
                          │    Merchant: 0.92× 0.15 = 0.14 │
                          │    ─────────────────────────── │
                          │    Confidence:         = 0.99  │
                          │                (99%)           │
                          └────┬────────────────────────────┘
                               │ Confidence ≥ 70%? YES → Keep
                               ▼
                          ┌────────────────────────────────┐
                          │ 4. Sort by confidence:         │
                          │    [99%, 95%, 87%, 82%, ...]   │
                          └────┬───────────────────────────┘
                               │
                               ▼
                          ┌────────────────────────────────┐
                          │ 5. Greedy matching:            │
                          │    Take highest (99%)          │
                          │    ├─ CAR-1 matched ✓          │
                          │    └─ Receipt-5 matched ✓      │
                          │    Take next (95%)             │
                          │    ├─ CAR-2 not used ✓         │
                          │    └─ Receipt-8 not used ✓     │
                          │    Skip if already matched     │
                          └────┬───────────────────────────┘
                               │
                               ▼
┌─────────────┐          ┌────────────────────────────────┐
│ matches     │◀─────────│ 6. Save matches:               │
│ table       │  INSERT  │    INSERT INTO matches (       │
│ ┌─────────┐ │          │      car_transaction_id,       │
│ │match-1  │ │          │      receipt_transaction_id,   │
│ │  99%    │ │          │      confidence_score,         │
│ ├─────────┤ │          │      date_score,               │
│ │match-2  │ │          │      amount_score,             │
│ │  95%    │ │          │      employee_score,           │
│ ├─────────┤ │          │      merchant_score,           │
│ │...      │ │          │      status='pending'          │
│ └─────────┘ │          │    )                           │
└─────────────┘          └────────────────────────────────┘
                                   │
                                   ▼
┌─────────────┐          ┌────────────────────────────────┐
│transactions │◀─────────│ 7. Mark as matched:            │
│ table       │  UPDATE  │    UPDATE transactions         │
│ ┌─────────┐ │          │    SET is_matched = TRUE       │
│ │CAR-1    │ │          │    WHERE id IN (...)           │
│ │matched✓ │ │          └────────────────────────────────┘
│ │Receipt-5│ │                     │
│ │matched✓ │ │                     │
│ └─────────┘ │                     │
└─────────────┘                     │ Return matches with full txn details
                                    ▼
                             ┌────────────────────────┐
                             │ Frontend displays      │
                             │ matches with           │
                             │ [Approve] buttons      │
                             └────────────────────────┘
```

### **Flow 4: PDF Splitting & Export**

```
Frontend                Backend              File System
┌────────┐             ┌──────────────┐
│ Click  │             │ Splitting    │
│ Export │──POST──────▶│ Service      │
└────────┘ /export/    └──────┬───────┘
           match/{id}         │
                              ▼
                       ┌──────────────────┐
                       │ 1. Query match:  │
Database               │    Get car_txn   │
┌─────────────┐        │    Get rcpt_txn  │
│ matches     │        └──────┬───────────┘
│ ┌─────────┐ │               │
│ │match-1  │ │◀──────────────┘
│ │ car: A  │ │
│ │ rcpt: B │ │──────┐
│ └─────────┘ │      │
└─────────────┘      │
                     ▼
              ┌──────────────────────┐
Database      │ 2. Get PDF metadata: │
┌───────────┐ │    CAR PDF path      │
│pdfs       │ │    Receipt PDF path  │
│┌────────┐ │ │    Page numbers      │
││CAR PDF │ │ └──────┬───────────────┘
││path: / │ │        │
││uploads │ │◀───────┘
││/car/.. │ │
│└────────┘ │
│┌────────┐ │
││Receipt │ │
││path: / │ │
││uploads │ │
││/rcpt/..│ │
│└────────┘ │
└───────────┘
     │
     ▼
┌──────────────────────┐
│ 3. Open source PDFs: │
│    PyPDF2.PdfReader  │
└──────┬───────────────┘
       │
Mounted Volume         │
┌─────────────────┐    │
│ uploads/        │    │
│ ├─ car/         │    │
│ │  └─550e.pdf   │◀───┤ Read CAR PDF (15 pages)
│ └─ receipt/     │    │ Extract: page 5
│    └─660e.pdf   │◀───┘ Read Receipt PDF (25 pages)
└─────────────────┘      Extract: page 3
       │
       ▼
┌──────────────────────────────┐
│ 4. Create new PdfWriter:     │
│    ┌──────────────────────┐  │
│    │ New PDF:             │  │
│    │ ├─ Page 1: CAR pg 5  │  │
│    │ └─ Page 2: Rcpt pg 3 │  │
│    └──────────────────────┘  │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ 5. Save to exports/:         │
│    match_{id}_{timestamp}.pdf│
└──────┬───────────────────────┘
       │
Mounted Volume                 │
┌─────────────────┐            │
│ exports/        │            │
│ └─ match_...pdf │◀───────────┘ Save combined PDF
└─────────────────┘
       │
       ▼
Database
┌─────────────┐
│ matches     │
│ ┌─────────┐ │
│ │ UPDATE: │ │◀──── 6. Update match record
│ │exported │ │           exported = TRUE
│ │ =true   │ │           export_path = "/exports/match..."
│ │path=/.. │ │           exported_at = now()
│ │status=  │ │           status = 'exported'
│ │exported │ │
│ └─────────┘ │
└─────────────┘
       │
       │ Return: {export_path, total_pages}
       ▼
┌────────────┐
│ Frontend   │
│ Shows:     │
│ [Exported] │
└────────────┘
```

---

## 🎬 **Real-World Example**

### **Scenario**: Employee John Smith's October Expenses

**Input Files**:
1. **CAR PDF**: `amex_statement_october_2025.pdf` (8 pages, 42 transactions)
2. **Receipt PDF**: `october_receipts_john_smith.pdf` (42 pages, 42 receipts)

### **Step-by-Step**

**Day 1 - Month End**:
1. Accounting receives CAR and receipts from employee
2. Opens http://localhost:5173
3. Uploads CAR PDF → "✓ 8 pages uploaded"
4. Uploads receipt PDF → "✓ 42 pages uploaded"
5. Clicks "Continue to Extract Transactions"

**Extraction** (2-5 seconds):
- CAR: 42 transactions extracted
  - Employee ID: 12345
  - Employee Name: SMITH, JOHN
  - Card: XXXXXX1234
  - Date range: 10/01/25 - 10/31/25
  - Total: $3,456.78
- Receipts: 42 transactions extracted
  - Various merchants, dates, amounts

**Matching** (1-3 seconds):
6. Clicks "Run Matching Algorithm"
7. System finds 38 high-confidence matches (90-100%)
8. System finds 2 medium-confidence matches (75-85%)
9. System leaves 2 CAR transactions unmatched (no receipt found)
10. System leaves 2 receipts unmatched (no CAR transaction)

**Review**:
11. Reviews high-confidence matches - look good ✓
12. Reviews medium-confidence matches:
    - Match 1: Different merchant names but same amount/date → Approve ✓
    - Match 2: Dates off by 1 day, manual verification needed → Check receipt → Approve ✓
13. Notes 2 unmatched CAR transactions → Will follow up with employee
14. Notes 2 unmatched receipts → Likely personal, not business

**Export** (5-10 seconds):
15. Clicks "Approve" on all 40 valid matches
16. Clicks "Export PDF" on each (or future: "Export All")
17. System generates 40 combined PDFs in `exports/`
18. Each PDF contains 2 pages:
    - Page 1: CAR transaction line
    - Page 2: Corresponding receipt

**Result**:
- 40 matched pairs ready for filing
- 2 unmatched CAR transactions flagged for follow-up
- 2 unmatched receipts flagged for review
- Accounting process complete in ~10 minutes (vs hours of manual matching)

---

## 📈 **Efficiency Comparison**

### **Manual Process** (Before)
1. Print CAR (8 pages)
2. Print receipts (42 pages)
3. Highlight each CAR transaction
4. Find matching receipt by date/amount
5. Staple CAR page + receipt
6. Repeat 42 times
7. File in folders

**Time**: 2-3 hours per employee
**Error Rate**: ~5-10% (wrong receipts attached)

### **Automated Process** (With This App)
1. Upload CAR PDF (10 seconds)
2. Upload receipt PDF (10 seconds)
3. Click extract (5 seconds)
4. Click match (2 seconds)
5. Review matches (2-5 minutes)
6. Export all (10 seconds)

**Time**: 5-10 minutes per employee
**Error Rate**: ~1-2% (only where algorithm uncertain, flagged for review)
**Time Saved**: ~2.5 hours per employee × multiple employees = significant efficiency gain

---

## 🔍 **Edge Cases & How System Handles Them**

### **Case 1: Missing Receipt**

**Scenario**: Employee lost receipt for $45 purchase

**System Behavior**:
- CAR transaction extracted ✓
- No matching receipt found
- Transaction remains in "Unmatched CAR" column
- User reviews, notes missing receipt, follows up with employee

### **Case 2: Duplicate Amounts Same Day**

**Scenario**: Two $50 transactions on 10/15

**System Behavior**:
- Both CAR transactions extracted
- Two receipts with $50 on 10/15 extracted
- Matching algorithm calculates confidence:
  - Match 1: CAR-1 ↔ Receipt-A (merchant similarity: 95%)
  - Match 2: CAR-1 ↔ Receipt-B (merchant similarity: 40%)
  - Match 3: CAR-2 ↔ Receipt-A (merchant similarity: 35%)
  - Match 4: CAR-2 ↔ Receipt-B (merchant similarity: 90%)
- Greedy algorithm picks:
  - Highest first: Match 1 (CAR-1 ↔ Receipt-A)
  - Next available: Match 4 (CAR-2 ↔ Receipt-B)
- Correct pairing based on merchant names ✓

### **Case 3: Receipt Date Wrong**

**Scenario**: Receipt shows 10/15 but transaction posted 10/16

**System Behavior**:
- Date score: 0.5 (1 day tolerance)
- Amount score: 1.0 (exact match)
- Employee score: 1.0 (exact match)
- Merchant score: 0.9 (good match)
- Overall: 0.30×0.5 + 0.30×1.0 + 0.25×1.0 + 0.15×0.9 = 0.835 (83.5%)
- Match created with "good" confidence
- User reviews, sees 1-day difference, approves based on amount/merchant

### **Case 4: Personal vs Business Receipt**

**Scenario**: Employee accidentally included personal receipt

**System Behavior**:
- Receipt extracted with employee ID
- No matching CAR transaction (wasn't a business expense)
- Receipt remains in "Unmatched Receipts" column
- User reviews, identifies as personal, excludes from export

### **Case 5: Split Receipt**

**Scenario**: Multiple employees split one bill, each has portion on CAR

**System Limitation**: Current algorithm matches 1:1 only
- Each CAR transaction looks for one receipt
- If receipt has total $200 but CAR shows $100 (employee's portion):
  - Amount score: 0.0 (doesn't match)
  - Match fails
  - User handles manually

**Future Enhancement**: Add split transaction support

---

## 🛠️ **Technical Flow** (For Developers)

### **Docker Container Flow**

```
User Browser                     Docker Network
    │                           ┌─────────────────────────┐
    │ http://localhost:5173     │ expense-splitter       │
    ▼                           │ (bridge network)       │
┌─────────────────────┐         │                        │
│ Frontend Container  │         │  ┌──────────────────┐  │
│ ┌─────────────────┐ │         │  │ Backend          │  │
│ │ Nginx:80        │ │         │  │ Container        │  │
│ │ Serves:         │ │         │  │ ┌──────────────┐ │  │
│ │ /usr/share/     │ │         │  │ │ FastAPI:8000 │ │  │
│ │ nginx/html/     │ │         │  │ └──────────────┘ │  │
│ │ ├─index.html    │ │         │  │                  │  │
│ │ ├─assets/       │ │         │  │ Volumes:         │  │
│ │ │ └─*.js,css    │ │         │  │ - ./backend:/app │  │
│ │ └─...           │ │         │  │ - ./data:/data   │  │
│ └─────────────────┘ │         │  │ - ./uploads:     │  │
│                     │         │  │   /uploads       │  │
│ Port mapping:       │         │  │ - ./exports:     │  │
│ Host:5173→          │         │  │   /exports       │  │
│   Container:80      │         │  └──────────────────┘  │
└─────────────────────┘         │                        │
    │                           │  Port mapping:         │
    │ API calls                 │  Host:8000→            │
    │ http://localhost:8000/api │    Container:8000      │
    └───────────────────────────┼────────────────────────┘
                                │
                                ▼
                          Backend processes
                          request, accesses
                          mounted volumes

Host File System            Container File System
┌─────────────────┐        ┌──────────────────┐
│ ./data/         │◀──────▶│ /data/           │
│ expense.db      │ mount  │ expense.db       │
└─────────────────┘        └──────────────────┘

┌─────────────────┐        ┌──────────────────┐
│ ./uploads/      │◀──────▶│ /uploads/        │
│ ├─car/          │ mount  │ ├─car/           │
│ └─receipt/      │        │ └─receipt/       │
└─────────────────┘        └──────────────────┘

┌─────────────────┐        ┌──────────────────┐
│ ./exports/      │◀──────▶│ /exports/        │
│ └─match_*.pdf   │ mount  │ └─match_*.pdf    │
└─────────────────┘        └──────────────────┘

Container restart: Volumes persist ✓
```

---

## 💡 **User Tips**

### **Best Practices**

1. **File Naming**: Use descriptive names like `CAR_October_2025.pdf` and `Receipts_JohnSmith_October.pdf`

2. **Receipt Organization**: Ensure receipt PDF has one receipt per page (not multiple per page)

3. **Review Before Export**: Always review matches before exporting, especially those with confidence 70-85%

4. **Handle Unmatched**: Investigate unmatched transactions - often indicates missing receipts

5. **Backup**: Keep original PDF files - exported files are for convenience, not primary records

### **Common Questions**

**Q: What if merchant names don't match?**
A: System uses fuzzy matching. "ACME CORP" matches "ACME CORPORATION" at ~90%. Different abbreviations usually still match if similar enough.

**Q: What if dates are slightly off?**
A: System allows 1-day tolerance. Transaction date might differ from receipt date due to posting delays.

**Q: Can I re-match after exporting?**
A: Current version: No. Matched transactions are marked and excluded from future matching. Future: Add "unmatch" capability.

**Q: What if no matches are found?**
A: Check:
- Are employee IDs consistent between CAR and receipts?
- Are dates in expected format?
- Are amounts exact (don't round)?
- Lower confidence threshold temporarily for testing

**Q: Can I match across multiple months?**
A: Yes! Upload multiple CAR and receipt PDFs. All transactions pool together for matching.

---

## 📱 **Deployment Scenarios**

### **Scenario 1: Single User (Desktop App)**

**Setup**: Docker on local machine
**Access**: http://localhost:5173
**Data**: Stored locally in `data/`, `uploads/`, `exports/`
**Use Case**: Individual user processing their own expenses

### **Scenario 2: Team (Shared Server)**

**Setup**: Docker on network server
**Access**: http://server-ip:5173 (or domain name)
**Data**: Centralized on server, all users access same instance
**Use Case**: Accounting team processing multiple employees

### **Scenario 3: Cloud (Production)**

**Setup**: Docker on cloud VM (AWS, Azure, GCP)
**Access**: https://expense-matcher.company.com
**Data**: Persistent volumes or object storage (S3)
**Use Case**: Enterprise deployment with SSL, backups, monitoring

---

## 🔐 **Data Privacy & Security**

### **What's Stored**

1. **Original PDFs**: Temporarily in `uploads/` (can be deleted after export)
2. **Extracted Data**: Transaction details in database (amounts, dates, merchants)
3. **Matched PDFs**: Combined PDFs in `exports/` (for download)

### **Data Retention**

**Recommendation**:
- Keep exported PDFs as needed for accounting/audit
- Delete uploads after successful export
- Archive old database periodically

**Implementation** (Future):
- Add auto-cleanup for uploads older than 30 days
- Add archive feature for old transactions
- Add export to accounting system integration

---

## 🚀 **Quick Start for End Users**

### **First Time Setup** (IT/Admin)

```bash
# 1. Install Docker Desktop
# 2. Clone repository
git clone <repo-url>
cd Expense-Splitter

# 3. Start application
docker-compose up -d

# 4. Verify running
docker-compose ps
```

### **Daily Use** (End User)

```
1. Open browser: http://localhost:5173
2. Upload CAR PDF
3. Upload receipts PDF
4. Click "Continue to Extract Transactions"
5. Click "Run Matching Algorithm"
6. Review matches
7. Click "Approve" on valid matches
8. Click "Export PDF" on approved matches
9. Find exported files in exports/ folder
10. Submit to accounting system
```

### **Troubleshooting** (End User)

**Problem**: "Upload failed"
- **Check**: Is PDF less than 300MB?
- **Check**: Is PDF not password-protected?
- **Try**: Convert scanned image to searchable PDF (OCR)

**Problem**: "No transactions extracted"
- **Check**: Is PDF text-based (not scanned image)?
- **Try**: Different PDF viewer to verify content
- **Contact**: IT support if PDF format unusual

**Problem**: "No matches found"
- **Check**: Are employee IDs same in CAR and receipts?
- **Check**: Are amounts exact (to the cent)?
- **Try**: Lower confidence threshold
- **Manual**: Match manually if patterns don't fit

---

## 📊 **Success Metrics**

### **Efficiency**
- ✅ 95%+ of transactions auto-matched
- ✅ 90%+ reduction in manual matching time
- ✅ <10 minutes per employee statement

### **Accuracy**
- ✅ 95%+ accuracy on high-confidence matches (90%+)
- ✅ 85%+ accuracy on medium-confidence matches (70-89%)
- ✅ Unmatched transactions flagged for manual review

### **User Satisfaction**
- ✅ Single-page workflow (minimal clicks)
- ✅ Immediate visual feedback
- ✅ Clear confidence scores for decision-making
- ✅ Undo capability (delete match if wrong)

---

*This map provides a complete picture of the user journey through the PDF Transaction Matcher application.*
