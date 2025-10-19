# Crooked Finger iOS - Project Context

## Project Overview
Native iOS port of the Crooked Finger web application - a crochet pattern assistant with AI-powered pattern translation, diagram generation, and project management.

**Parent Web App**: `/Users/chandlerhardy/repos/crooked-finger`

## Tech Stack
- **Platform**: iOS 17+ (SwiftUI)
- **Language**: Swift 6
- **Architecture**: MVVM + SwiftUI
- **Backend**: Shared GraphQL API (FastAPI + Strawberry)
- **AI**: Multi-provider system (Google Gemini + OpenRouter) via backend
- **Networking**: Apollo GraphQL Client (Swift)
- **Local Storage**: SwiftData / Core Data
- **Image Handling**: Kingfisher for caching

## Backend Integration
**Shared Backend URL**: `https://backend.chandlerhardy.com/crooked-finger/graphql`

### GraphQL Endpoints:
- **Production**: `https://backend.chandlerhardy.com/crooked-finger/graphql`
- **Local Dev**: `http://localhost:8001/crooked-finger/graphql`

### Key Backend Features:
1. **Pattern Translation** - Convert crochet notation to instructions
2. **AI Chat** - Multi-provider AI assistant with automatic fallback:
   - **Primary (Testing)**: OpenRouter Qwen3-30B-A3B (free, unlimited)
   - **Fallback**: Google Gemini (Pro, Flash Preview, Flash, Flash-Lite with daily quotas)
3. **Diagram Generation** - matplotlib-based crochet charts (PNG/SVG)
4. **YouTube Transcripts** - Extract patterns from video tutorials via RapidAPI (100 requests/month free)
5. **Pattern Library** - Save, browse, manage patterns
6. **Project Management** - Track projects with images and notes

## Core iOS Features (Phase 1)
1. ✅ **Home Screen** - Dashboard with recent projects and conversations
2. ✅ **AI Chat Interface** - Chat with Gemini assistant about crochet patterns
3. ✅ **Pattern Library** - Browse, search, save patterns
4. ✅ **Project Management** - Create and track crochet projects
5. ✅ **Image Viewer** - View pattern diagrams and project photos
6. ✅ **Settings** - User preferences and app configuration

## Backend Infrastructure
**Shared Backend with Web App** - Oracle Cloud Infrastructure (OCI)

### Server Details
- **IP**: `150.136.38.166`
- **SSH**: `ssh ubuntu@150.136.38.166 -i /Users/chandlerhardy/.ssh/ampere.key`
- **Location**: `/home/ubuntu/crooked-finger/`
- **Port**: 8001 (backend), 5433 (PostgreSQL external)

### Production URLs
- **GraphQL API**: https://backend.chandlerhardy.com/crooked-finger/graphql
- **Health Check**: https://backend.chandlerhardy.com/crooked-finger/health
- **Web App**: https://crookedfinger.chandlerhardy.com

### Docker Setup
**Production**: `docker-compose.backend.yml`
- PostgreSQL 15 (port 5433 external, 5432 internal)
- FastAPI backend (port 8001)
- Nginx reverse proxy with Let's Encrypt SSL

**Development**: `docker-compose.dev.yml`
- Local PostgreSQL (port 5434)
- For testing without OCI server

### Key Files
- `backend/Dockerfile` - Python 3.11 with FastAPI + Strawberry GraphQL
- `backend/requirements.txt` - Python dependencies (includes httpx for OpenRouter)
- `backend/.env` - Environment variables (API keys, CORS_ORIGINS) - **NOT committed to git**
- `docker-compose.backend.yml` - Uses `env_file: ./backend/.env` for secure key loading

### AI Provider Configuration
**Current Setup (Oct 7, 2025):**
- `use_openrouter_default = True` in `ai_service.py` - routes all requests to OpenRouter Qwen3
- Three API keys configured in `backend/.env`:
  - `GEMINI_API_KEY` - Google Gemini (fallback, daily quotas)
  - `OPENROUTER_API_KEY` - OpenRouter (primary, unlimited free tier)
  - `RAPIDAPI_KEY` - YouTube Transcript3 service (100 requests/month)

**Environment Variable Management:**
- ✅ `docker-compose.backend.yml` uses `env_file: ./backend/.env` directive
- ✅ All API keys loaded from `backend/.env` (secure, not in git)
- ✅ Production deployment copies `backend/.env` to server via deploy script
- ✅ Override production values with `environment:` section (DATABASE_URL, ENVIRONMENT, DEBUG)
- ⚠️ Backend uses `case_sensitive = False` in config.py for env var loading

**Adding New AI Providers:**
1. Add API key to `backend/app/core/config.py` (e.g., `anthropic_api_key: Optional[str] = None`)
2. Add key to `backend/.env` locally and on production server
3. Implement `_translate_with_<provider>()` and `_chat_with_<provider>()` methods in `ai_service.py`
4. Add provider to fallback logic or set as default via flag (e.g., `use_anthropic_default = True`)
5. Redeploy backend with `./deploy-backend-to-oci.sh 150.136.38.166`

**Provider Priority System:**
- Set `use_<provider>_default = True` to make it primary
- When primary fails/unavailable, fallback chain activates:
  - OpenRouter Qwen3 → Gemini Pro → Gemini Flash Preview → Gemini Flash → Gemini Flash-Lite
- Easy to test new providers without removing existing ones

## Project Structure
```
Crooked Finger iOS/
├── App/
│   └── Crooked_Finger_iOSApp.swift          # App entry point
├── Views/
│   ├── Home/
│   │   └── HomeView.swift                    # Dashboard
│   ├── Chat/
│   │   ├── ChatView.swift                    # AI chat interface
│   │   └── MessageRowView.swift              # Chat message cells
│   ├── Patterns/
│   │   ├── PatternLibraryView.swift          # Pattern browsing
│   │   ├── PatternDetailView.swift           # Pattern detail page
│   │   └── PatternCardView.swift             # Pattern grid item
│   ├── Projects/
│   │   ├── ProjectsView.swift                # Projects list
│   │   ├── ProjectDetailView.swift           # Project detail page
│   │   └── ProjectCardView.swift             # Project grid item
│   ├── Settings/
│   │   └── SettingsView.swift                # App settings
│   └── Components/
│       ├── Navigation/
│       │   └── TabNavigationView.swift       # Main tab navigation
│       └── Shared/
│           ├── ImageViewerView.swift         # Zoom/pan image viewer
│           └── LoadingView.swift             # Loading states
├── ViewModels/
│   ├── ChatViewModel.swift                   # Chat logic
│   ├── PatternViewModel.swift                # Pattern management
│   ├── ProjectViewModel.swift                # Project management
│   └── AIUsageViewModel.swift                # AI usage tracking
├── Models/
│   ├── Pattern.swift                         # Pattern data model
│   ├── Project.swift                         # Project data model
│   ├── ChatMessage.swift                     # Chat message model
│   └── Conversation.swift                    # Chat conversation model
├── Services/
│   ├── GraphQL/
│   │   ├── ApolloClient.swift                # GraphQL client setup
│   │   ├── Queries.graphql                   # GraphQL queries
│   │   └── Mutations.graphql                 # GraphQL mutations
│   ├── AIService.swift                       # AI assistant integration
│   ├── PatternService.swift                  # Pattern management
│   └── StorageService.swift                  # Local data persistence
├── Utilities/
│   ├── Extensions/
│   │   ├── String+Extensions.swift           # String helpers
│   │   └── View+Extensions.swift             # SwiftUI view helpers
│   └── Constants.swift                       # App constants
└── Assets.xcassets/                          # Images, colors, icons

Crooked Finger iOSTests/
└── Unit tests

Crooked Finger iOSUITests/
└── UI tests
```

## Development Guidelines
- **SwiftUI First**: Use SwiftUI for all UI components
- **MVVM Pattern**: ViewModels manage business logic, Views are declarative
- **Async/Await**: Use modern Swift concurrency for network calls
- **Type Safety**: Leverage Swift's strong typing system
- **Error Handling**: Graceful error states with user-friendly messages
- **iOS HIG**: Follow Apple's Human Interface Guidelines
- **Accessibility**: Support VoiceOver and Dynamic Type

## Key Differences from Web App
1. **Navigation**: Tab bar instead of sidebar navigation
2. **Storage**: SwiftData/Core Data for local persistence (vs localStorage)
3. **Images**: Kingfisher for caching (vs Next.js Image)
4. **State Management**: SwiftUI @State/@Observable (vs React hooks)
5. **Routing**: NavigationStack (vs Next.js routing)

## Implementation Status

### ✅ Phase 1 (MVP) - COMPLETED (Sep 15 - Oct 1, 2025):
1. ✅ Project structure setup
2. ✅ GraphQL client integration (lightweight URLSession-based)
3. ✅ Basic navigation (TabView with 5 tabs)
4. ✅ Home screen with mock data
5. ✅ Chat interface with FULL backend integration
6. ✅ Pattern library (list view with mock data)
7. ✅ Project list view (with mock data)
8. ✅ Swift packages added (Apollo iOS, Kingfisher)

**Key Achievement**: Established foundational architecture with SwiftUI, MVVM, and GraphQL backend integration.

### ✅ Phase 2 (UI Polish & Theme) - COMPLETED (Sep 28 - Oct 2, 2025):
1. ✅ ChatViewModel with backend integration
2. ✅ Pattern detail pages (UI complete, mock data)
3. ✅ Project detail pages (UI complete, mock data)
4. ✅ Settings screen (basic UI)
5. ✅ **Custom theme matching web app** (warm browns, cream backgrounds)
6. ✅ **Dark mode support** (adaptive colors)
7. ✅ **Empty state views** for patterns and projects
8. ✅ **Pull-to-refresh** on list views
9. ✅ **Loading states** and animations
10. ✅ **Haptic feedback** on interactions
11. ✅ **Markdown rendering** in chat messages
12. ✅ **Card-style list items** with borders and shadows
13. ✅ **Message animations** with fade-in effects

**Key Achievement**: Elevated app from functional MVP to polished, production-ready user experience with custom design system.

### ✅ Phase 3 (Backend Integration Complete) - COMPLETED (Oct 1 - Oct 4, 2025):
1. ✅ PatternViewModel with full backend integration
2. ✅ ProjectViewModel with full backend integration
3. ✅ GraphQL CRUD operations (create, read, update, delete)
4. ✅ Pattern vs Project filtering (notes field logic)
5. ✅ **User Authentication System**
   - ✅ Login/Signup UI with SwiftUI forms (LoginView, RegisterView)
   - ✅ JWT token management with UserDefaults
   - ✅ AuthViewModel with login/register/logout
   - ✅ Protected app navigation (LoginView ↔ TabNavigationView)
   - ✅ Settings screen with logout functionality
6. ✅ **Backend Authentication Fixed** (Oct 4, 2025)
   - ✅ Migrated from bcrypt to Argon2 password hashing
   - ✅ Fixed GraphQL context_getter db session handling
   - ✅ Removed FastAPI Request.user setter issue
   - ✅ Deployed to production with working auth
7. ✅ Error handling and retry logic
8. ✅ Optimistic UI updates
9. ✅ **Image Upload & Management** (Oct 4, 2025)
   - ✅ ImageService with base64 encoding/decoding and compression (1920px @ 80%)
   - ✅ Base64ImageView component with async loading and fullscreen viewer
   - ✅ ImagePicker with camera and photo library support (max 10 images)
   - ✅ Projects: Full image upload/view/delete functionality
   - ✅ Patterns: Image upload/view/delete (previously read-only)
   - ✅ Chat: ChatGPT-style "+" button with image attachments (max 5 images)
   - ✅ Nginx configured for 10MB upload limit
10. ✅ **Performance Optimizations** (Oct 5, 2025)
   - ✅ ChatViewModel lazy initialization with async loading
   - ✅ UserDefaults I/O moved to background threads (Task.detached)
   - ✅ Removed blocking UserDefaults.synchronize() calls
   - ✅ Pre-computed markdown rendering (AttributedString cached)
   - ✅ Tab-based lazy view loading (views only created when visited)
   - ✅ Static timestamp formatting (removed expensive .relative style)
   - ✅ Reduced animation durations and removed shadows
   - ✅ Claude-style chat UI (full-width assistant messages, bubbled user messages)
   - ✅ Immediate input clearing and keyboard dismissal on send
11. ✅ **App Icon & UX Enhancements** (Oct 5, 2025)
   - ✅ Added official Crooked Finger Crochet app icon (1024x1024)
   - ✅ Project-specific chat conversations (separate chat per project)
   - ✅ Editable pattern text in ProjectDetailView (Pattern tab with Edit/Save/Cancel)
   - ✅ Editable notes in ProjectDetailView (Notes tab with auto-save)
   - ✅ Editable pattern notation/instructions in PatternDetailView
   - ✅ Tap-to-dismiss keyboard (ZStack overlay pattern, like ChatView)
12. ✅ **YouTube Transcript Feature via RapidAPI** (Oct 6, 2025)
   - Backend migrated from youtube-transcript-api to RapidAPI YouTube Transcript3 service
   - Works from production backend (no IP blocking issues)
   - Free tier: 100 requests/month
   - iOS YouTubeTranscriptView with full UI (fetch, extract, preview, save)
   - GraphQL mutation `fetchYoutubeTranscript` fully functional
   - Thumbnail download and base64 conversion for pattern images
   - Automatic INSTRUCTIONS section parsing (splits notation from plain-text instructions)
   - **Backend Schema Update** (Oct 6, 2025 - PENDING DEPLOYMENT):
     - Added `translated_text` field to `CreateProjectInput` (types.py)
     - Updated `create_project` mutation to accept instructions on create (mutations.py)
     - Eliminates need for separate update request when saving patterns with instructions
     - More performant: 1 request instead of 2
13. ✅ **Multimodal AI Image Support** (Oct 8, 2025)
   - Backend: Added `image_data` parameter to `chatWithAssistantEnhanced` GraphQL mutation
   - Backend: Implemented proper Gemini SDK image handling with `types.Part.from_bytes()`
   - Backend: Enhanced system prompts for pattern extraction with explicit format instructions
   - iOS: MediaPickerView with camera/photo library/browse files (including PDF support)
   - iOS: PDF to image conversion using PDFKit (security-scoped resource handling for device compatibility)
   - iOS: Pattern creation AI assistant can analyze images and auto-populate pattern fields
   - iOS: Chat images displayed with tap-to-enlarge fullscreen viewer
   - iOS: Optimized Base64ImageViewer with separate ZoomableImageView for smooth zoom/pan
14. ✅ **Image Persistence & Management** (Oct 8, 2025)
   - Fixed critical bug: Pattern/project image uploads now combine existing + new images
   - MediaPickerView added to existing pattern/project detail views (not just creation)
   - Multiple PDFs can be added to same pattern/project
   - PDFs and photos can be mixed in any order and persist correctly
   - Pattern images from AI assistant automatically saved to pattern gallery
   - Comprehensive debug logging for image pipeline troubleshooting
15. ⏳ AI Usage dashboard integration (pending)
16. ⏳ Local data persistence with SwiftData (pending)

**Key Achievement**: Complete multimodal AI integration with image analysis, PDF support, and robust image persistence across patterns, projects, and chat. Pattern creation AI assistant can extract patterns from images and auto-populate all fields.

### 🔄 Phase 4 (Advanced Features & Polish) - IN PROGRESS (Oct 5 - Oct 20, 2025):
1. ✅ **Image Upload & Management** - COMPLETED
   - ✅ Camera integration for project photos
   - ✅ Base64 encoding for GraphQL upload
   - ✅ Photo library picker with multi-select
   - ✅ Image compression and optimization
   - ✅ ChatGPT-style image attachments in chat
   - ✅ Fullscreen image viewer with zoom/pan gestures
2. 🔐 **Enhanced Security**
   - Biometric authentication (Face ID/Touch ID)
   - JWT token refresh mechanism
   - Keychain storage for sensitive data
3. 📊 **AI Usage Dashboard**
   - Display token usage by model
   - Cost tracking and estimates
   - Usage history and analytics
4. 🎨 **Enhanced Features**
   - Pattern sharing (Share sheet, PDF export, QR codes)
   - Enhanced chat (model selection, voice input)
   - Professional diagram viewer with zoom/pan
   - Project templates and progress tracking

### Phase 5 (Offline-First Architecture) - BACKLOG (Oct 21 - Nov 10, 2025):
1. SwiftData as single source of truth
2. Intelligent sync engine with conflict resolution
3. Background sync with BGTaskScheduler
4. Network resilience and offline mode
5. Data management (caching, export/import)

**Key Goal**: Transform app into offline-first architecture for seamless usage regardless of connectivity.

### Phase 6 (Native iOS Platform Features) - BACKLOG (Nov 11 - Dec 5, 2025):
1. **Widgets**: Stitch counter, active project, AI chat widgets
2. **Siri Shortcuts**: Voice commands for common actions
3. **Apple Watch**: Companion app with stitch counter and complications
4. **Live Activities**: Dynamic Island integration for project progress
5. **iPad Features**: Split View, Slide Over, Apple Pencil support
6. **Spotlight**: Index patterns/projects for system-wide search

**Key Goal**: Deep iOS platform integration for premium native experience.

### Phase 7 (Final Polish & App Store Launch) - BACKLOG (Dec 6, 2025 - Jan 15, 2026):
1. Performance optimization (launch time, memory, battery)
2. Accessibility compliance (VoiceOver, Dynamic Type, WCAG)
3. Comprehensive testing (unit, UI, integration, device testing)
4. Bug fixes and stability (<0.1% crash rate target)
5. App Store preparation (screenshots, icons, descriptions)
6. TestFlight beta testing (50-100 users)
7. Analytics and monitoring setup
8. App Store submission and launch

**Key Goal**: Production-ready app with App Store approval and public release.

## Known Issues & Debugging Notes

### PatternDetailView Layout Bug (Oct 8, 2025) - ACTIVE INVESTIGATION

**Issue**: When adding images to an existing pattern, the Instructions section sometimes renders directly under the pattern title instead of in its proper location below Notation.

**Symptoms**:
- Happens when new images are added via MediaPickerView
- Instructions text appears in the wrong position (under title, above difficulty/materials)
- Layout corrupts in real-time as images are added to carousel
- Workaround: Restart app and layout is correct

**What We've Tried** (all unsuccessful):
1. ✗ `.id(patternImages.count)` on TabView - still corrupts
2. ✗ `.id("pattern-\(pattern.id)-images-\(patternImages.count)")` on VStack - still corrupts
3. ✗ `@State private var viewKey = UUID()` + update on image change - still corrupts
4. ✗ Temporary clear/reset pattern images array with delay - still corrupts
5. ✗ Removed GeometryReader from TabView - still corrupts
6. ✗ Separated TabView and content into different VStacks - still corrupts

**Current Theory**:
- TabView asynchronous image loading may be racing with VStack layout calculation
- SwiftUI may be caching incorrect layout after first render
- The conditional `if !patternImages.isEmpty` may be causing view identity confusion

**File**: `PatternDetailView.swift:49-254`

**Next Steps to Try**:
1. Pre-load all images before showing TabView (convert all base64 to UIImage eagerly)
2. Replace nested VStacks with LazyVStack
3. Add explicit frame heights to each section
4. Use List instead of ScrollView + VStack
5. Completely separate views for "has images" vs "no images" states

**Relevant Console Logs**:
```
🖼️ Uploading 1 new images to pattern
🖼️ Current pattern has 1 existing images
🖼️ Total images after combining: 2
📸 Image compressed: 4828KB → 654KB (ratio: 13.5%)
✅ Pattern updated with 2 total images
```
(Images are saving correctly - bug is purely visual/layout)

## Environment Configuration
**IMPORTANT: Temporary Backend Configuration (Oct 5, 2025)**
```swift
enum APIConfig {
    static let graphqlURL = "https://backend.chandlerhardy.com/crooked-finger/graphql"
    static let localGraphqlURL = "http://localhost:8001/crooked-finger/graphql"

    #if DEBUG
    // TODO: Revert to production backend once YouTube IP block clears (24-48 hours)
    // YouTube is currently blocking production backend IP (150.136.38.166) from transcript requests
    static let currentGraphqlURL = localGraphqlURL  // TEMPORARY: Using local backend
    #else
    static let currentGraphqlURL = graphqlURL
    #endif
}
```

## Dependencies (Swift Package Manager)
- **Apollo iOS** - GraphQL client
- **Kingfisher** - Image caching
- **SwiftUI Introspect** (optional) - UIKit interop

## Testing Strategy
- **Unit Tests**: ViewModels, Services, Models
- **UI Tests**: Critical user flows (chat, pattern save, project creation)
- **Manual Testing**: Device testing on iPhone/iPad

## GraphQL Client Implementation Notes
**Custom URLSession-based client (no Apollo codegen)**

### Pattern vs Project Filtering
Both use the same backend `CrochetProject` table, differentiated by `notes` field:
- **Patterns**: `notes == null` (reusable templates)
- **Projects**: `notes != null` (active work with user notes)

### Important Implementation Details
```swift
// ✅ CORRECT: Use native Swift dictionaries for GraphQL variables
let variables: [String: Any] = [
    "input": [
        "title": title,
        "description": description
    ]
]

// ❌ INCORRECT: Don't use Codable structs - causes JSON encoding issues
```

### Authentication Status
✅ **FULLY ENABLED** - Authentication system complete (Oct 4, 2025)

**Current Implementation:**
- JWT token storage in UserDefaults (works, but Keychain recommended for production)
- Login/Register/Logout flow with AuthViewModel
- Protected navigation (LoginView ↔ TabNavigationView based on isAuthenticated)
- Authorization header automatically added to GraphQL requests
- Backend uses Argon2 password hashing (migrated from bcrypt)

**Test Accounts:**
- Test account available for development (see private Notion docs)

**Future Enhancements:**
1. Migrate token storage from UserDefaults to Keychain
2. Implement JWT token refresh mechanism
3. Add biometric authentication (Face ID/Touch ID)
4. Session timeout and auto-logout

## iOS-Specific Features
**Native capabilities beyond web app:**
- Pull-to-refresh gestures
- System color scheme (light/dark mode)
- Haptic feedback on interactions
- Native SwiftUI navigation patterns
- Future: Widgets, Siri Shortcuts, Apple Watch

## Development Workflow
### Local Development
```bash
# Start local PostgreSQL database
cd /Users/chandlerhardy/repos/crooked-finger
docker-compose -f docker-compose.dev.yml up -d

# Point iOS app to local backend
# Update GraphQLClient.swift baseURL to http://localhost:8001
```

### Testing with Production Backend
```bash
# iOS app uses production backend by default
# baseURL: https://backend.chandlerhardy.com/crooked-finger/graphql
```

### Common Issues
**GraphQL variable errors**: Use native Swift dictionaries, not Codable structs
**Image upload 413 errors**: Check nginx client_max_body_size (currently 10MB), verify compression settings
**Login errors**: Ensure backend is running and admin account has Argon2 hash

## Project Roadmap
See Notion Projects database for detailed phase breakdowns:
- Phase 1-3: ✅ Complete (MVP, UI Polish, Backend Integration + Auth)
- Phase 4: 🔄 In Progress (Image Upload ✅, Biometrics ⏳, AI Dashboard ⏳)
- Phase 5: ⏳ Backlog (Offline-first, Sync)
- Phase 6: ⏳ Backlog (Widgets, Watch, Siri)
- Phase 7: ⏳ Backlog (App Store Launch)

## 📝 Recent iOS Updates

### October 7, 2025 - UI Polish & Chat Improvements
1. **Backend-Synced Chat History** (`eb3a67a`)
   - Conversations and messages now load from PostgreSQL database
   - Added conversation_id filtering support
   - Implemented eager data loading for patterns and projects on startup
   - Chat messages display in chronological order

2. **Project Detail View Improvements** (`8d6cbab`)
   - Added notation/instructions toggle for pattern display
   - Reduced spacing between tab picker and content
   - Removed minHeight constraint causing large gaps
   - Optimized image gallery padding and alignment
   - Technical notation shown in monospace font
   - Plain English instructions shown in regular font

3. **App Branding** (`bdf8383`)
   - Added custom logo and launch screen
   - Professional app icon design
   - Polished first-launch experience

### October 13, 2025 - Web App AI Model Configuration & Cross-Platform Standardization
1. **Web App - AI Model Configuration Backend Sync**
   - Web `AIModelSelector` component now syncs with backend via GraphQL `setAiModel` mutation
   - Added model ID to backend name mapping (e.g., 'openrouter-qwen' → 'qwen/qwen3-30b-a3b:free')
   - Configuration syncs on component mount and on every change
   - Smart routing mode: passes `modelName: null` with priority order for complexity-based routing
   - Single model mode: passes specific model name with fallback chain
   - **Cross-Platform Impact**: iOS should eventually implement similar backend sync for consistency

2. **Web App - Fallback Order Reordering**
   - Added up/down arrow buttons to reorder fallback models
   - Users can customize which models to try first after primary fails
   - Visual hint: "Click arrows to reorder"
   - Buttons disabled at boundaries (first/last items)
   - **Cross-Platform Impact**: iOS could implement similar drag-to-reorder UI in Settings

3. **Web App - Smart Primary Model Management**
   - When primary model changes, it automatically moves to top of fallback order
   - Ensures primary model is always first in fallback chain
   - Default fallback order now includes Qwen as first item:
     `['openrouter-qwen', 'openrouter-deepseek', 'gemini-pro', 'gemini-flash-preview', 'gemini-flash', 'gemini-flash-lite']`
   - **Cross-Platform Impact**: iOS and web both use same 6-model system

4. **Web App - Multimodal Image Format Standardization**
   - Fixed: Web now sends images as JSON string (matching iOS implementation)
   - GraphQL mutation changed from `$imageData: [String!]` to `$imageData: String`
   - Web extracts base64 data from data URLs: `img.split(',')[1]`
   - Both platforms now send: `JSON.stringify(base64ImagesArray)`
   - **Cross-Platform Impact**: Standardized image upload format across web and iOS

5. **Web App - Apollo Client Direct Calls**
   - Replaced `useMutation` hook with direct `apolloClient.mutate()` calls
   - Fixed Next.js Turbopack module resolution issues
   - More reliable for configuration syncing
   - **iOS Note**: iOS already uses this pattern with custom URLSession-based GraphQL client

### Technical Details (Web App Changes):
**Files Modified:**
- `frontend/src/lib/graphql/mutations.ts` - Added SET_AI_MODEL mutation
- `frontend/src/components/AIModelSelector.tsx` - Backend sync + reordering UI
- `frontend/src/app/page.tsx` - Fixed image data format for multimodal AI

**Model ID Mappings (Frontend → Backend):**
```typescript
'openrouter-qwen' → 'qwen/qwen3-30b-a3b:free'
'openrouter-deepseek' → 'deepseek/deepseek-chat-v3.1:free'
'gemini-pro' → 'gemini-2.5-pro'
'gemini-flash-preview' → 'gemini-2.5-flash-preview-09-2025'
'gemini-flash' → 'gemini-2.5-flash'
'gemini-flash-lite' → 'gemini-2.5-flash-lite'
```

**What These Changes Fix:**
- ✅ AI model selection now properly respected on web (was only localStorage, not synced)
- ✅ No more duplicate model prefixes in responses (e.g., `[gemini-2.5-flash-preview-09-2025] [gemini-2.5-flash]`)
- ✅ Smart routing toggle works correctly (backend now knows when to use complexity-based routing)
- ✅ Multimodal image support now works on web (GraphQL type mismatch resolved)
- ✅ Web and iOS send identical image data format (cross-platform consistency)

### October 6, 2025 - YouTube & Content Management
1. **YouTube Transcript Integration** (`9faf812`)
   - Re-enabled YouTube pattern extraction using RapidAPI
   - Extract patterns directly from YouTube crochet tutorials
   - 100 free requests/month quota

2. **YouTube Pattern Enhancements** (`2fe4ce4`, `16f46d5`)
   - Added YouTube thumbnail display on pattern cards
   - Fixed pattern saving with both thumbnails and instructions
   - Improved home page card UI with thumbnail support
   - YouTube thumbnails now properly persist to backend

3. **Delete & Markdown Improvements** (`0c26fea`)
   - Added delete functionality for patterns and projects
   - Implemented markdown cleaning for better text display
   - Remove excessive newlines and formatting artifacts
   - Cleaner pattern/project descriptions

---
*Last Updated: October 13, 2025*
