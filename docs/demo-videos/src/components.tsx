import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { COLORS } from './constants';

// ── Fade-in from zero opacity
export const useFadeIn = (start = 0, duration = 20) => {
  const frame = useCurrentFrame();
  return interpolate(frame, [start, start + duration], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
};

// ── Slide up and fade in
export const useSlideUp = (start = 0, duration = 25, distance = 40) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({ frame: frame - start, fps, config: { damping: 80, stiffness: 200 }, durationInFrames: duration });
  return {
    opacity: interpolate(frame, [start, start + duration * 0.5], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
    transform: `translateY(${interpolate(progress, [0, 1], [distance, 0])}px)`,
  };
};

// ── Scale in from 0.85
export const useScaleIn = (start = 0, duration = 20) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - start, fps, config: { damping: 100, stiffness: 300 }, durationInFrames: duration });
  return {
    opacity: interpolate(frame, [start, start + duration * 0.4], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
    transform: `scale(${interpolate(s, [0, 1], [0.85, 1])})`,
  };
};

// ── Generic spring progress (0 → 1)
export const useSpring = (start: number, durationInFrames = 30) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - start, fps, config: { damping: 80, stiffness: 180 }, durationInFrames });
};

// ── Typewriter text
export const useTypewriter = (text: string, startFrame: number, framesPerChar = 2) => {
  const frame = useCurrentFrame();
  const charsToShow = Math.max(0, Math.floor((frame - startFrame) / framesPerChar));
  return text.slice(0, charsToShow);
};

// ── Blinking cursor
export const BlinkingCursor: React.FC = () => {
  const frame = useCurrentFrame();
  const visible = Math.floor(frame / 15) % 2 === 0;
  return (
    <span style={{
      display: 'inline-block',
      width: 2,
      height: '1em',
      background: COLORS.primary,
      marginLeft: 1,
      verticalAlign: 'text-bottom',
      opacity: visible ? 1 : 0,
    }} />
  );
};

// ── Tag chip (mimics PatternFly labels)
export const Tag: React.FC<{ label: string; color?: string; bg?: string }> = ({
  label, color = COLORS.tagText, bg = COLORS.tagBg,
}) => (
  <span style={{
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: 20,
    background: bg,
    color,
    fontSize: 20,
    fontWeight: 500,
    border: `1px solid ${color}30`,
    margin: '3px 4px',
    whiteSpace: 'nowrap',
  }}>
    {label}
  </span>
);

// ── Score badge
export const ScoreBadge: React.FC<{ label: string; score: number; delay?: number }> = ({ label, score, delay = 0 }) => {
  const frame = useCurrentFrame();
  const color = score >= 8 ? COLORS.success : score >= 6 ? COLORS.warning : COLORS.danger;
  const bg = score >= 8 ? COLORS.successLight : score >= 6 ? '#FFF5D4' : COLORS.dangerLight;
  const progress = interpolate(frame, [delay, delay + 45], [0, score], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const barWidth = interpolate(frame, [delay, delay + 45], [0, score * 10], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
      <span style={{ width: 200, fontSize: 24, color: COLORS.textMuted }}>{label}</span>
      <div style={{ flex: 1, height: 14, background: COLORS.border, borderRadius: 7, overflow: 'hidden' }}>
        <div style={{ width: `${barWidth}%`, height: '100%', background: color, borderRadius: 7 }} />
      </div>
      <span style={{ width: 70, fontSize: 24, fontWeight: 700, color, textAlign: 'right' }}>{Math.round(progress)}/10</span>
    </div>
  );
};

// ── Browser frame chrome
export const BrowserFrame: React.FC<{ url: string; children: React.ReactNode }> = ({ url, children }) => (
  <div style={{
    borderRadius: 12,
    overflow: 'hidden',
    boxShadow: '0 24px 80px rgba(0,0,0,0.22)',
    border: `1px solid ${COLORS.border}`,
    background: COLORS.bg,
  }}>
    {/* Browser chrome */}
    <div style={{ background: '#F1F1F1', padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 8, borderBottom: `1px solid ${COLORS.border}` }}>
      <div style={{ display: 'flex', gap: 7 }}>
        {['#FF5F57','#FFBD2E','#28CA42'].map((c, i) => (
          <div key={i} style={{ width: 14, height: 14, borderRadius: '50%', background: c }} />
        ))}
      </div>
      <div style={{ flex: 1, background: COLORS.bg, borderRadius: 6, padding: '5px 14px', fontSize: 16, color: COLORS.textMuted, textAlign: 'center', border: `1px solid ${COLORS.border}` }}>
        {url}
      </div>
    </div>
    {children}
  </div>
);

// ── Terminal window
export const TerminalWindow: React.FC<{ title?: string; children: React.ReactNode }> = ({ title = 'bash', children }) => (
  <div style={{
    borderRadius: 10,
    overflow: 'hidden',
    background: COLORS.codeBg,
    boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
    border: '1px solid #333',
  }}>
    <div style={{ background: '#2D2D2D', padding: '11px 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ display: 'flex', gap: 7 }}>
        {['#FF5F57','#FFBD2E','#28CA42'].map((c, i) => <div key={i} style={{ width: 14, height: 14, borderRadius: '50%', background: c }} />)}
      </div>
      <span style={{ flex: 1, textAlign: 'center', fontSize: 14, color: '#8A8A8A', fontFamily: 'inherit' }}>{title}</span>
    </div>
    <div style={{ padding: '24px 28px', fontFamily: "'JetBrains Mono', monospace", fontSize: 24, lineHeight: 1.75 }}>
      {children}
    </div>
  </div>
);

// ── Section Title card
export const SectionTitle: React.FC<{ label: string; title: string; subtitle?: string; delay?: number }> = ({
  label, title, subtitle, delay = 0,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [delay, delay + 22], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const y = interpolate(frame, [delay, delay + 28], [35, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <div style={{ opacity, transform: `translateY(${y}px)` }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: COLORS.primary, letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 14 }}>
        {label}
      </div>
      <div style={{ fontSize: 68, fontWeight: 800, color: COLORS.text, lineHeight: 1.1, marginBottom: subtitle ? 18 : 0 }}>
        {title}
      </div>
      {subtitle && <div style={{ fontSize: 30, color: COLORS.textMuted, lineHeight: 1.6, marginTop: 8 }}>{subtitle}</div>}
    </div>
  );
};

// ── Highlight box
export const HighlightBox: React.FC<{ children: React.ReactNode; color?: string; delay?: number }> = ({
  children, color = COLORS.primary, delay = 0,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [delay, delay + 18], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <div style={{
      opacity,
      borderLeft: `5px solid ${color}`,
      background: `${color}12`,
      padding: '18px 26px',
      borderRadius: '0 10px 10px 0',
      margin: '14px 0',
    }}>
      {children}
    </div>
  );
};

// ── Feature bullet
export const FeatureBullet: React.FC<{ icon: string; text: string; delay?: number }> = ({ icon, text, delay = 0 }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [delay, delay + 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const x = interpolate(frame, [delay, delay + 20], [-30, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <div style={{ opacity, transform: `translateX(${x}px)`, display: 'flex', alignItems: 'flex-start', gap: 16, marginBottom: 18 }}>
      <span style={{ fontSize: 26, lineHeight: 1.4, minWidth: 32 }}>{icon}</span>
      <span style={{ fontSize: 28, color: COLORS.text, lineHeight: 1.45 }}>{text}</span>
    </div>
  );
};

// ── Plugin card (mimics the real plugin card UI)
export const PluginCard: React.FC<{
  name: string;
  description: string;
  enabled?: boolean;
  tag: string;
  version?: string;
  delay?: number;
  highlight?: boolean;
  actionLabel?: string;
}> = ({ name, description, enabled = false, tag, version = 'v0.1.0', delay = 0, highlight = false, actionLabel }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [delay, delay + 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const y = interpolate(frame, [delay, delay + 25], [20, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <div style={{
      opacity,
      transform: `translateY(${y}px)`,
      border: `2px solid ${highlight ? COLORS.primary : COLORS.border}`,
      borderRadius: 10,
      padding: '20px 24px',
      background: highlight ? COLORS.primaryLight : COLORS.bg,
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span style={{ fontSize: 22, fontWeight: 700, color: COLORS.text }}>{name}</span>
        <div style={{
          fontSize: 17,
          fontWeight: 600,
          color: enabled ? COLORS.success : COLORS.danger,
          background: enabled ? COLORS.successLight : COLORS.dangerLight,
          padding: '3px 12px',
          borderRadius: 12,
          border: `1px solid ${enabled ? COLORS.success : COLORS.danger}40`,
        }}>
          {enabled ? '✓ Enabled' : '⊗ Disabled'}
        </div>
      </div>
      <div style={{ fontSize: 20, color: COLORS.textMuted, lineHeight: 1.5 }}>{description}</div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Tag label={tag} />
        <Tag label={version} color={COLORS.textMuted} bg={COLORS.bgAlt} />
      </div>
      {actionLabel && (
        <button style={{
          marginTop: 4,
          padding: '8px 20px',
          background: COLORS.primary,
          color: COLORS.bg,
          border: 'none',
          borderRadius: 6,
          fontSize: 19,
          fontWeight: 600,
          cursor: 'default',
          alignSelf: 'flex-start',
        }}>{actionLabel}</button>
      )}
    </div>
  );
};
