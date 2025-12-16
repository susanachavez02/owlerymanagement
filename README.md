# Owlery Management System

A comprehensive legal case management platform designed for attorneys and clients to streamline case workflows, communication, document management, and billing.

## 🌟 Features

- **Case Management** - Track cases through customizable workflow stages
- **Client Portal** - Secure communication between attorneys and clients
- **Document Generation** - Create contracts and legal documents from templates
- **Consultation Scheduling** - Book and manage client meetings
- **Calendar Integration** - View deadlines, meetings, and important dates
- **User Management** - Role-based access for admins, attorneys, and clients
- **Automated Workflows** - Define case stages and transitions

## 🛠️ Technology Stack

- **Backend:** Django 5.2.7
- **Language:** Python 3.12
- **Database:** SQLite (dev) / PostgreSQL (production)
- **Frontend:** Bootstrap 5, HTML5, CSS3
- **PDF Generation:** WeasyPrint
- **Document Processing:** python-docx
- **Payment Processing:** Stripe
- **Authentication:** Django built-in auth system

## 📋 Prerequisites

- Python 3.12+
- pip (Python package manager)
- Virtual environment (recommended)
- Git

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/susanachavez02/owlerymanagement.git
cd owlerymanagement
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Variables
Create a `.env` file in the root directory with the following:
```
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
STRIPE_PUBLIC_KEY=your-stripe-public-key
STRIPE_SECRET_KEY=your-stripe-secret-key
```

### 5. Database Setup
```bash
python manage.py migrate
python manage.py createsuperuser  # Create admin account
```

### 6. Run the Development Server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your browser.

## 📁 Project Structure

```
owlerymanagement/
├── cases/              # Case management, workflows, documents
├── communication/      # Messaging system between users
├── users/              # User authentication and profiles
├── owleryconfig/       # Project settings and configuration
├── templates/          # HTML templates
├── static/             # CSS, JavaScript, images
├── db.sqlite3          # SQLite database (development)
├── manage.py           # Django management script
└── requirements.txt    # Python dependencies
```

## 🔧 Common Commands

### Development
```bash
# Activate virtual environment
source venv/bin/activate

# Run development server
python manage.py runserver

# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files (for production)
python manage.py collectstatic
```

### Git Workflow
```bash
# Pull latest changes
git pull

# Check status
git status

# Add changes
git add .

# Commit changes
git commit -m "Description of changes"

# Push to remote
git push origin main
```

## 🎯 Quick Start Guide

1. **Create a superuser** to access the admin panel
2. **Log in** at `/admin/` to configure the system
3. **Create workflows** to define case stages
4. **Add attorneys** through user management
5. **Create registration keys** for new clients
6. **Start managing cases** through the dashboard

## 🐛 Troubleshooting

### Server won't start - Missing dependencies
```bash
pip install -r requirements.txt
```

### Database errors - Unapplied migrations
```bash
python manage.py migrate
```

### Module not found errors
Make sure your virtual environment is activated:
```bash
source venv/bin/activate
```

### Static files not loading
```bash
python manage.py collectstatic
```

## 📦 Main Dependencies

- Django 5.2.7 - Web framework
- django-crispy-forms - Form styling
- djangorestframework - API development
- WeasyPrint - PDF generation
- python-docx - Document processing
- Stripe - Payment processing
- psycopg2-binary - PostgreSQL adapter

## 👥 User Roles

- **Admin** - Full system access and configuration
- **Attorney** - Case management, client communication
- **Client** - View cases, upload documents, communicate

## 📞 Support

For questions or issues, contact:
- Email: support@owlerylegal.com
- Phone: +1 (555) 019-2834

## 📄 License

This project is proprietary software for Owlery Legal.

## 🤝 Contributing

This is a private repository. For team members:
1. Create a new branch for features
2. Test thoroughly before committing
3. Submit pull requests for review
4. Keep commits focused and well-documented

---

**Last Updated:** December 2025 