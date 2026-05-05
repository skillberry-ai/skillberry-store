// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Page,
  Masthead,
  MastheadToggle,
  MastheadMain,
  MastheadBrand,
  MastheadContent,
  PageSidebar,
  PageSidebarBody,
  Nav,
  NavList,
  NavItem,
  PageSection,
  Brand,
  Button,
  Divider,
} from '@patternfly/react-core';
import { BarsIcon } from '@patternfly/react-icons';

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { id: 'home', label: 'Home', path: '/' },
    { id: 'skills', label: 'Skills', path: '/skills' },
    { id: 'tools', label: 'Tools', path: '/tools' },
    { id: 'snippets', label: 'Snippets', path: '/snippets' },
    { id: 'vmcp-servers', label: 'Virtual MCP Servers', path: '/vmcp-servers' },
  ];

  const masthead = (
    <Masthead>
      <MastheadToggle>
        <Button
          variant="plain"
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          aria-label="Toggle navigation"
        >
          <BarsIcon />
        </Button>
      </MastheadToggle>
      <MastheadMain>
        <MastheadBrand onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          <Brand
            src="/vite.svg"
            alt="Skillberry Store"
            heights={{ default: '36px' }}
          >
            <span style={{ marginLeft: '1rem', fontSize: '1.25rem', fontWeight: 600 }}>
              Skillberry Store
            </span>
          </Brand>
        </MastheadBrand>
      </MastheadMain>
      <MastheadContent>
        {/* Add user menu or other header content here */}
      </MastheadContent>
    </Masthead>
  );

  const sidebar = (
    <PageSidebar isSidebarOpen={isSidebarOpen}>
      <PageSidebarBody>
        <Nav>
          <NavList>
            {/* Home */}
            <NavItem
              key="home"
              itemId="home"
              isActive={location.pathname === '/'}
              onClick={() => navigate('/')}
            >
              Home
            </NavItem>
            
            <Divider style={{ margin: '0.5rem 0' }} />
            
            {/* Skills, Tools, Snippets */}
            {navItems.slice(1, 4).map((item) => (
              <NavItem
                key={item.id}
                itemId={item.id}
                isActive={location.pathname === item.path ||
                         (item.path !== '/' && location.pathname.startsWith(item.path))}
                onClick={() => navigate(item.path)}
              >
                {item.label}
              </NavItem>
            ))}
            
            <Divider style={{ margin: '0.5rem 0' }} />
            
            {/* Virtual MCP Servers */}
            <NavItem
              key="vmcp-servers"
              itemId="vmcp-servers"
              isActive={location.pathname === '/vmcp-servers' ||
                       location.pathname.startsWith('/vmcp-servers')}
              onClick={() => navigate('/vmcp-servers')}
            >
              Virtual MCP Servers
            </NavItem>

            <Divider style={{ margin: '0.5rem 0' }} />

            {/* Observability */}
            <NavItem
              key="observability"
              itemId="observability"
              isActive={location.pathname === '/observability'}
              onClick={() => navigate('/observability')}
            >
              Observability
            </NavItem>

            {/* Connect Your Agent */}
            <NavItem
              key="agent-connect"
              itemId="agent-connect"
              isActive={location.pathname === '/agent-connect'}
              onClick={() => navigate('/agent-connect')}
            >
              Connect Your Agent
            </NavItem>

            {/* Admin */}
            <NavItem
              key="admin"
              itemId="admin"
              isActive={location.pathname === '/admin'}
              onClick={() => navigate('/admin')}
            >
              Admin
            </NavItem>
          </NavList>
        </Nav>
      </PageSidebarBody>
    </PageSidebar>
  );

  return (
    <Page masthead={masthead} sidebar={sidebar}>
      <PageSection>{children}</PageSection>
    </Page>
  );
}