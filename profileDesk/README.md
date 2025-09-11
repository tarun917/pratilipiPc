# Profile Tab UI & API Integration Guide

This README is for Android developers building the Profile Tab using Jetpack Compose, powered by the Django backend in `profileDesk`.

---

## 1. Overview
The Profile Tab displays user information, profile image, badge, bio, stats, and allows editing/updating profile details. All data is served by the Django backend (`profileDesk`).

## 2. Key API Endpoints
- **Get Profile:** `GET /api/profile/`
- **Update Profile:** `PUT /api/profile/`
- **Upload Profile Image:** `POST /api/profile/picture/`
- **Get Followers:** `GET /api/profile/followers/`
- **Get Following:** `GET /api/profile/following/`
- **Get User Posts:** `GET /api/users/{user_id}/posts/`

## 3. Data Model (CustomUser)
- `id`: Int
- `username`: String
- `profile_image`: URL
- `badge`: String
- `bio`: String
- `followers_count`: Int
- `following_count`: Int
- `posts_count`: Int

## 4. UI Structure (Jetpack Compose)
- **ProfileHeader**: Shows profile image, username, badge
- **ProfileStats**: Followers, Following, Posts
- **ProfileBio**: User bio/description
- **ProfileActions**: Edit profile, upload image
- **ProfileTabs**: Switch between posts, followers, following

## 5. API Integration Steps
1. **Fetch profile data** on tab load
2. **Display profile image, username, badge** in header
3. **Show stats** (followers, following, posts)
4. **Show bio**
5. **Edit profile**: open edit screen, send update request
6. **Upload image**: open image picker, send upload request
7. **Tabs**: fetch and display posts, followers, following

## 6. UI/UX Notes
- Use Material Design components
- Show loading and error states
- Use smooth transitions for tab switching and image upload
- Ensure accessibility and responsiveness

## 7. Example API Response
```json
{
  "id": 9,
  "username": "tarunbawari",
  "profile_image": "http://localhost:8000/media/profiles/abc.jpg",
  "badge": "Copper",
  "bio": "Android developer & reader",
  "followers_count": 120,
  "following_count": 80,
  "posts_count": 34
}
```

## 8. Contact & Contribution
- For backend/API questions, contact the Django team
- For UI/UX suggestions, contact the Android team

---

## 9. Available Jetpack Compose Components & UI/UX Best Practices

### Components & Placement
- **ProfileHeader**: Top of screen. Shows profile image, username, badge.
- **ProfileStats**: Below header. Shows followers, following, posts count.
- **ProfileBio**: Below stats. Shows user bio/description.
- **ProfileActions**: Next to header or as a floating action button. Edit profile, upload/change image.
- **ProfileTabs**: Below bio/stats. Tabs for Posts, Followers, Following. Sticky at top when scrolling.
- **PostList**: In Posts tab. Shows user’s posts in a scrollable list.
- **FollowersList / FollowingList**: In respective tabs. Shows followers/following users.
- **Loading/Error/Empty States**: Overlay or main content area. Shows progress bar, error message, or “No data” message.

### UI/UX Best Practices
- Use Material Design components (Card, Button, TabRow, etc.)
- Layout adapts to all screen sizes (responsive)
- Add content descriptions, readable font sizes, and color contrast (accessibility)
- Animate tab switching, image upload, and profile edits (smooth transitions)
- Show clear error messages for failed API calls or invalid input
- Use progress indicators while fetching data (loading states)
- Use dialog or separate screen for editing profile info (edit flow)
- Use image picker, show preview, and upload progress (image upload)
- Show friendly message and illustration for empty states
- Match app colors, typography, and iconography (consistent theming)

### Example Component Layout

```
| ProfileHeader      |
| ProfileStats       |
| ProfileBio         |
| ProfileActions     |
|--------------------|
| ProfileTabs        |
|--------------------|
| Tab Content        |
| (Posts/Followers/  |
|  Following List)   |
```

---

**Keep this README updated as backend or UI changes!**
