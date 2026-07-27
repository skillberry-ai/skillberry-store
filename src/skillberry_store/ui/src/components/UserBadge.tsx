// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0
//
// Small header widget: "Signed in as X · Sign out". Renders only when the
// caller is authenticated. See §10.4 of the design doc.

import { useNavigate } from 'react-router-dom';
import { Button, Flex, FlexItem } from '@patternfly/react-core';
import { useAuth } from '@/contexts/AuthContext';

export function UserBadge() {
  const { token, tenantId, signOut, mode } = useAuth();
  const navigate = useNavigate();

  if (mode === 'disabled' || !token) return null;

  const handleSignOut = async () => {
    await signOut();
    navigate('/login', { replace: true });
  };

  return (
    <Flex alignItems={{ default: 'alignItemsCenter' }}>
      <FlexItem>
        <span style={{ color: '#f0f0f0' }}>
          Signed in as <strong>{tenantId || 'user'}</strong>
        </span>
      </FlexItem>
      <FlexItem>
        <Button variant="link" onClick={handleSignOut}>
          Sign out
        </Button>
      </FlexItem>
    </Flex>
  );
}
