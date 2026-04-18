# {{PROJECT_NAME}}

Electron desktop application (wrapping React/React Native or static web).

## Requirements

- Node.js 18+
- npm or yarn

## Quick Start

```bash
# Install dependencies
npm install

# Start development
npm start

# Build for current platform
npm run build

# Build for specific platform
npm run build:win
npm run build:mac
npm run build:linux
```

## Structure

- `main.js` - Electron main process
- `preload.js` - Preload script for secure context bridge
- `www/` - Web content (place your React build or static files here)
