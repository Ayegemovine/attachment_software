@(
# Attachment Management System - Eujim Solutions Ltd

A professional Django-based platform designed to manage industrial attachments, track applicant progress, and generate branded certification documents.

## ?? Features
- **Branded Document Generation:** Automated generation of Completion Letters, Recommendation Letters, and ID Cards with QR code verification.
- **Dynamic Dashboard:** Admin review board with 'Pending' default view, scalable row management (5-100 rows), and cross-device optimization.
- **Automated Communication:** Email triggers for application receipt and status updates (Approved, Admitted, Rejected, Completed).
- **Advanced Search:** Multi-parameter search by Tracking ID, Email, or National ID.
- **Data Portability:** Support for CSV Import/Export of attachee records.

## ??? Tech Stack
- **Backend:** Django 6.0.1 / Python 3.13
- **PDF Engine:** ReportLab
- **Database:** SQLite (Development)
- **Frontend:** Bootstrap 5 with custom Branded CSS

## ?? Setup Instructions
1. Clone the repository:
   \\\ash
   git clone <your-repository-url>
   \\\
2. Install dependencies:
   \\\ash
   pip install django reportlab qrcode pillow
   \\\
3. Run migrations:
   \\\ash
   python manage.py migrate
   \\\
4. Start the server for local network testing:
   \\\ash
   python manage.py runserver 0.0.0.0:8000
   \\\

---
© 2026 Eujim Solutions Limited. All Rights Reserved.
)
