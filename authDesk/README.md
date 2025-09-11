# Auth Tab UI & API Integration Guide

This README is for Android developers building the Auth Tab (login, registration, password, JWT) using Jetpack Compose, powered by the Django backend in `authDesk`.

---

## 1. Overview
The Auth Tab handles user authentication, registration, password management, and token-based login/logout. All data is served by the Django backend (`authDesk`).

## 2. Key API Endpoints & URLs

## Base URL & Environment
Set your base URL according to your Django server settings in `settings.py`:
```
http://<your-server-domain-or-ip>:8000
```
For local development, use your machine's IP (e.g., `192.168.1.4:8000`) or `localhost:8000`.
For production, set your domain and ensure HTTPS is enabled in `settings.py`.


**API Endpoints:**
- **Signup/Register:**
    - URL: `POST <base-url>/api/auth/signup/`
    - Fields required: username, full_name, email, mobile_number, password, terms_accepted
- **Login:**
    - URL: `POST <base-url>/api/auth/login/`
    - Fields required: username/email, password
- **Logout:** `POST <base-url>/api/auth/logout/`
- **Refresh Token:** `POST <base-url>/api/auth/token/refresh/`
- **Password Reset:** `POST <base-url>/api/auth/password/reset/`
- **Password Change:** `POST <base-url>/api/auth/password/change/`
- **Profile:** `GET <base-url>/api/profile/` (after login, see profileDesk for details)

**Note:**
- All endpoints are relative to your base URL (see above).
- For Android, store the base URL in a config file or constant for easy switching between dev/staging/prod.

## 3. Data Models
- **User (profileDesk):**
    - `id`: Int
    - `username`: String
    - `full_name`: String
    - `email`: String
    - `mobile_number`: String
    - `profile_image`: URL
    - `badge`: String
    - `bio`/`about`: String
    - `followers_count`, `following_count`, `posts_count`: Int
- **JWT Token:** access, refresh

## 4. UI Structure (Jetpack Compose)
- **LoginScreen**: Username/email, password, login button, error messages
- **SignupScreen**: Username, full name, email, mobile number, password, confirm password, terms checkbox, signup button, error messages
- **ForgotPasswordScreen**: Email input, send reset link
- **ChangePasswordScreen**: Old password, new password, confirm new password
- **ProfileScreen**: After login, show user info (from profileDesk)
- **Loading/Error/EmptyState**: For feedback

## 5. API Integration Steps (Android)
1. **Set base URL** in your app config (match Django `settings.py`)
2. **Signup/Register**:
    - Use the signup endpoint (`/api/auth/signup/`)
    - Validate all fields before sending (empty, duplicate, invalid format, terms not accepted)
    - Show error messages from API response
    - On success, store tokens and user info
3. **Login**:
    - Use the login endpoint (`/api/auth/login/`)
    - Send username/email and password
    - On success, store tokens and user info
    - Show error messages for invalid credentials
4. **Store tokens** securely (DataStore/EncryptedSharedPrefs)
5. **Use access token** for authenticated requests (add `Authorization: Bearer <token>` header)
6. **Refresh token** when access expires
7. **Profile fetch**: After login, fetch user info from profileDesk
8. **Password reset/change**: Send requests, handle feedback
9. **Logout**: Clear tokens, navigate to login
10. **Show loading/error states**

## 6. UI/UX Notes
- Use Material Design components
- Responsive layouts for all screen sizes
- Accessibility: content descriptions, readable fonts, color contrast
- Show clear error messages for failed login/registration/signup
- Use progress indicators while authenticating or registering
- Securely store tokens
- Validate input fields (email, password strength, mobile format, terms checkbox)
- Show success/failure toasts/snackbars

## 7. Example Signup & Login API Request/Response
**Signup Request:**
POST `<base-url>/api/auth/signup/`
```json
{
  "username": "tarunbawari",
  "full_name": "Tarun Bawari",
  "email": "tarunbawari@gmail.com",
  "mobile_number": "9876543210",
  "password": "yourpassword",
  "terms_accepted": true
}
```
**Signup Response:**
```json
{
  "token": "<access_token>",
  "refresh_token": "<refresh_token>",
  "userId": 9,
  "username": "tarunbawari"
}
```

**Login Request:**
POST `<base-url>/api/auth/login/`
```json
{
  "username": "tarunbawari",
  "password": "yourpassword"
}
```
**Login Response:**
```json
{
  "token": "<access_token>",
  "refresh_token": "<refresh_token>",
  "userId": 9,
  "username": "tarunbawari"
}
```

## 8. Component Placement Example
```
| LoginScreen         |
|---------------------|
| SignupScreen        |
|---------------------|
| ForgotPasswordScreen|
|---------------------|
| ChangePasswordScreen|
|---------------------|
| ProfileScreen       |
|---------------------|
```

## 9. Contact & Contribution
- For backend/API questions, contact the Django team
- For UI/UX suggestions, contact the Android team
- For user info/profile details, see profileDesk README

---

**Keep this README updated as backend or UI changes!**
