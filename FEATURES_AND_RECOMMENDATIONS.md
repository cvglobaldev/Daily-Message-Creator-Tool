# Current Features & System Documentation

## Current Features

### Core System Capabilities
1. **Multi-Platform Chatbot System** - WhatsApp and Telegram integration for reaching diverse audiences
2. **Multi-Bot Management** - Create and manage multiple independent bots with separate configurations
3. **Role-Based Access Control (RBAC)** - Admin vs Super Admin with different permission levels
4. **Automated Content Delivery** - Scheduler delivers daily content based on configurable intervals
5. **Content Management System (CMS)** - Full CRUD operations for multimedia content
6. **AI-Powered Analytics** - Comprehensive insights into user engagement and journey progression
7. **Chat Management & Monitoring** - View, filter, and export user conversations
8. **Tag Management System** - Dual-layer tagging (AI-powered + Rule-based)
9. **User Administration** - Manage admin users and permissions (super admin only)
10. **Voice Message Handling** - Transcription and synthesis with multi-language support
11. **Media Management** - Images, videos, audio files with upload and preview
12. **AI Content Generation** - Generate 10-90 day journeys with audience customization

### Admin Pages & Routes
1. **Dashboard** (`/dashboard`) - System overview, recent messages, human handoff requests, user stats
2. **Bot Management** (`/bots`) - Create, edit, delete bots with platform-specific configurations
3. **Content Management System** (`/cms`, `/bots/<id>/content`) - CRUD content with multimedia support, AI content generation
4. **Chat Management** (`/chat-management`, `/chat/<user_id>`) - View conversations, filter by tags/sentiment, export data
5. **Analytics Dashboard** (`/analytics`) - Journey insights, drop-off rates, faith tag distribution, completion metrics
6. **Tag Management** (`/tags`) - Super admin only: Create/edit AI and rule-based tags
7. **User Management** (`/user-management`) - Super admin only: Manage admin accounts and roles

### Role-Based Permissions

**Regular Admin:**
- Create and manage only their own bots
- View dashboard showing only their bots' data
- Access analytics filtered to only their bots
- NO access to tag management
- NO access to user management
- Cannot see or edit other admins' bots

**Super Admin:**
- Full access to ALL bots (own and others')
- View complete analytics for all bots
- Exclusive access to tag management (create, edit, delete tags)
- Exclusive access to user management (create, edit, delete admin users)
- Can change user roles and permissions
- Can delete user conversation history

### Technical Features

**AI & Intelligence:**
- Sentiment analysis using Google Gemini API
- Automated tag detection with confidence scoring
- Contextual AI responses aware of user's journey stage
- Human handoff detection for sensitive topics
- Content gap detection and handling

**Messaging & Communication:**
- WhatsApp Business API integration with webhook support
- Telegram Bot API integration with bot-specific routing
- Voice message transcription (Google Cloud Speech-to-Text)
- Voice synthesis for responses (Google Cloud Text-to-Speech)
- Multi-language support (English, Indonesian, Spanish, Hindi, etc.)

**Integration & Delivery:**
- Duplicate message prevention using atomic database locks
- Bot-specific service caching for performance
- Media file validation and upload system
- Webhook verification and security
- Background scheduler with configurable intervals

---

## Known Issues & Technical Debt

### Navigation Inconsistencies
1. **Analytics page** uses different navigation structure (only Dashboard + Analytics links visible)
2. **Analytics page** uses Feather icons while other pages use Font Awesome icons
3. **CMS page** missing Analytics and Users links in navigation bar
4. **Chat Management page** has minimal navigation (only Back to Dashboard + Content Management)
5. No consistent "Settings" or "Profile" link across all pages

### Missing Features & Access Issues
1. **Chat Management link** not consistently accessible from all admin pages
2. **CMS/Content Management** not linked from dashboard or bot management
3. No direct access to view bot-specific chats from dashboard
4. Export chat endpoint (`/api/chat-management/export`) missing bot ownership permission checks
5. No breadcrumb navigation when viewing bot-specific pages

### Design & UX Gaps
1. Analytics page doesn't match CVGlobal design theme used in other pages
2. Navigation not predictable across different sections
3. No visual indicator of which bot context user is currently in

---

## Recommendations for Necessary Changes

### HIGH PRIORITY: Standardize Navigation Across All Pages

**Goal:** Create consistent navigation experience across all admin pages

**Actions:**
1. Update Analytics page (`templates/analytics.html`) to use same navigation as Dashboard/Bot Management
2. Add full navigation bar to CMS page with all links (Dashboard, Bots, CMS, Chats, Analytics, Tags, Users)
3. Update Chat Management page with complete navigation
4. Standardize on Font Awesome icons (remove Feather icons from Analytics)
5. Add user dropdown with: Profile, Change Password, Logout

**Files to Modify:**
- `templates/analytics.html` - Replace navigation, update icons
- `templates/cms.html` - Add Analytics and Users links
- `templates/chat_management.html` - Add complete navigation bar
- `templates/tag_management.html` - Verify consistency

**Benefits:**
- Improved user experience with predictable navigation
- Faster navigation between sections
- Professional, cohesive interface

**Implementation Example:**
```html
<!-- Standard navigation template to use across all pages -->
<nav class="navbar navbar-dark bg-primary mb-4">
    <div class="container">
        <a class="navbar-brand" href="/">
            <img src="/static/favicon/cv-new-logo-favicon-32px.png" alt="CV Global Logo" class="me-2" style="width: 24px; height: 24px;">
            Daily Message Creator
        </a>
        <div class="navbar-nav flex-row">
            <a class="nav-link me-3" href="/dashboard">
                <i class="fas fa-tachometer-alt me-1"></i>Dashboard
            </a>
            <a class="nav-link me-3" href="/bots">
                <i class="fas fa-robot me-1"></i>Bots
            </a>
            <a class="nav-link me-3" href="/cms">
                <i class="fas fa-edit me-1"></i>Content
            </a>
            <a class="nav-link me-3" href="/chat-management">
                <i class="fas fa-comments me-1"></i>Chats
            </a>
            <a class="nav-link me-3" href="/analytics">
                <i class="fas fa-chart-line me-1"></i>Analytics
            </a>
            {% if current_user.is_authenticated and current_user.role == 'super_admin' %}
            <a class="nav-link me-3" href="/tags">
                <i class="fas fa-tags me-1"></i>Tags
            </a>
            <a class="nav-link me-3" href="/user-management">
                <i class="fas fa-users me-1"></i>Users
            </a>
            {% endif %}
            <div class="nav-item dropdown">
                <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                    <i class="fas fa-user me-1"></i>{{ current_user.full_name }}
                </a>
                <ul class="dropdown-menu dropdown-menu-end">
                    <li><a class="dropdown-item" href="/profile"><i class="fas fa-user-circle me-2"></i>Profile</a></li>
                    <li><a class="dropdown-item" href="/change-password"><i class="fas fa-key me-2"></i>Change Password</a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="/logout"><i class="fas fa-sign-out-alt me-2"></i>Logout</a></li>
                </ul>
            </div>
        </div>
    </div>
</nav>
```

---

### MEDIUM PRIORITY: Bot-Specific Navigation & Context

**Goal:** Show clear visual indication when working within a specific bot context

**Actions:**
1. Add breadcrumb navigation to bot-specific pages (CMS, chats, edit)
2. Display current bot name prominently in page header
3. Add quick bot switcher dropdown in navigation
4. Show bot status indicator (active/inactive) in bot context pages

**Files to Modify:**
- `templates/cms.html` - Add breadcrumb, bot context header
- `templates/full_chat.html` - Add breadcrumb, bot indicator
- `templates/edit_bot.html` - Add breadcrumb navigation
- `main.py` - Add bot context to template variables

**Benefits:**
- Users always know which bot they're managing
- Easy navigation back to bot management
- Quick switching between bots
- Reduced confusion and errors

---

### MEDIUM PRIORITY: Add Settings/Profile Section

**Goal:** Centralized user profile and settings management

**Actions:**
1. Create `/profile` route and template for user profile view/edit
2. Move password change to profile section (keep existing route for compatibility)
3. Add notification preferences for email alerts
4. Add session management (view active sessions, logout all)

**Files to Create:**
- `templates/profile.html` - User profile page
- Add routes in `main.py` for profile management

**Benefits:**
- Centralized account management
- Better security with session control
- Personalization options

---

### LOW PRIORITY: Access Control Improvements

**Goal:** Ensure all endpoints properly enforce bot ownership permissions

**Actions:**
1. Add creator_id filtering to `/api/chat-management/export` endpoint
2. Add ownership checks to all analytics sub-routes
3. Add audit logging for admin actions (delete bot, delete user data, role changes)
4. Implement API rate limiting for webhook endpoints

**Files to Modify:**
- `main.py` - Add permission checks to export and analytics routes
- `db_manager.py` - Add audit logging methods
- Add new `audit_log` table to models.py

**Benefits:**
- Improved security and data isolation
- Compliance with data privacy requirements
- Debugging and accountability

---

## Implementation Priority Summary

**Sprint 1 (Immediate):**
1. ✅ Standardize navigation across all pages
2. ✅ Fix Analytics page design and navigation
3. ✅ Add bot context indicators

**Sprint 2 (Short-term):**
1. ⏳ Implement profile/settings section
2. ⏳ Add breadcrumb navigation
3. ⏳ Create bot switcher component

**Sprint 3 (Medium-term):**
1. ⏳ Access control audit and fixes
2. ⏳ Add audit logging system
3. ⏳ Implement rate limiting

**Ongoing:**
- Monitor navigation consistency
- Gather user feedback on UX
- Refine permission system based on usage patterns
