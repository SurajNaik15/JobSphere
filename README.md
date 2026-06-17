# JobSphere – Your Gateway To Governance

**Government Job Notification Analyzer | MCA Final Year Project**

---

## Project Overview

JobSphere is a web-based Government Job Notification Analyzer built with Python Flask and MySQL.  
It allows users to discover government job opportunities, check eligibility, save and track applications,  
and receive structured information automatically extracted from official recruitment PDF notifications.

---

## Features

- **User Authentication** – Register, login, logout with password hashing  
- **User Dashboard** – Stats, expiring jobs, quick actions  
- **Browse & Filter Jobs** – Search, category filter, qualification filter  
- **Save & Track Jobs** – Bookmark jobs, mark as applied  
- **PDF Processing** – Auto-extract qualification, age limit, salary, last date from PDFs  
- **Admin Panel** – Add / Edit / Delete jobs, upload PDFs, manage users  
- **Analytics** – Category-wise charts using Chart.js  
- **Responsive UI** – Bootstrap 5 with sidebar navigation  

---

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Frontend   | HTML5, CSS3, Bootstrap 5, Font Awesome |
| Backend    | Python Flask                      |
| Database   | MySQL                             |
| PDF        | pdfplumber + Regular Expressions  |
| Charts     | Chart.js                          |

---

## Project Structure

```
JobSphere/
├── app.py                  # Main Flask application
├── config.py               # Configuration (DB, upload settings)
├── create_admin.py         # Script to create admin account
├── requirements.txt        # Python dependencies
├── database/
│   └── schema.sql          # MySQL schema
├── templates/
│   ├── base.html           # Base layout (navbar + sidebar)
│   ├── index.html          # Public homepage
│   ├── register.html       # User registration
│   ├── login.html          # User login
│   ├── dashboard.html      # User dashboard
│   ├── jobs.html           # Browse & filter jobs
│   ├── job_detail.html     # Single job detail
│   ├── saved_jobs.html     # Bookmarked jobs
│   ├── applied_jobs.html   # Application tracker
│   ├── profile.html        # Edit profile
│   └── admin/
│       ├── login.html      # Admin login
│       ├── dashboard.html  # Admin dashboard + charts
│       ├── jobs.html       # Manage all jobs
│       ├── add_job.html    # Add job + PDF extraction
│       ├── edit_job.html   # Edit existing job
│       └── users.html      # View registered users
├── static/
│   ├── css/style.css       # Main stylesheet
│   └── js/                 # (JS files if added)
├── uploads/pdfs/           # Uploaded PDF notifications
└── utils/
    └── pdf_extractor.py    # PDF text extraction logic
```

---

## Setup Instructions

### Step 1 – Prerequisites
- Python 3.8 or above
- MySQL Server
- pip

### Step 2 – Clone / Extract Project
```bash
cd JobSphere
```

### Step 3 – Install Python Dependencies
```bash
pip install -r requirements.txt
```

> **Note:** On some systems you may need `pip install mysqlclient` separately.  
> For Linux: `sudo apt-get install libmysqlclient-dev` first.

### Step 4 – Set Up MySQL Database
Open MySQL and run:
```sql
source database/schema.sql;
```
Or import it from MySQL Workbench.

### Step 5 – Configure Database Connection
Edit `config.py`:
```python
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'your_mysql_password'
MYSQL_DB = 'jobsphere_db'
```

### Step 6 – Create Admin Account
```bash
python create_admin.py
```
Default admin: **username:** `admin` | **password:** `admin123`

### Step 7 – Run the Application
```bash
python app.py
```

Visit: **http://localhost:5000**

---

## Usage

### User Flow
1. Register at `/register`
2. Login at `/login`
3. Browse jobs at `/jobs`
4. Save, filter, mark as applied

### Admin Flow
1. Login at `/admin/login` (admin / admin123)
2. Go to **Add Job**
3. Upload a government recruitment PDF → auto-extraction runs
4. Review extracted data, edit if needed, save

---

## PDF Extraction

The system uses **pdfplumber** to read PDF text and **Regex** to find:
- Qualification (looks for degree names, "Educational Qualification" headings)
- Age Limit (e.g., "21 to 35 years", "age limit: 18-27")
- Salary (e.g., "Rs. 56,100", "Pay Band-2")
- Last Date (e.g., "Last Date: 30/06/2024")

Extracted data appears pre-filled in the form for admin review before saving.

---

## Security
- Passwords hashed with `werkzeug.security` (PBKDF2-SHA256)
- SQL queries use parameterized statements (no SQL injection)
- File uploads restricted to `.pdf` only, max 16MB
- Sessions managed by Flask (server-side)

---

*Built for MCA Final Year Project | JobSphere v1.0*
