# SentinelCode Frontend

React + TypeScript + Vite frontend for the SentinelCode multi-agent code reviewer.

## Features

- **Dashboard**: View review statistics and recent reviews
- **New Review**: Submit code diffs for analysis (paste or upload)
- **Review Results**: View detailed findings with filtering and search
- **History**: Browse all past reviews
- **Mock Mode**: Demo mode with simulated data for testing

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router v7
- **State Management**: TanStack Query (React Query)
- **Icons**: Lucide React
- **Fonts**: Inter (sans-serif) + JetBrains Mono (monospace)

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build

```bash
npm run build
```

### Lint

```bash
npm run lint
```

### Test

```bash
npm test
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Use mock API for demo (default: false)
VITE_USE_MOCK=true

# Backend API URL (only used when VITE_USE_MOCK=false)
VITE_API_BASE_URL=http://localhost:8000
```

## API Contract

The frontend communicates with the backend via REST API. All requests include an `X-Client-Token` header (UUID) generated on first visit.

### Endpoints

#### POST /api/reviews
Create a new code review.

**Request:**
```typescript
{
  diff_text: string;        // Unified diff (max 40,000 chars)
  file_paths?: string[];    // Optional list of file paths
  source?: string;          // Optional source identifier
}
```

**Response:**
```typescript
{
  id: string;               // Review ID
  status: 'queued' | 'running' | 'done' | 'failed';
}
```

#### GET /api/reviews
List all reviews (summary).

**Response:**
```typescript
{
  id: string;
  status: ReviewStatus;
  verdict?: 'APPROVE' | 'REQUEST_CHANGES';
  finding_counts: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  created_at: string;       // ISO 8601 timestamp
  duration_s?: number;
}[]
```

#### GET /api/reviews/:id
Get detailed review by ID.

**Response:**
```typescript
{
  id: string;
  status: ReviewStatus;
  verdict?: Verdict;
  duration_s?: number;
  error?: string;           // Only when status === 'failed'
  report_md?: string;      // Markdown report
  diff_text: string;        // Original diff
  agents: {
    agent: string;          // Agent name
    status: 'idle' | 'running' | 'done' | 'skipped';
    duration_s: number;
    finding_count: number;
  }[];
  findings: {
    id: string;
    title: string;
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
    confidence: 'HIGH' | 'MEDIUM' | 'LOW';
    cwe: string;            // CWE identifier
    file: string;
    line: number;
    evidence: string;
    fix: string;
    sources: string[];      // Agent names that found this
    status: 'kept' | 'rejected';
    rejection_reason?: string;
  }[];
  created_at: string;
  finished_at?: string;
}
```

#### DELETE /api/reviews/:id
Delete a review by ID.

**Response:** 204 No Content

#### GET /api/samples
Get available sample diffs for testing.

**Response:**
```typescript
{
  id: string;
  name: string;
  description: string;
  diff_text: string;
  file_paths?: string[];
}[]
```

#### GET /api/stats
Get user statistics.

**Response:**
```typescript
{
  total_reviews: number;
  finding_counts: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  verdict_split: {
    approve: number;
    request_changes: number;
  };
  avg_review_time_s: number;
}
```

## Mock Mode

When `VITE_USE_MOCK=true`, the frontend uses a mock API client that:

- Simulates async review lifecycle (queued → running → done)
- Includes one failed review and one with rejected findings
- Shows a "Demo data" badge on review pages
- Does not require a running backend

## Type Definitions

All API types are defined in `src/api/types.ts`:

```typescript
type ReviewStatus = 'queued' | 'running' | 'done' | 'failed';
type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
type Confidence = 'HIGH' | 'MEDIUM' | 'LOW';
type Verdict = 'APPROVE' | 'REQUEST_CHANGES';
type FindingStatus = 'kept' | 'rejected';
```

## Components

### Core Components

- **Badge**: Severity and confidence badges with variants
- **Card**: Reusable card component
- **Tabs**: Tab navigation
- **NavBar**: Navigation bar for /app pages
- **ErrorBoundary**: Error boundary for error handling
- **Toast**: Toast notifications
- **Skeleton**: Loading skeleton

### Pages

- **Landing**: Landing page with pipeline diagram
- **Dashboard**: KPIs and recent reviews
- **NewReview**: Submit new code review
- **ReviewResult**: Detailed review with tabs
- **History**: Review history table
- **NotFound**: 404 page

## Design System

### Colors

- Page: `#0D1117`
- Panel: `#161B22`
- Border: `#21262D`
- Text: `#E6EDF3`
- Secondary: `#8B949E`
- Brand (accent): `#8B5CF6` (violet)
- Critical: `#F85149`
- High: `#FF8C42`
- Medium: `#E3B341`
- Low: `#58A6FF`
- Safe: `#3FB950`

### Typography

- Sans-serif: Inter (400, 500, 600, 700)
- Monospace: JetBrains Mono (400, 500)

### Spacing

- Border radius: 8px
- Default padding: 1rem (16px)

## Testing

Tests are written with Vitest and Testing Library:

- `src/utils/diffValidation.test.ts` - Diff validation logic
- `src/components/Badge.test.tsx` - Badge component
- `src/hooks/usePolling.test.ts` - Polling hook logic
- `src/utils/filterLogic.test.ts` - Filter logic

Run tests:
```bash
npm test
```

## Linting

ESLint with TypeScript and React rules:

```bash
npm run lint
```

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
