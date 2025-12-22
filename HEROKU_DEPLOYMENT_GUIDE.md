# 🚀 Heroku Deployment Guide - Pratilipi Box Backend

> **Complete step-by-step guide for deploying Django backend to Heroku**

---

## 📋 Pre-Deployment Checklist

### ✅ Files Created/Modified:
- [x] `Procfile` - Heroku process configuration
- [x] `runtime.txt` - Python version specification
- [x] `requirements.txt` - Updated with Heroku dependencies
- [x] `settings.py` - Production-ready configuration

### ✅ Dependencies Added:
- [x] `whitenoise==6.6.0` - Static file serving
- [x] `dj-database-url==2.1.0` - Database URL parsing
- [x] `psycopg2-binary==2.9.9` - PostgreSQL adapter
- [x] `django-cors-headers==4.3.1` - CORS for Android app

---

## 🔧 Step 1: Install Heroku CLI

### macOS:
```bash
brew tap heroku/brew && brew install heroku
```

### Verify Installation:
```bash
heroku --version
```

---

## 🔐 Step 2: Login to Heroku

```bash
heroku login
```

---

## 📦 Step 3: Create Heroku App

```bash
# Navigate to your project directory
cd /Users/tarundaharwal/pratilipiPc

# Create Heroku app (replace 'your-app-name' with unique name)
heroku create pratilipi-box-backend

# Or let Heroku generate a name
heroku create
```

---

## 🗄️ Step 4: Add Database (PostgreSQL)

```bash
# Add Heroku Postgres (Hobby Dev - Free)
heroku addons:create heroku-postgresql:hobby-dev

# Add Redis (Hobby Dev - Free with student credits)
heroku addons:create heroku-redis:hobby-dev
```

---

## 🔑 Step 5: Set Environment Variables

```bash
# Required Django settings
heroku config:set SECRET_KEY="your-super-secret-key-here-50-characters-long"
heroku config:set DEBUG=False

# Razorpay settings (get from Razorpay dashboard)
heroku config:set RAZORPAY_KEY_ID="rzp_test_xxxxxxxxxx"
heroku config:set RAZORPAY_KEY_SECRET="your_razorpay_secret"
heroku config:set RAZORPAY_WEBHOOK_SECRET="your_webhook_secret"

# Google Play settings (optional)
heroku config:set GOOGLE_PLAY_PACKAGE_NAME="com.pratilipi.box"
heroku config:set COIN_PACK_SKUS='{"coins_100":100,"coins_250":250,"coins_500":500,"coins_1000":1000}'

# AWS S3 settings (optional - for media files)
heroku config:set ENABLE_S3=1
heroku config:set AWS_ACCESS_KEY_ID="your_aws_access_key"
heroku config:set AWS_SECRET_ACCESS_KEY="your_aws_secret_key"
heroku config:set AWS_STORAGE_BUCKET_NAME="your-bucket-name"
heroku config:set AWS_S3_REGION_NAME="ap-south-1"

# Check all config vars
heroku config
```

### 🔐 Generate SECRET_KEY:
```python
# Run this in Python shell to generate SECRET_KEY
import secrets
print(secrets.token_urlsafe(50))
```

---

## 📤 Step 6: Deploy to Heroku

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit for Heroku deployment"

# Add Heroku remote
heroku git:remote -a your-app-name

# Deploy to Heroku
git push heroku main
```

### If you're on a different branch:
```bash
git push heroku your-branch:main
```

---

## 🗄️ Step 7: Run Database Migrations

```bash
# Run migrations on Heroku
heroku run python manage.py migrate

# Create superuser
heroku run python manage.py createsuperuser

# Collect static files (if needed)
heroku run python manage.py collectstatic --noinput
```

---

## 🌐 Step 8: Open Your App

```bash
# Open app in browser
heroku open

# Check logs
heroku logs --tail
```

---

## 📱 Step 9: Test API Endpoints

Your app will be available at: `https://your-app-name.herokuapp.com`

### Test these endpoints:
- `GET /` - Welcome page
- `GET /admin/` - Admin panel
- `POST /api/auth/signup/` - User registration
- `POST /api/auth/login/` - User login
- `GET /api/home/` - Home data

---

## 🔧 Step 10: Configure Custom Domain (Optional)

```bash
# Add custom domain
heroku domains:add yourdomain.com

# Get DNS target
heroku domains
```

---

## 📊 Monitoring & Maintenance

### View Logs:
```bash
heroku logs --tail
heroku logs --source app
```

### Scale Dynos:
```bash
# Check current dynos
heroku ps

# Scale web dynos (with student credits)
heroku ps:scale web=1
```

### Database Management:
```bash
# Access database
heroku pg:psql

# Database info
heroku pg:info

# Reset database (DANGER!)
heroku pg:reset DATABASE_URL
```

---

## 🚨 Troubleshooting

### Common Issues:

#### 1. **Build Failed - Missing Dependencies**
```bash
# Check requirements.txt format
# Ensure no extra spaces or invalid versions
```

#### 2. **Application Error (H10)**
```bash
# Check logs
heroku logs --tail

# Usually missing Procfile or wrong process type
```

#### 3. **Database Connection Error**
```bash
# Check if DATABASE_URL is set
heroku config:get DATABASE_URL

# Run migrations
heroku run python manage.py migrate
```

#### 4. **Static Files Not Loading**
```bash
# Collect static files
heroku run python manage.py collectstatic --noinput

# Check STATIC_ROOT in settings.py
```

#### 5. **CORS Errors from Android App**
```bash
# Verify CORS settings in settings.py
# Check if corsheaders is in INSTALLED_APPS
```

---

## 💰 Cost Estimation (with GitHub Student Pack)

| Service | Student Price | Regular Price |
|---------|---------------|---------------|
| **Hobby Dyno** | FREE ($13 credit) | $7/month |
| **Heroku Postgres** | FREE (included) | $9/month |
| **Heroku Redis** | FREE (included) | $15/month |
| **Custom Domain** | FREE | FREE |
| **SSL Certificate** | FREE | FREE |
| **Total** | **$0/month** | $31/month |

**Duration:** 24 months with student pack

---

## 🔄 Continuous Deployment

### Auto-deploy from GitHub:
1. Go to Heroku Dashboard
2. Select your app
3. Go to "Deploy" tab
4. Connect to GitHub repository
5. Enable "Automatic deploys" from main branch

---

## 📞 Support & Resources

- **Heroku Docs:** https://devcenter.heroku.com/
- **Django on Heroku:** https://devcenter.heroku.com/articles/django-app-configuration
- **Student Pack:** https://www.heroku.com/github-students

---

## 🎯 Next Steps After Deployment

1. **Test all API endpoints** with Postman/Android app
2. **Setup monitoring** with Heroku metrics
3. **Configure domain** if needed
4. **Setup CI/CD** with GitHub Actions
5. **Monitor logs** regularly
6. **Backup database** periodically

---

## 📝 Important URLs

- **App URL:** `https://your-app-name.herokuapp.com`
- **Admin Panel:** `https://your-app-name.herokuapp.com/admin/`
- **API Base:** `https://your-app-name.herokuapp.com/api/`

---

**🎉 Congratulations! Your Pratilipi Box backend is now live on Heroku!**
