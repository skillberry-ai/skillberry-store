# Skillberry Store UI - Setup Guide

This guide will help you set up and run the Skillberry Store UI.

## Prerequisites

- Node.js 18+ and npm
- Skillberry Store backend running on port 8000

## Installation Steps

### 1. Navigate to the UI directory

```bash
cd ui
```

### 2. Install dependencies

```bash
npm install
```

This will install all required packages including:
- React 18
- TypeScript
- Vite
- PatternFly (IBM's design system)
- TanStack Query (for data fetching)
- React Router (for navigation)

### 3. Start the development server

```bash
npm run dev
```

The UI will be available at [http://localhost:3000](http://localhost:3000)

## Available Scripts

- `npm run dev` - Start development server on port 3000
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run typecheck` - Run TypeScript type checking

## Project Structure

```
ui/
├── src/
│   ├── components/          # Reusable UI components
│   │   └── AppLayout.tsx    # Main layout with navigation
│   ├── pages/               # Page components
│   │   ├── HomePage.tsx
│   │   ├── ToolsPage.tsx
│   │   ├── ToolDetailPage.tsx
│   │   ├── SkillsPage.tsx
│   │   ├── SkillDetailPage.tsx
│   │   ├── SnippetsPage.tsx
│   │   ├── SnippetDetailPage.tsx
│   │   ├── VMCPServersPage.tsx
│   │   ├── VMCPServerDetailPage.tsx
│   │   └── NotFoundPage.tsx
│   ├── services/            # API service layer
│   │   └── api.ts           # API client functions
│   ├── types/               # TypeScript type definitions
│   │   └── index.ts
│   ├── styles/              # Global styles
│   │   └── global.css
│   ├── App.tsx              # Main app component with routing
│   ├── main.tsx             # Application entry point
│   └── vite-env.d.ts        # Vite type definitions
├── public/                  # Static assets
├── index.html               # HTML template
├── package.json             # Dependencies and scripts
├── tsconfig.json            # TypeScript configuration
├── vite.config.ts           # Vite configuration
└── README.md                # Project documentation
```

## API Integration

The UI communicates with the Skillberry Store backend through a proxy configuration:

- **UI**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **Proxy**: All `/api/*` requests are proxied to the backend

The proxy is configured in `vite.config.ts`:

```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  },
}
```

## Features

### Tools Management
- List all tools with search functionality
- View tool details including source code
- Create new tools with file upload
- Execute tools with parameters
- Delete tools

### Skills Management
- List all skills with search functionality
- View skill details
- Create, update, and delete skills
- Organize tools and snippets into skills

### Snippets Management
- List all snippets with search functionality
- View snippet content with syntax highlighting
- Create, update, and delete snippets

### VMCP Servers Management
- List all virtual MCP servers
- View server details and associated tools
- Create and delete VMCP servers
- Monitor server status

## Technology Stack

- **React 18**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool and dev server
- **PatternFly**: IBM's design system for consistent UI
- **TanStack Query**: Data fetching, caching, and state management
- **React Router**: Client-side routing
- **React Markdown**: Markdown rendering

## Development Tips

### Hot Module Replacement (HMR)
Vite provides fast HMR, so changes to your code will be reflected immediately in the browser without a full page reload.

### Type Checking
Run `npm run typecheck` to check for TypeScript errors without building.

### Linting
Run `npm run lint` to check for code quality issues.

### API Service Layer
All API calls are centralized in `src/services/api.ts`. This makes it easy to:
- Update API endpoints
- Add error handling
- Implement request/response interceptors
- Mock API calls for testing

### State Management
TanStack Query handles all server state management:
- Automatic caching
- Background refetching
- Optimistic updates
- Request deduplication

## Troubleshooting

### Port 3000 already in use
If port 3000 is already in use, you can change it in `vite.config.ts`:

```typescript
server: {
  port: 3001, // Change to any available port
  // ...
}
```

### Backend connection issues
Ensure the Skillberry Store backend is running on port 8000. You can verify by visiting:
```
http://localhost:8000/docs
```

### TypeScript errors
The TypeScript errors you see before running `npm install` are expected. They will be resolved once all dependencies are installed.

## Next Steps

After setup, you can:

1. **Customize the UI**: Modify components in `src/components/` and `src/pages/`
2. **Add new features**: Create new pages and add routes in `src/App.tsx`
3. **Extend the API**: Add new API functions in `src/services/api.ts`
4. **Style customization**: Modify `src/styles/global.css` or add component-specific styles

## Support

For issues or questions:
- Check the main project README at the root level
- Review the Skillberry Store backend documentation
- Consult PatternFly documentation: https://www.patternfly.org/