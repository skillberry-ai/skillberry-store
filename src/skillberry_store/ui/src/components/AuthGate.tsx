// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0
//
// Route wrapper: in `standalone` mode, redirect anonymous requests to
// `/login`. In `disabled` mode this is a passthrough. See §10.4 of the
// design doc.

import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

interface AuthGateProps {
  children: React.ReactNode;
}

export function AuthGate({ children }: AuthGateProps) {
  const { mode, token } = useAuth();
  const location = useLocation();

  if (mode === 'standalone' && !token && location.pathname !== '/login') {
    return (
      <Navigate to="/login" replace state={{ from: location.pathname }} />
    );
  }

  return <>{children}</>;
}
