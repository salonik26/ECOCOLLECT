
# EcoCollect ♻️

EcoCollect is an e-waste collection and recycling platform. It helps users request electronic-waste pickups and connects them with collectors and recycling centres.

## Features

- User registration and login
- Separate dashboards for users, collectors and recyclers
- E-waste photo upload
- Demo e-waste category identification
- Doorstep pickup requests
- Pickup status updates
- Green Points system
- SQLite database

## Technology Used

- Python
- Flask
- SQLite
- HTML
- CSS

## Project Structure

```text
ECOCOLLECT/
│
├── app.py
├── requirements.txt
├── README.md
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── auth.html
│   └── dashboard.html
│
└── static/
    ├── style.css
    └── uploads/
```

## Installation and Setup

### 1. Open the project folder

Open the ECOCOLLECT folder in VS Code.

### 2. Create a virtual environment

```powershell
py -3.13 -m venv venv
```

### 3. Activate the virtual environment

```powershell
venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\Activate.ps1
```

### 4. Install the required packages

```powershell
python -m pip install -r requirements.txt
```

### 5. Run the application

```powershell
python app.py
```

### 6. Open the website

Visit this address in your browser:

http://127.0.0.1:5000

## Demo Login Accounts

| Role | Email |
|---|---|
| User | user@ecocollect.demo |
| Collector | collector@ecocollect.demo |
| Recycler | recycler@ecocollect.demo |

**Demo password for all accounts:** `demo1234`

## Important Note

The current e-waste identification feature is a prototype that uses the uploaded filename to suggest a category. It does not perform real AI image recognition.

The database uses SQLite and is created automatically when the application starts.

## Future Improvements

- Real AI-based e-waste image recognition
- Live pickup tracking
- Verified recycling-centre directory
- Notifications
- Improved Green Rewards system

---

**EcoCollect — Collect today. Protect tomorrow.**
