# Skillberry Store UI

A React-based user interface for the Skillberry Store service, built with TypeScript, Vite, and PatternFly.

**Note**: This UI is automatically started when you run the Skillberry Store backend. You typically don't need to run it separately unless you're developing the UI.

## Features

- **Skills Management**: View, create, update, delete, and search skills
- **Tools Management**: View, create, update, delete, execute, and search tools
- **Snippets Management**: View, create, update, delete, and search snippets
- **VMCP Servers**: View, create, delete, and manage virtual MCP servers
- **Modern UI**: Built with PatternFly (IBM's design system)
- **Type-Safe**: Full TypeScript support
- **Fast Development**: Powered by Vite

## Prerequisites

- Node.js 18+ and npm (automatically checked when starting the backend)
- Skillberry Store backend running on port 8000 (starts automatically)

## Getting Started

### Automatic Start (Recommended)

The UI starts automatically when you run the Skillberry Store:

```bash
# From the project root
make run
```

The UI will be available at [http://localhost:3000](http://localhost:3000)

### Manual Development (For UI Development Only)

If you want to work on the UI separately:

```bash
# From this directory (src/skillberry_store/ui)
npm install
npm run dev
```

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
ui/
├── src/
│   ├── components/     # Reusable UI components
│   ├── pages/          # Page components
│   ├── services/       # API service layer
│   ├── types/          # TypeScript type definitions
│   ├── hooks/          # Custom React hooks
│   ├── styles/         # Global styles
│   ├── App.tsx         # Main app component
│   └── main.tsx        # Application entry point
├── public/             # Static assets
└── index.html          # HTML template
```

## API Integration

The UI proxies API requests to the Skillberry Store backend:
- UI runs on: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Proxy configuration in `vite.config.ts`

## Technology Stack

- **React 18**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool and dev server
- **PatternFly**: IBM's design system
- **TanStack Query**: Data fetching and caching
- **React Router**: Client-side routing
- **React Markdown**: Markdown rendering

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run typecheck` - Run TypeScript type checking