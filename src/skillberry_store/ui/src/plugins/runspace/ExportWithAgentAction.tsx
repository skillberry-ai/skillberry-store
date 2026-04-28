// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState } from 'react';
import { Button } from '@patternfly/react-core';
import { AutomationIcon } from '@patternfly/react-icons';
import { AgenticExportModal } from './AgenticExportModal';

interface Ctx {
  skill?: { name?: string };
}

/**
 * Slot contribution for `skill.detail.actions`. Renders the "Export with Runspace Agent"
 * button on the skill detail page and owns the modal's open/close state.
 */
export function ExportWithAgentAction({ skill }: Ctx) {
  const [isOpen, setIsOpen] = useState(false);
  const skillName = skill?.name || '';

  return (
    <>
      <Button
        variant="secondary"
        icon={<AutomationIcon />}
        onClick={() => setIsOpen(true)}
        isDisabled={!skillName}
      >
        Export with Runspace Agent
      </Button>
      <AgenticExportModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        skillName={skillName}
      />
    </>
  );
}
