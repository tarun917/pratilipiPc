# API Documentation for Jetpack Compose App Integration

## Base URL
```
https://your-domain.com/api/
```

## Authentication
All API endpoints (except auth endpoints) require JWT authentication.

### Headers
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## 🔐 Authentication Endpoints

### 1. User Registration
```http
POST /api/auth/signup/
```

**Request Body:**
```json
{
    "username": "string",
    "email": "string",
    "password": "string",
    "full_name": "string",
    "mobile_number": "string",
    "terms_accepted": true
}
```

**Response:**
```json
{
    "user": {
        "id": 1,
        "username": "string",
        "email": "string",
        "full_name": "string",
        "mobile_number": "string",
        "unique_id": "uuid",
        "profile_image": "url",
        "about": "string",
        "coin_count": 0,
        "is_active": true
    },
    "access": "jwt_token",
    "refresh": "jwt_refresh_token"
}
```

### 2. User Login
```http
POST /api/auth/login/
```

**Request Body:**
```json
{
    "username": "string",
    "password": "string"
}
```

**Response:**
```json
{
    "user": {
        "id": 1,
        "username": "string",
        "email": "string",
        "full_name": "string",
        "mobile_number": "string",
        "unique_id": "uuid",
        "profile_image": "url",
        "about": "string",
        "coin_count": 0,
        "is_active": true
    },
    "access": "jwt_token",
    "refresh": "jwt_refresh_token"
}
```

### 3. Logout
```http
POST /api/auth/logout/
```

**Request Body:**
```json
{
    "refresh": "jwt_refresh_token"
}
```

---

## 👤 Profile Endpoints

### 1. Get User Profile
```http
GET /api/profile/
```

**Response:**
```json
{
    "id": 1,
    "username": "string",
    "email": "string",
    "full_name": "string",
    "mobile_number": "string",
    "unique_id": "uuid",
    "profile_image": "url",
    "about": "string",
    "coin_count": 0,
    "is_active": true
}
```

### 2. Update User Profile
```http
PATCH /api/profile/
```

**Request Body:**
```json
{
    "full_name": "string",
    "about": "string",
    "mobile_number": "string"
}
```

### 3. Upload Profile Picture
```http
POST /api/profile/picture/
```

**Request Body:** (multipart/form-data)
```
profile_image: file
```

---

## 🏪 Store Endpoints

### 1. Get All Comics
```http
GET /api/store/comics/
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 10)
- `genre`: Filter by genre ID
- `search`: Search by title

**Response:**
```json
{
    "count": 100,
    "next": "url",
    "previous": "url",
    "results": [
        {
            "id": 1,
            "title": "string",
            "cover_image": "url",
            "price": "decimal",
            "discount_price": "decimal",
            "description": "string",
            "pages": 50,
            "rating": 4.5,
            "rating_count": 100,
            "buyer_count": 250,
            "stock_quantity": 10,
            "preview_file": "url",
            "genres": [
                {
                    "id": 1,
                    "name": "Action"
                }
            ],
            "created_at": "datetime"
        }
    ]
}
```

### 2. Get Comic Details
```http
GET /api/store/comics/{id}/
```

**Response:**
```json
{
    "id": 1,
    "title": "string",
    "cover_image": "url",
    "price": "decimal",
    "discount_price": "decimal",
    "description": "string",
    "pages": 50,
    "rating": 4.5,
    "rating_count": 100,
    "buyer_count": 250,
    "stock_quantity": 10,
    "preview_file": "url",
    "genres": [
        {
            "id": 1,
            "name": "Action"
        }
    ],
    "created_at": "datetime"
}
```

### 3. Get Genres
```http
GET /api/store/genres/
```

**Response:**
```json
[
    {
        "id": 1,
        "name": "Action",
        "created_at": "datetime"
    }
]
```

### 4. Create Order
```http
POST /api/store/orders/
```

**Request Body:**
```json
{
    "comic": 1,
    "buyer_name": "string",
    "email": "string",
    "mobile": "string"
}
```

### 5. Get User Orders
```http
GET /api/store/orders/
```

**Response:**
```json
[
    {
        "id": 1,
        "comic": {
            "id": 1,
            "title": "string",
            "cover_image": "url",
            "price": "decimal"
        },
        "purchase_date": "datetime",
        "buyer_name": "string",
        "email": "string",
        "mobile": "string"
    }
]
```

### 6. Get Wishlist
```http
GET /api/store/wishlist/
```

### 7. Add to Wishlist
```http
POST /api/store/wishlist/
```

**Request Body:**
```json
{
    "comic": 1
}
```

---

## ❤️ Favourites Endpoints

### 1. Get User Favourites
```http
GET /api/favourites/
```

**Response:**
```json
[
    {
        "id": 1,
        "comic_type": "digital",
        "comic_id": 1,
        "created_at": "datetime"
    }
]
```

### 2. Add to Favourites
```http
POST /api/favourites/
```

**Request Body:**
```json
{
    "comic_type": "digital",
    "comic_id": 1
}
```

### 3. Remove from Favourites
```http
DELETE /api/favourites/{comic_id}/
```

### 4. Check Favourite Status
```http
GET /api/favourites/status/{comic_id}/
```

**Response:**
```json
{
    "is_favourite": true
}
```

### 5. Search Favourites
```http
GET /api/favourites/search/
```

**Query Parameters:**
- `q`: Search query

---

## 🏠 Home Endpoints (Based on existing structure)

### 1. Get Home Configuration
```http
GET /api/home/config/
```

**Response:**
```json
{
    "featured_comics": [
        {
            "id": 1,
            "title": "string",
            "cover_image": "url",
            "price": "decimal"
        }
    ],
    "trending_comics": [
        {
            "id": 1,
            "title": "string",
            "cover_image": "url",
            "rating": 4.5
        }
    ],
    "recent_comics": [
        {
            "id": 1,
            "title": "string",
            "cover_image": "url",
            "created_at": "datetime"
        }
    ]
}
```

---

## 🌐 Community Endpoints

### 1. Get Community Posts
```http
GET /api/community/posts/
```

**Query Parameters:**
- `page`: Page number
- `page_size`: Items per page

**Response:**
```json
{
    "count": 100,
    "next": "url",
    "previous": "url",
    "results": [
        {
            "id": 1,
            "user": {
                "id": 1,
                "username": "string",
                "full_name": "string",
                "profile_image": "url"
            },
            "text": "string",
            "image_url": "url",
            "hashtags": ["tag1", "tag2"],
            "commenting_enabled": true,
            "share_count": 10,
            "created_at": "datetime",
            "updated_at": "datetime",
            "comments": [
                {
                    "id": 1,
                    "user": {
                        "id": 2,
                        "username": "string",
                        "full_name": "string",
                        "profile_image": "url"
                    },
                    "text": "string",
                    "created_at": "datetime"
                }
            ]
        }
    ]
}
```

### 2. Create Post
```http
POST /api/community/posts/
```

**Request Body:** (multipart/form-data)
```
text: string
image_url: file (optional)
hashtags: ["tag1", "tag2"]
commenting_enabled: boolean
```

### 3. Get Post Details
```http
GET /api/community/posts/{id}/
```

### 4. Add Comment
```http
POST /api/community/posts/{id}/comments/
```

**Request Body:**
```json
{
    "text": "string"
}
```

---

## 🔍 Search Endpoints

### 1. Global Search
```http
GET /api/search/
```

**Query Parameters:**
- `q`: Search query
- `type`: Filter by type (comics, posts, users)

**Response:**
```json
{
    "comics": [
        {
            "id": 1,
            "title": "string",
            "cover_image": "url",
            "price": "decimal"
        }
    ],
    "posts": [
        {
            "id": 1,
            "text": "string",
            "user": {
                "username": "string",
                "full_name": "string"
            }
        }
    ],
    "users": [
        {
            "id": 1,
            "username": "string",
            "full_name": "string",
            "profile_image": "url"
        }
    ]
}
```

---

## 🎠 Carousel Endpoints

### 1. Get Carousel Items
```http
GET /api/carousel/
```

**Response:**
```json
[
    {
        "id": 1,
        "title": "string",
        "image": "url",
        "link": "url",
        "order": 1,
        "is_active": true
    }
]
```

---

## 💰 Coin Management Endpoints

### 1. Get User Coins
```http
GET /api/coins/balance/
```

**Response:**
```json
{
    "balance": 100,
    "transactions": [
        {
            "id": 1,
            "amount": 50,
            "transaction_type": "earned",
            "description": "Daily bonus",
            "created_at": "datetime"
        }
    ]
}
```

### 2. Purchase Coins
```http
POST /api/coins/purchase/
```

**Request Body:**
```json
{
    "amount": 100,
    "payment_method": "string"
}
```

---

## 🔔 Notification Endpoints

### 1. Get User Notifications
```http
GET /api/notifications/
```

**Response:**
```json
[
    {
        "id": 1,
        "title": "string",
        "message": "string",
        "is_read": false,
        "created_at": "datetime",
        "notification_type": "general"
    }
]
```

### 2. Mark Notification as Read
```http
PATCH /api/notifications/{id}/
```

**Request Body:**
```json
{
    "is_read": true
}
```

---

## 📱 Android App Specific Considerations

### Error Handling
All API endpoints return consistent error responses:

```json
{
    "error": "string",
    "message": "string",
    "details": {}
}
```

### HTTP Status Codes
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `500`: Internal Server Error

### Pagination
List endpoints support pagination with the following parameters:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 10, max: 100)

### Authentication Flow
1. User logs in → Receives access & refresh tokens
2. Store tokens securely in Android app
3. Include access token in all API requests
4. Refresh token when access token expires
5. Logout → Blacklist refresh token

### Image Handling
- Profile images: `media/profiles/`
- Comic covers: `media/comics/covers/`
- Post images: `media/posts/`
- Preview files: `media/comics/previews/`

### Real-time Features (Future Enhancement)
Consider implementing WebSocket connections for:
- Real-time notifications
- Live community feed updates
- Real-time chat features

This API documentation provides the foundation for seamless integration between your Jetpack Compose Android app and the existing Django backend.