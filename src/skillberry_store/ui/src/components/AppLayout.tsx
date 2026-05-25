// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useEffect } from 'react';
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
  Button,
  Divider,
} from '@patternfly/react-core';
import { BarsIcon, CodeIcon } from '@patternfly/react-icons';

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  // Start with sidebar closed on smaller screens
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 1200;
    }
    return true;
  });
  const navigate = useNavigate();
  const location = useLocation();

  // Handle responsive sidebar behavior
  useEffect(() => {
    const handleResize = () => {
      // Auto-close sidebar on smaller screens
      if (window.innerWidth < 1200 && isSidebarOpen) {
        setIsSidebarOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isSidebarOpen]);

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
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#151515' }}>
            <CodeIcon style={{ color: '#0066CC', fontSize: '1.5rem', flexShrink: 0 }} />
            <span style={{ fontSize: '1.25rem', fontWeight: 600, whiteSpace: 'nowrap' }}>
              Skillberry Store
            </span>
          </div>
        </MastheadBrand>
      </MastheadMain>
      <MastheadContent>
        {/* Add user menu or other header content here */}
      </MastheadContent>
    </Masthead>
  );

  const sidebar = (
    <PageSidebar>
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

            {/* Virtual NFS Servers */}
            <NavItem
              key="vnfs-servers"
              itemId="vnfs-servers"
              isActive={location.pathname === '/vnfs-servers' ||
                       location.pathname.startsWith('/vnfs-servers')}
              onClick={() => navigate('/vnfs-servers')}
            >
              Virtual NFS Servers
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
    <Page
      header={masthead}
      sidebar={isSidebarOpen ? sidebar : undefined}
    >
      <PageSection>{children}</PageSection>
    </Page>
  );
}