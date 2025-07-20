---

# **Community Tab Jetpack Compose Roadmap – Real Project Flow**

Absolutely, **aapki workflow ko real production jaisa modular bana ke** hum ek ek feature top se implement karenge, full Compose architecture ke hisaab se. **Ye roadmap ek ek block banata hai, jisse aap daily ya weekly sprint me implement kar sakte ho**.

## **Step-by-Step Plan (Top → Bottom, UI Flow order)**

---

### **1. Create Post Input (Top Bar)**

* **What’s on your mind?** multi-line text field
* **Image picker** (gallery/camera)
* **Hashtag adder with suggestions** (type `#` → dropdown)
* **Poll Button** (opens poll modal)
* **Word limit, live counter**
* **Send/Post button** (active/inactive state, error on empty post)
* **UX:** Keyboard behavior, emoji support, error/empty states

**Target:**
Users can create a text post, upload image, add hashtags, or start a poll—directly from top bar.

---

### **2. Poll Creation Modal**

* **Bottom sheet/modal with fields:**
  * Poll question
  * Minimum 2 options (dynamic add up to 6)
  * Validation: 2–6 options, empty check, duplicate option check
  * **Create & Cancel button**
* **UI:** Clear focus, instant error feedback, show remaining option slots

---

### **3. Feed/List of Posts**

* **LazyColumn** with paginated loading
* **Each post:**
  * User profile (image, badge, tap for profile)
  * Username + badge
  * Post timestamp
  * Post text (spans/links for hashtags)
  * Hashtags as tappable chips
  * Image (or fallback)
  * **If poll:** Poll card (radio, show result, vote)
  * **If shared:** Share count/chip
  * Actions row: Like, Comment, Share, Copy Link
  * Post menu (⋮) if owner: Edit, Delete, Toggle comments, Copy link

---

### **4. Poll Display & Voting (In Feed)**

* **Poll card:**
  * Question at top
  * Options as radio (pre/post vote)
  * Result bars after vote (progress %, color), total vote count
  * “You have voted” indicator, allow changing vote if API allows

---

### **5. Like/Unlike (In Feed)**

* **Heart icon:**
  * Filled/unfilled, animation, count, local update + backend sync
* **Instant state:** Optimistic UI; revert on error

---

### **6. Comments System**

* **Feed post has ‘View Comments (N)’**
* **Modal/sheet with:**
  * List of comments (user img, username, badge, text, timestamp)
  * Add comment input
  * Delete (if comment owner)
* **State:** Loading, error, no comments

---

### **7. Share & Copy Link**

* **ShareSheet** for WhatsApp/others
* **Copy Link** button: Clipboard + Toast, count update

---

### **8. Post Owner Menu**

* **Long-press or ⋮ icon:**
  * Edit post (modal)
  * Delete (confirm dialog)
  * Toggle commenting (on/off badge)
  * Copy link

---

### **9. Infinite Scroll/Pagination**

* **Load next page** at end of list (scroll listener)
* **Show shimmer/spinner** at bottom
* **API integration:** Use next URL from backend, avoid dupe loads

---

### **10. UI Polish/Production States**

* **Image fallback**
* **Empty state illustrations/messages**
* **Loading shimmer (not just spinner)**
* **Snackbar for errors**
* **Touch targets, accessibility**
* **Badge styles, dark/light mode, bilingual (if needed)**

---

## **Recommended Implementation Order**

1. **Create Post Input Bar (with hashtag suggestions)**
2. **Poll Creation Modal**
3. **Feed/Post List with paginated loading**
4. **Poll Card in Feed (display + voting)**
5. **Like/Unlike**
6. **Comments (Add/View/Delete)**
7. **Share/Copy**
8. **Post Owner Menu**
9. **Infinite Scroll**
10. **UI/UX Polish**

---

## **Professional Way to Implement Each Block**

* **Har block ka**:
  * Jetpack Compose UI
  * ViewModel/State
  * Repository/API integration
  * Error handling, UX fallback
  * Kaha paste karna, clearly bataunga
* **Modular banaenge**:
  * Reusable composables (e.g., PollCard, CommentList, HashtagChip)
  * State hoist karein, side effects handle karein (using `collectAsState()`, `remember` etc.)
  * Har endpoint ka testable, isolated implementation

---

## **Aap Start Kis Block Se Karwana Chahte Ho?**

*(e.g., “Pehle input bar complete karo including poll and hashtag UI”, ya “Poll Card ready karo”, ya “Like/Unlike integrate karo”, ya “Comments system banao”)*

---

### **Sample Start:**

**Step 1. Create Post Input Bar with Hashtag Suggestions (UI+VM, No Poll Yet)
Step 2. Poll Modal**
...and so on.

---

### **BOLD STEP:**

*Just reply karo* — “**Step 1: Input Bar + Hashtag UI se shuru karo, uska Jetpack Compose+ViewModel code do**”
**ya**
“Step 2: Poll Modal implement karo”

---

**Jis bhi block ka code aapko chahiye, main sirf real, modular, production-level Jetpack Compose code dunga with integration instructions.**

---

*(You can copy this whole plan into your project Wiki or Notion also as a blueprint.)*
# Community Tab UI & API Integration Guide

This README is for Android developers building the Community Tab using Jetpack Compose, powered by the Django backend in `communityDesk`.

---

## 1. Overview
The Community Tab displays a feed of posts, allows users to create posts (with images and hashtags), comment, like, share, vote in polls, follow users, and search content. All data is served by the Django backend (`communityDesk`).

## 2. Key API Endpoints
- **List Posts:** `GET /api/community/posts/`
- **Create Post:** `POST /api/community/posts/`
- **Get Post Detail:** `GET /api/community/posts/{id}/`
- **Comment on Post:** `POST /api/community/posts/{post_pk}/comments/`
- **Like Post:** `POST /api/community/posts/{post_pk}/likes/`
- **Share Post:** `POST /api/community/posts/{id}/share/`
- **Copy Link:** `GET /api/community/posts/{id}/copy-link/`
- **Polls & Votes:** `GET/POST /api/community/posts/{post_pk}/polls/`, `POST /api/community/polls/{poll_pk}/votes/`
- **Follow/Unfollow:** `POST /api/community/users/{user_pk}/follow/`
- **Search:** `GET /api/community/search/?q=...`
- **Get User Posts:** `GET /api/community/users/{user_id}/posts/`

## 3. Data Models
- **Post:** id, user, text, image_url, hashtags, commenting_enabled, like_count, comment_count, share_count, poll, created_at
- **Comment:** id, post, user, text, created_at
- **Poll:** id, post, question, options, votes, created_at
- **Vote:** id, poll, user, option_id, created_at
- **Follow/Like:** id, user, post/following, created_at

## 4. UI Structure (Jetpack Compose)
- **SearchBar**: Top of screen, for searching posts/users
- **PostList**: LazyColumn for feed
- **PostCard**: Shows user, image, text, hashtags, like/comment/share buttons
- **CreatePostBox**: Inline at top of feed, similar to Facebook. Shows user's avatar, text input, image upload, hashtags input, and a 'Post' button. Also allows adding a poll (question and options) during post creation.
- **PostDetailScreen**: Shows full post, comments, poll, actions
- **CommentList**: For comments under a post
- **PollView**: For polls attached to posts
- **UserProfilePreview**: For showing user info
- **ActionButtons**: Like, comment, share, follow
- **Loading/Error/EmptyState**: For feedback

## 5. API Integration Steps
1. **Fetch posts** for feed on tab load
2. **Display PostCard** for each post
3. **Create post**: use inline CreatePostBox at top of feed, send post request. If user adds a poll, include poll question and options in the request.
4. **Like, comment, share, follow**: send respective requests
5. **Show post detail**: fetch post, comments, poll
6. **Vote in poll**: send vote request
7. **Search**: send search request, show results
8. **Handle loading, error, empty states**

## 6. UI/UX Notes
- Use Material Design components
- Responsive layouts for all screen sizes
- Accessibility: content descriptions, readable fonts, color contrast
- Smooth transitions for post creation, voting, liking
- Clear error/loading/empty states
- Easy navigation between feed, post detail, user profiles
- In CreatePostBox, provide an option to add a poll: show input for poll question and multiple options. Validate that at least two options are provided.

## 7. Example Post API Response
```json
{
  "id": 28,
  "user": {
    "id": 9,
    "username": "tarunbawari",
    "profile_image": "http://localhost:8000/media/profiles/abc.jpg",
    "badge": "Copper"
  },
  "text": "checking 1",
  "image_url": "http://localhost:8000/media/posts/images_7y7JVvC.jpeg",
  "hashtags": ["#tarun", "#bhawin"],
  "commenting_enabled": false,
  "like_count": 0,
  "comment_count": 0,
  "is_liked": false,
  "share_count": 0,
  "poll": {
    "id": 5,
    "question": "Which is your favorite color?",
    "options": {"1": "Red", "2": "Blue", "3": "Green"},
    "votes": {"1": 10, "2": 5, "3": 2},
    "created_at": "2025-07-20T21:06:11.900292+05:30"
  },
  "created_at": "2025-07-20T21:06:11.900292+05:30",
  "updated_at": "2025-07-20T21:06:11.900333+05:30"
}
```

## 8. Component Placement Example
```
| SearchBar           |
|---------------------|
| CreatePostBox       | <-- Inline, Facebook-style
|---------------------|
| PostList            |
|---------------------|
| PostCard            |
|  - User info        |
|  - Image            |
|  - Text/hashtags    |
|  - Like/Comment/Share|
|---------------------|
| PostDetailScreen    |
|  - Full post        |
|  - Comments         |
|  - Poll (if any)    |
|---------------------|
```

## 9. Contact & Contribution
- For backend/API questions, contact the Django team
- For UI/UX suggestions, contact the Android team

---

**Keep this README updated as backend or UI changes!**
