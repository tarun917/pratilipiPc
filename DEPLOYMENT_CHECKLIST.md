# 🚀 Pratilipi Box Backend - Production Deployment Checklist

> **Project:** pratilipiPc (Django 5.2.4 Backend for Pratilipi Box Android App)  
> **Last Updated:** December 2024

---

## 📋 Project Overview

### Tech Stack
- **Framework:** Django 5.2.4 + Django REST Framework 3.16.0
- **Database:** MySQL (mysqlclient 2.2.7)
- **Cache:** Redis (django-redis 6.0.0)
- **Auth:** JWT (djangorestframework-simplejwt 5.5.0)
- **Payments:** Razorpay + Google Play Billing
- **Storage:** AWS S3 (optional, django-storages 1.14.6)
- **Server:** Gunicorn 23.0.0

### Django Apps (16 total)
| App | Purpose |
|-----|---------|
| `profileDesk` | Custom User Model, Addresses |
| `authDesk` | Login, Signup, Logout, JWT Token Refresh |
| `communityDesk` | Posts, Comments, Polls, Likes, Follows |
| `storeDesk` | Physical Comics Store, Orders, Reviews, Wishlist, Promotions |
| `homeDesk` | Home Tab Configuration |
| `digitalcomicDesk` | Digital Comics, Episodes, Slices, Episode Access |
| `motioncomicDesk` | Motion Comics (Video), Episodes, Access |
| `premiumDesk` | Subscriptions, Wallet Ledger |
| `coinManagementDesk` | User Coin Balance |
| `favouriteDesk` | User Favourites |
| `searchDesk` | Search Filters |
| `notificationDesk` | Notifications, Device Tokens (FCM ready) |
| `carouselDesk` | Home Carousel Items |
| `creatorDesk` | Creator Submissions, Terms & Conditions |
| `paymentsDesk` | Razorpay & Google Play Payment Processing |
| `readingActivityDesk` | Reading Progress Tracking |

---

## ✅ Pre-Deployment Checklist

### 1. Environment Variables (.env file)
> Create `.env` file on server with these variables:

```bash
# [ ] Required - Django Core
SECRET_KEY=<generate-new-50-char-random-key>
DEBUG=False

# [ ] Required - Database (MySQL)
DB_USER=<mysql_username>
DB_PASSWORD=<mysql_password>
# Note: DB_HOST is hardcoded as 'localhost' in settings.py - change if needed

# [ ] Required - Razorpay (for payments)
RAZORPAY_KEY_ID=<your_razorpay_key_id>
RAZORPAY_KEY_SECRET=<your_razorpay_key_secret>
RAZORPAY_WEBHOOK_SECRET=<your_webhook_secret>

# [ ] Optional - AWS S3 (for media storage)
ENABLE_S3=1
AWS_ACCESS_KEY_ID=<your_aws_access_key>
AWS_SECRET_ACCESS_KEY=<your_aws_secret_key>
AWS_STORAGE_BUCKET_NAME=<your_bucket_name>
AWS_S3_REGION_NAME=ap-south-1

# [ ] Optional - Google Play Billing
GOOGLE_PLAY_PACKAGE_NAME=com.pratilipi.box
COIN_PACK_SKUS={"coins_100":100,"coins_250":250,"coins_500":500,"coins_1000":1000}
SUB_PLAN_SKUS={"premium_3m":{"plan":"3_month"},"premium_6m":{"plan":"6_month"},"premium_12m":{"plan":"12_month"}}
```

---

### 2. Settings.py Changes for Production

| Task | File | Status |
|------|------|--------|
| [ ] Set `DEBUG = False` | `pratilipiPc/settings.py:15` | Pending |
| [ ] Update `ALLOWED_HOSTS` with actual domain/IP | `pratilipiPc/settings.py:16` | Pending |
| [ ] Add `STATIC_ROOT` for collectstatic | `pratilipiPc/settings.py` | **Missing** |
| [ ] Enable SSL settings | `pratilipiPc/settings.py:198-201` | Pending |
| [ ] Remove `debug_toolbar` from production | `pratilipiPc/settings.py:47,75` | Pending |
| [ ] Update `DATABASES['HOST']` if not localhost | `pratilipiPc/settings.py:114` | Pending |
| [ ] Update Redis `LOCATION` if not localhost | `pratilipiPc/settings.py:127` | Pending |

#### Required Code Changes:

**Add STATIC_ROOT (missing):**
```python
# Add after line 152 in settings.py
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

**Production Security Settings (update lines 198-204):**
```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
```

**Conditional Debug Toolbar:**
```python
# Modify INSTALLED_APPS to conditionally include debug_toolbar
if DEBUG:
    INSTALLED_APPS.append('debug_toolbar')
```

---

### 3. Database Setup

| Task | Command/Action | Status |
|------|----------------|--------|
| [ ] Install MySQL Server on production | `apt install mysql-server` | Pending |
| [ ] Create database | `CREATE DATABASE pratilipipcdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;` | Pending |
| [ ] Create MySQL user | `CREATE USER 'pratilipi_user'@'localhost' IDENTIFIED BY 'secure_password';` | Pending |
| [ ] Grant permissions | `GRANT ALL PRIVILEGES ON pratilipipcdb.* TO 'pratilipi_user'@'localhost';` | Pending |
| [ ] Run migrations | `python manage.py migrate` | Pending |
| [ ] Create superuser | `python manage.py createsuperuser` | Pending |

---

### 4. Redis Setup

| Task | Command/Action | Status |
|------|----------------|--------|
| [ ] Install Redis | `apt install redis-server` | Pending |
| [ ] Start Redis | `systemctl start redis` | Pending |
| [ ] Enable Redis on boot | `systemctl enable redis` | Pending |
| [ ] Test Redis | `redis-cli ping` (should return PONG) | Pending |

---

### 5. Static & Media Files

| Task | Command/Action | Status |
|------|----------------|--------|
| [ ] Add STATIC_ROOT to settings | See code above | Pending |
| [ ] Run collectstatic | `python manage.py collectstatic` | Pending |
| [ ] Create media directories | Already exist in project | ✅ Done |
| [ ] Configure Nginx for static/media | See Nginx config below | Pending |
| [ ] (Optional) Setup S3 for media | Configure AWS env vars | Pending |

**Media Directories (already created):**
- `media/carousel/`
- `media/comics/`
- `media/digitalcomics/`
- `media/motioncomics/`
- `media/posts/`
- `media/profiles/`
- `media/submissions/`

---

### 6. Dependencies Installation

```bash
# [ ] Create virtual environment
python3 -m venv venv
source venv/bin/activate

# [ ] Install dependencies
pip install -r requirements.txt

# [ ] Install additional production dependencies
pip install whitenoise  # For static files (optional)
```

---

### 7. CORS Configuration (Missing - Required for Android App)

| Task | Status |
|------|--------|
| [ ] Install django-cors-headers | `pip install django-cors-headers` | Pending |
| [ ] Add to INSTALLED_APPS | Pending |
| [ ] Add CorsMiddleware | Pending |
| [ ] Configure CORS_ALLOWED_ORIGINS | Pending |

**Add to requirements.txt:**
```
django-cors-headers==4.3.1
```

**Add to settings.py:**
```python
INSTALLED_APPS = [
    ...
    'corsheaders',
    ...
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Add at top
    ...
]

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True  # For development
# OR for production:
# CORS_ALLOWED_ORIGINS = [
#     "https://yourdomain.com",
# ]
CORS_ALLOW_CREDENTIALS = True
```

---

### 8. Gunicorn Configuration

| Task | Status |
|------|--------|
| [ ] Create gunicorn config file | Pending |
| [ ] Create systemd service | Pending |

**Create `/etc/systemd/system/pratilipi.service`:**
```ini
[Unit]
Description=Pratilipi Box Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/pratilipiPc
Environment="PATH=/path/to/pratilipiPc/venv/bin"
ExecStart=/path/to/pratilipiPc/venv/bin/gunicorn --workers 3 --bind unix:/path/to/pratilipiPc/pratilipi.sock pratilipiPc.wsgi:application

[Install]
WantedBy=multi-user.target
```

---

### 9. Nginx Configuration

**Create `/etc/nginx/sites-available/pratilipi`:**
```nginx
server {
    listen 80;
    server_name your_domain_or_ip;

    location /static/ {
        alias /path/to/pratilipiPc/staticfiles/;
    }

    location /media/ {
        alias /path/to/pratilipiPc/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/path/to/pratilipiPc/pratilipi.sock;
    }

    client_max_body_size 100M;  # For large file uploads
}
```

---

### 10. SSL/HTTPS Setup

| Task | Status |
|------|--------|
| [ ] Install Certbot | `apt install certbot python3-certbot-nginx` | Pending |
| [ ] Obtain SSL certificate | `certbot --nginx -d yourdomain.com` | Pending |
| [ ] Auto-renewal setup | `certbot renew --dry-run` | Pending |

---

### 11. Payment Gateway Setup

#### Razorpay
| Task | Status |
|------|--------|
| [ ] Create Razorpay account | Pending |
| [ ] Get API keys (Test/Live) | Pending |
| [ ] Configure webhook URL | `https://yourdomain.com/api/payments/razorpay/webhook/razorpay/` | Pending |
| [ ] Set webhook secret in .env | Pending |

#### Google Play Billing
| Task | Status |
|------|--------|
| [ ] Setup Google Play Console | Pending |
| [ ] Create Service Account for API | Pending |
| [ ] Configure in-app products (coins) | Pending |
| [ ] Configure subscriptions | Pending |
| [ ] Implement real verification (currently placeholder) | **TODO in code** |

---

### 12. Admin Panel Setup

| Task | Status |
|------|--------|
| [ ] Create superuser | `python manage.py createsuperuser` | Pending |
| [ ] Access admin at `/admin/` | Pending |
| [ ] Add initial data (Genres, Carousels, etc.) | Pending |

---

### 13. Logging Configuration

**Add to settings.py:**
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs/error.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
```

---

### 14. Security Checklist

| Task | Status |
|------|--------|
| [ ] Generate new SECRET_KEY for production | Pending |
| [ ] Set DEBUG=False | Pending |
| [ ] Configure ALLOWED_HOSTS properly | Pending |
| [ ] Enable HTTPS | Pending |
| [ ] Remove debug.log from production | Pending |
| [ ] Secure .env file permissions | `chmod 600 .env` | Pending |
| [ ] Configure firewall (UFW) | Pending |

---

### 15. API Endpoints Reference

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/signup/` | POST | No | User registration |
| `/api/auth/login/` | POST | No | User login |
| `/api/auth/logout/` | POST | Yes | User logout |
| `/api/auth/token/refresh/` | POST | No | Refresh JWT token |
| `/api/profile/` | GET/PUT | Yes | User profile |
| `/api/community/` | Various | Mixed | Posts, comments, follows |
| `/api/store/` | Various | Mixed | Comics store |
| `/api/home/` | GET | No | Home screen data |
| `/api/premium/` | Various | Yes | Subscriptions |
| `/api/coin/` | Various | Yes | Coin management |
| `/api/digitalcomic/` | Various | Mixed | Digital comics |
| `/api/motioncomic/` | Various | Mixed | Motion comics |
| `/api/favourite/` | Various | Yes | User favourites |
| `/api/search/` | GET | No | Search |
| `/api/notification/` | Various | Yes | Notifications |
| `/api/carousel/` | GET | No | Carousel items |
| `/api/creator/` | Various | Yes | Creator submissions |
| `/api/payments/razorpay/` | Various | Yes | Razorpay payments |
| `/api/payments/play/verify/` | POST | Yes | Google Play verification |
| `/api/activity/` | Various | Yes | Reading activity |
| `/admin/` | GET | Admin | Django Admin Panel |

---

## 🔄 Deployment Steps (Order)

```bash
# 1. Server Setup
[ ] Setup server (AWS/Heroku/DigitalOcean/etc.)
[ ] Install Python 3.11+, MySQL, Redis, Nginx

# 2. Code Deployment
[ ] Clone repository
[ ] Create virtual environment
[ ] Install dependencies
[ ] Create .env file with all variables

# 3. Database
[ ] Create MySQL database and user
[ ] Run migrations: python manage.py migrate
[ ] Create superuser: python manage.py createsuperuser

# 4. Static Files
[ ] Add STATIC_ROOT to settings
[ ] Run: python manage.py collectstatic

# 5. Services
[ ] Configure Gunicorn systemd service
[ ] Configure Nginx
[ ] Start services

# 6. SSL
[ ] Setup SSL with Certbot

# 7. Testing
[ ] Test all API endpoints
[ ] Test admin panel
[ ] Test payment flows (test mode)

# 8. Go Live
[ ] Switch to production payment keys
[ ] Monitor logs
```

---

## ⚠️ Known Issues / TODOs

1. **Google Play Verification:** Currently placeholder in DEBUG mode. Need to implement actual Google Play Developer API verification for production.

2. **CORS:** Not configured. Required for Android app to communicate with backend.

3. **STATIC_ROOT:** Missing in settings.py. Required for collectstatic.

4. **Debug Toolbar:** Should be conditionally loaded only in DEBUG mode.

5. **Logging:** Basic logging exists but production logging config should be added.

6. **Whitenoise:** Consider adding for serving static files without Nginx.

---

## 📞 Support Contacts

- **Developer:** [Your Name]
- **Server Admin:** [Admin Name]
- **Razorpay Support:** https://razorpay.com/support/

---

**Note:** Aap jab bhi deployment platform (AWS, Heroku, DigitalOcean, etc.) decide kar lein, mujhe batayein - main platform-specific instructions add kar dunga.
