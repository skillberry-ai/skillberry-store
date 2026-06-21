import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PluginCard } from './PluginCard';
import type { Plugin } from '@/types';

const basePlugin: Plugin = {
  slug: 'demo',
  name: 'Demo Plugin',
  description: 'A demo',
  version: '1.0',
  plugin_type: 'creator' as Plugin['plugin_type'],
  enabled: true,
  admin_enabled: true,
  status: 'Ready',
  has_router: false,
  has_cli: false,
  has_ui: false,
};

describe('PluginCard toggle', () => {
  it('calls onToggleEnabled with the negated admin_enabled value', () => {
    const onToggle = vi.fn();
    render(<PluginCard plugin={basePlugin} onToggleEnabled={onToggle} />);
    fireEvent.click(screen.getByRole('checkbox'));
    expect(onToggle).toHaveBeenCalledWith(basePlugin, false);
  });

  it('dims the card when the plugin is admin-disabled', () => {
    const { container, rerender } = render(<PluginCard plugin={basePlugin} />);
    expect(container.querySelector('[data-disabled="true"]')).toBeNull();

    rerender(<PluginCard plugin={{ ...basePlugin, admin_enabled: false }} />);
    expect(container.querySelector('[data-disabled="true"]')).not.toBeNull();
  });

  it('keeps the toggle interactive while dimmed', () => {
    const onToggle = vi.fn();
    render(
      <PluginCard
        plugin={{ ...basePlugin, admin_enabled: false, enabled: false }}
        onToggleEnabled={onToggle}
      />
    );
    fireEvent.click(screen.getByRole('checkbox'));
    expect(onToggle).toHaveBeenCalledWith(
      expect.objectContaining({ slug: 'demo' }),
      true
    );
  });
});
