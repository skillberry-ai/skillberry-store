import React from 'react';
import { useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { COLORS } from '../constants';

export const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 80, stiffness: 180 }, durationInFrames: 40 });
  const logoOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const titleOpacity = interpolate(frame, [20, 50], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const titleY = interpolate(frame, [20, 50], [30, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const subtitleOpacity = interpolate(frame, [45, 75], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const lineWidth = interpolate(frame, [60, 120], [0, 420], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const taglineOpacity = interpolate(frame, [80, 110], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <div style={{
      width: 1920, height: 1080,
      background: COLORS.bg,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: "'Red Hat Display', 'Segoe UI', system-ui, sans-serif",
    }}>
      {/* Logo mark */}
      <div style={{
        opacity: logoOpacity,
        transform: `scale(${interpolate(logoScale, [0, 1], [0.6, 1])})`,
        marginBottom: 32,
        display: 'flex',
        alignItems: 'center',
        gap: 18,
      }}>
        <svg width="72" height="72" viewBox="0 0 72 72" fill="none">
          <rect width="72" height="72" rx="16" fill={COLORS.primary} />
          <path d="M18 36 L28 22 L38 36 L28 50 Z" fill="white" opacity="0.9" />
          <path d="M34 36 L44 22 L54 36 L44 50 Z" fill="white" opacity="0.6" />
        </svg>
        <span style={{ fontSize: 36, fontWeight: 700, color: COLORS.textMuted, letterSpacing: '0.06em' }}>
          SKILLBERRY
        </span>
      </div>

      {/* Main title */}
      <div style={{
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
        textAlign: 'center',
      }}>
        <h1 style={{
          margin: 0,
          fontSize: 110,
          fontWeight: 900,
          color: COLORS.text,
          letterSpacing: '-0.02em',
          lineHeight: 1.0,
        }}>
          Skillberry Store
        </h1>
      </div>

      {/* Accent line */}
      <div style={{
        marginTop: 32,
        height: 4,
        width: lineWidth,
        background: `linear-gradient(90deg, ${COLORS.primary}, ${COLORS.accent})`,
        borderRadius: 2,
      }} />

      {/* Subtitle */}
      <div style={{ opacity: subtitleOpacity, marginTop: 28, textAlign: 'center' }}>
        <p style={{ margin: 0, fontSize: 34, color: COLORS.textMuted, fontWeight: 400 }}>
          Smart Skills Repository for Agentic Workflows
        </p>
      </div>

      {/* Tagline */}
      <div style={{ opacity: taglineOpacity, marginTop: 20 }}>
        <p style={{ margin: 0, fontSize: 24, color: COLORS.border, fontWeight: 500, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Manage · Execute · Organize · Publish
        </p>
      </div>
    </div>
  );
};
