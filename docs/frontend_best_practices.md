# React Frontend Best Practices

> A practical guide for building maintainable, scalable React applications.

---

## 1. Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ui/              # Basic elements (Button, Input, Card)
│   └── features/        # Feature-specific (CoffeeCard, ReviewForm)
├── pages/               # Route-level components
├── hooks/               # Custom hooks (useAuth, useCoffee)
├── services/            # API calls
├── stores/              # State management (Zustand)
├── types/               # TypeScript interfaces
├── utils/               # Helper functions
└── styles/              # Global styles, themes
```

### File Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `CoffeeCard.tsx` |
| Hooks | camelCase with `use` prefix | `useCoffee.ts` |
| Utils | camelCase | `formatPrice.ts` |
| Types | PascalCase | `Coffee.types.ts` |
| Styles | kebab-case or module | `coffee-card.module.css` |

---

## 2. Component Best Practices

### 2.1 Keep Components Small and Focused

```tsx
// ❌ Bad - does too much
const CoffeePage = () => {
  // 300 lines of mixed logic, UI, API calls...
}

// ✅ Good - single responsibility
const CoffeePage = () => (
  <PageLayout>
    <CoffeeHeader />
    <CoffeeDetails />
    <CoffeeReviews />
  </PageLayout>
)
```

### 2.2 Separate Logic from UI

```tsx
// ✅ Custom hook for logic
const useCoffeeRating = (coffeeId: string) => {
  const [rating, setRating] = useState(0);
  const submit = () => api.submitRating(coffeeId, rating);
  return { rating, setRating, submit };
};

// ✅ Clean component
const RatingForm = ({ coffeeId }) => {
  const { rating, setRating, submit } = useCoffeeRating(coffeeId);
  return <StarPicker value={rating} onChange={setRating} onSubmit={submit} />;
};
```

### 2.3 Use TypeScript Interfaces for Props

```tsx
interface CoffeeCardProps {
  id: string;
  name: string;
  roastery: string;
  rating: number;
  price: number;
  onPress?: () => void;
}

const CoffeeCard = ({ 
  name, 
  roastery, 
  rating, 
  price, 
  onPress 
}: CoffeeCardProps) => {
  // Component implementation
};
```

### 2.4 Component Organization

```tsx
// Recommended order within a component file:

// 1. Imports
import { useState, useCallback } from 'react';
import { useCoffee } from '@/hooks/useCoffee';

// 2. Types/Interfaces
interface Props {
  coffeeId: string;
}

// 3. Component
export const CoffeeDetails = ({ coffeeId }: Props) => {
  // 3a. Hooks
  const { data, isLoading } = useCoffee(coffeeId);
  const [isExpanded, setIsExpanded] = useState(false);

  // 3b. Derived state
  const formattedPrice = formatPrice(data?.price);

  // 3c. Callbacks
  const handleToggle = useCallback(() => {
    setIsExpanded(prev => !prev);
  }, []);

  // 3d. Effects (if needed)
  useEffect(() => {
    // ...
  }, []);

  // 3e. Early returns (loading, error)
  if (isLoading) return <Skeleton />;

  // 3f. Render
  return (
    <div>
      {/* JSX */}
    </div>
  );
};
```

---

## 3. State Management

### 3.1 Choosing the Right State Type

| State Type | Solution | Use Case |
|------------|----------|----------|
| Local UI | `useState` | Form inputs, toggles, modals |
| Server data | React Query | API data, caching |
| Global client | Zustand | Auth, user preferences |
| URL state | React Router | Filters, pagination |

### 3.2 Local State with useState

```tsx
// Simple local state
const [isOpen, setIsOpen] = useState(false);

// Complex local state - use useReducer
const [state, dispatch] = useReducer(reducer, initialState);
```

### 3.3 Server State with React Query

```tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Fetching data
const useCoffee = (id: string) => {
  return useQuery({
    queryKey: ['coffee', id],
    queryFn: () => api.coffee.getById(id),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Mutating data
const useCreateReview = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: CreateReviewDTO) => api.reviews.create(data),
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
    },
  });
};

// Usage in component
const CoffeeDetails = ({ id }: { id: string }) => {
  const { data, isLoading, error } = useCoffee(id);
  const createReview = useCreateReview();

  if (isLoading) return <Loading />;
  if (error) return <Error message={error.message} />;

  return (
    <div>
      <h1>{data.name}</h1>
      <ReviewForm onSubmit={createReview.mutate} />
    </div>
  );
};
```

### 3.4 Global State with Zustand

```tsx
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  user: User | null;
  token: string | null;
  login: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      login: (user, token) => set({ user, token }),
      logout: () => set({ user: null, token: null }),
    }),
    {
      name: 'auth-storage',
    }
  )
);

// Usage
const Header = () => {
  const { user, logout } = useAuthStore();
  
  return (
    <header>
      {user ? (
        <>
          <span>{user.name}</span>
          <button onClick={logout}>Logout</button>
        </>
      ) : (
        <LoginButton />
      )}
    </header>
  );
};
```

---

## 4. API Layer

### 4.1 Centralized API Service

```tsx
// services/api.ts
const BASE_URL = import.meta.env.VITE_API_URL;

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const token = useAuthStore.getState().token;
  
  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new ApiError(response.status, await response.json());
  }

  return response.json();
}

export const api = {
  coffee: {
    getAll: (filters?: CoffeeFilters) => 
      fetchWithAuth(`/beans?${new URLSearchParams(filters as any)}`),
    getById: (id: string) => 
      fetchWithAuth(`/beans/${id}`),
    create: (data: CreateCoffeeDTO) =>
      fetchWithAuth('/beans', { 
        method: 'POST', 
        body: JSON.stringify(data) 
      }),
  },
  
  reviews: {
    getByCoffee: (coffeeId: string) =>
      fetchWithAuth(`/beans/${coffeeId}/reviews`),
    create: (data: CreateReviewDTO) =>
      fetchWithAuth('/reviews', { 
        method: 'POST', 
        body: JSON.stringify(data) 
      }),
  },
  
  groups: {
    getAll: () => fetchWithAuth('/groups'),
    getById: (id: string) => fetchWithAuth(`/groups/${id}`),
    join: (code: string) => 
      fetchWithAuth('/groups/join', { 
        method: 'POST', 
        body: JSON.stringify({ code }) 
      }),
  },
};
```

### 4.2 Custom Hooks for API Calls

```tsx
// hooks/useCoffees.ts
export const useCoffees = (filters?: CoffeeFilters) => {
  return useQuery({
    queryKey: ['coffees', filters],
    queryFn: () => api.coffee.getAll(filters),
  });
};

export const useCoffee = (id: string) => {
  return useQuery({
    queryKey: ['coffee', id],
    queryFn: () => api.coffee.getById(id),
    enabled: !!id,
  });
};

export const useCreateCoffee = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: api.coffee.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['coffees'] });
    },
  });
};
```

---

## 5. TypeScript Types

### 5.1 Define Clear Interfaces

```tsx
// types/coffee.ts
export interface Coffee {
  id: string;
  name: string;
  roastery: Roastery;
  origin: string;
  process: ProcessMethod;
  roastLevel: RoastLevel;
  rating: number;
  reviewCount: number;
  packages: Package[];
  createdAt: string;
}

export interface Package {
  id: string;
  weight: number; // grams
  price: number;  // cents
}

export type ProcessMethod = 'washed' | 'natural' | 'honey';
export type RoastLevel = 'light' | 'medium' | 'dark';

// DTOs for API
export interface CreateCoffeeDTO {
  name: string;
  roasteryId: string;
  origin: string;
  process: ProcessMethod;
  roastLevel: RoastLevel;
}

export interface CoffeeFilters {
  roasteryId?: string;
  origin?: string;
  process?: ProcessMethod;
  roastLevel?: RoastLevel;
  minRating?: number;
}
```

### 5.2 Utility Types

```tsx
// types/utils.ts

// API response wrapper
export interface ApiResponse<T> {
  data: T;
  meta?: {
    total: number;
    page: number;
    limit: number;
  };
}

// Make all properties optional recursively
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

// Extract props from component
export type PropsOf<T> = T extends React.ComponentType<infer P> ? P : never;
```

---

## 6. Performance Optimization

### 6.1 Memoization

```tsx
// useMemo - for expensive calculations
const sortedCoffees = useMemo(() => {
  return [...coffees].sort((a, b) => b.rating - a.rating);
}, [coffees]);

// useCallback - for callbacks passed to children
const handleSelect = useCallback((id: string) => {
  setSelectedId(id);
}, []);

// React.memo - for pure components
const CoffeeCard = memo(({ coffee, onSelect }: Props) => {
  return (
    <div onClick={() => onSelect(coffee.id)}>
      {coffee.name}
    </div>
  );
});
```

### 6.2 Code Splitting & Lazy Loading

```tsx
import { lazy, Suspense } from 'react';

// Lazy load pages
const CoffeePage = lazy(() => import('./pages/CoffeePage'));
const GroupsPage = lazy(() => import('./pages/GroupsPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));

// Router with suspense
const App = () => (
  <Suspense fallback={<LoadingScreen />}>
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/coffee/:id" element={<CoffeePage />} />
      <Route path="/groups" element={<GroupsPage />} />
      <Route path="/profile" element={<ProfilePage />} />
    </Routes>
  </Suspense>
);
```

### 6.3 Image Optimization

```tsx
// Lazy loading images
<img 
  src={coffee.imageUrl} 
  alt={coffee.name}
  loading="lazy"
  width={200}
  height={200}
/>

// Responsive images
<picture>
  <source 
    media="(max-width: 768px)" 
    srcSet={coffee.imageMobile} 
  />
  <img 
    src={coffee.imageDesktop} 
    alt={coffee.name} 
  />
</picture>
```

### 6.4 List Virtualization

```tsx
import { useVirtualizer } from '@tanstack/react-virtual';

const CoffeeList = ({ coffees }: { coffees: Coffee[] }) => {
  const parentRef = useRef<HTMLDivElement>(null);
  
  const virtualizer = useVirtualizer({
    count: coffees.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 100,
  });

  return (
    <div ref={parentRef} style={{ height: '100vh', overflow: 'auto' }}>
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: virtualItem.start,
              height: virtualItem.size,
            }}
          >
            <CoffeeCard coffee={coffees[virtualItem.index]} />
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## 7. Forms

### 7.1 React Hook Form

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

// Validation schema
const reviewSchema = z.object({
  rating: z.number().min(1).max(5),
  aroma: z.number().min(1).max(5).optional(),
  flavor: z.number().min(1).max(5).optional(),
  comment: z.string().max(1000).optional(),
  brewMethod: z.enum(['espresso', 'filter', 'french-press', 'aeropress']),
});

type ReviewFormData = z.infer<typeof reviewSchema>;

// Form component
const ReviewForm = ({ coffeeId, onSuccess }: Props) => {
  const createReview = useCreateReview();
  
  const { 
    register, 
    handleSubmit, 
    formState: { errors, isSubmitting } 
  } = useForm<ReviewFormData>({
    resolver: zodResolver(reviewSchema),
    defaultValues: {
      rating: 0,
      brewMethod: 'filter',
    },
  });

  const onSubmit = async (data: ReviewFormData) => {
    await createReview.mutateAsync({ ...data, coffeeId });
    onSuccess?.();
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div>
        <label>Rating</label>
        <StarPicker {...register('rating', { valueAsNumber: true })} />
        {errors.rating && <span>{errors.rating.message}</span>}
      </div>

      <div>
        <label>Brew Method</label>
        <select {...register('brewMethod')}>
          <option value="espresso">Espresso</option>
          <option value="filter">Filter</option>
          <option value="french-press">French Press</option>
          <option value="aeropress">AeroPress</option>
        </select>
      </div>

      <div>
        <label>Comment</label>
        <textarea {...register('comment')} />
        {errors.comment && <span>{errors.comment.message}</span>}
      </div>

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Submitting...' : 'Submit Review'}
      </button>
    </form>
  );
};
```

---

## 8. Error Handling

### 8.1 Error Boundary

```tsx
import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught:', error, errorInfo);
    // Send to error tracking service (Sentry, etc.)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || <ErrorFallback error={this.state.error} />;
    }
    return this.props.children;
  }
}

// Usage
const App = () => (
  <ErrorBoundary fallback={<ErrorPage />}>
    <Router>
      <Routes />
    </Router>
  </ErrorBoundary>
);
```

### 8.2 API Error Handling

```tsx
// Custom error class
export class ApiError extends Error {
  constructor(
    public status: number,
    public data: any
  ) {
    super(data.message || 'An error occurred');
    this.name = 'ApiError';
  }
}

// Error display component
const ErrorMessage = ({ error }: { error: Error }) => {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 401:
        return <p>Please log in to continue.</p>;
      case 403:
        return <p>You don't have permission to access this.</p>;
      case 404:
        return <p>The requested item was not found.</p>;
      default:
        return <p>{error.message}</p>;
    }
  }
  return <p>Something went wrong. Please try again.</p>;
};
```

---

## 9. Testing

### 9.1 Testing Strategy

| Type | Tool | What to Test |
|------|------|--------------|
| Unit | Vitest | Utils, hooks, pure functions |
| Component | Testing Library | User interactions, rendering |
| Integration | Testing Library | Feature flows |
| E2E | Playwright | Critical user journeys |

### 9.2 Component Testing

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CoffeeCard } from './CoffeeCard';

const mockCoffee = {
  id: '1',
  name: 'Ethiopia Yirgacheffe',
  roastery: 'Doubleshot',
  rating: 4.5,
  price: 389,
};

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
};

describe('CoffeeCard', () => {
  it('renders coffee information', () => {
    renderWithProviders(<CoffeeCard coffee={mockCoffee} />);
    
    expect(screen.getByText('Ethiopia Yirgacheffe')).toBeInTheDocument();
    expect(screen.getByText('Doubleshot')).toBeInTheDocument();
    expect(screen.getByText('389 Kč')).toBeInTheDocument();
  });

  it('calls onPress when clicked', () => {
    const onPress = vi.fn();
    renderWithProviders(<CoffeeCard coffee={mockCoffee} onPress={onPress} />);
    
    fireEvent.click(screen.getByRole('button'));
    expect(onPress).toHaveBeenCalledWith('1');
  });
});
```

### 9.3 Hook Testing

```tsx
import { renderHook, waitFor } from '@testing-library/react';
import { useCoffee } from './useCoffee';

describe('useCoffee', () => {
  it('fetches coffee data', async () => {
    const { result } = renderHook(() => useCoffee('1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data.name).toBe('Ethiopia Yirgacheffe');
  });
});
```

---

## 10. Accessibility (a11y)

### 10.1 Semantic HTML

```tsx
// ❌ Bad
<div onClick={handleClick}>Click me</div>

// ✅ Good
<button onClick={handleClick}>Click me</button>

// ❌ Bad
<div className="card">...</div>

// ✅ Good
<article className="card">...</article>
```

### 10.2 ARIA Attributes

```tsx
// Loading state
<button disabled={isLoading} aria-busy={isLoading}>
  {isLoading ? 'Loading...' : 'Submit'}
</button>

// Modal
<div 
  role="dialog" 
  aria-modal="true" 
  aria-labelledby="modal-title"
>
  <h2 id="modal-title">Add Review</h2>
  ...
</div>

// Form errors
<input 
  aria-invalid={!!error} 
  aria-describedby={error ? 'email-error' : undefined}
/>
{error && <span id="email-error" role="alert">{error}</span>}
```

### 10.3 Keyboard Navigation

```tsx
const Modal = ({ isOpen, onClose, children }) => {
  // Close on Escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);

  // Focus trap
  const modalRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (isOpen) {
      modalRef.current?.focus();
    }
  }, [isOpen]);

  return isOpen ? (
    <div ref={modalRef} tabIndex={-1} role="dialog">
      {children}
    </div>
  ) : null;
};
```

---

## 11. Security

### 11.1 XSS Prevention

```tsx
// ❌ Dangerous - never use with user input
<div dangerouslySetInnerHTML={{ __html: userContent }} />

// ✅ Safe - React escapes by default
<div>{userContent}</div>

// If you must render HTML, sanitize it
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(content) }} />
```

### 11.2 Sensitive Data

```tsx
// Never store sensitive data in localStorage
// ❌ Bad
localStorage.setItem('password', password);

// Use httpOnly cookies for tokens when possible
// Or store in memory (Zustand without persist for sensitive data)
```

---

## 12. Key Principles Summary

1. **Composition over complexity** – Build with small, reusable components
2. **Colocation** – Keep related code together (component + hook + styles)
3. **Single source of truth** – Clear ownership of each piece of state
4. **Type everything** – TypeScript prevents bugs and documents code
5. **Fail gracefully** – Always handle loading, error, and empty states
6. **Optimize last** – Don't prematurely optimize; measure first
7. **Test behavior, not implementation** – Focus on what users see and do
8. **Accessible by default** – Use semantic HTML and keyboard navigation

---

## Quick Reference: Recommended Stack

| Category | Tool |
|----------|------|
| Framework | React 18+ |
| Language | TypeScript |
| Build | Vite |
| Routing | React Router v6 |
| Server State | TanStack Query (React Query) |
| Client State | Zustand |
| Forms | React Hook Form + Zod |
| Styling | Tailwind CSS |
| Testing | Vitest + Testing Library |
| E2E | Playwright |
| Linting | ESLint + Prettier |