// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useNavigate } from 'react-router-dom';
import {
  PageSection,
  EmptyState,
  EmptyStateIcon,
  Title,
  EmptyStateBody,
  Button,
} from '@patternfly/react-core';
import { ExclamationTriangleIcon } from '@patternfly/react-icons';

export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <PageSection>
      <EmptyState>
        <EmptyStateIcon icon={ExclamationTriangleIcon} color="var(--pf-v5-global--warning-color--100)" />
        <Title headingLevel="h1" size="lg">
          404 - Page Not Found
        </Title>
        <EmptyStateBody>
          The page you are looking for does not exist.
        </EmptyStateBody>
        <Button variant="primary" onClick={() => navigate('/')}>
          Go to Home
        </Button>
      </EmptyState>
    </PageSection>
  );
}