import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, Img, staticFile } from 'remotion';
import { COLORS } from './constants';
import { useSlideUp, FeatureBullet } from './components';

// ════════════════════════════════════════
//  SCENE 01 – INTRO  (270 frames, 9s)
// ════════════════════════════════════════
export const SceneIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const bgOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const logoSlide = useSlideUp(10, 30, 60);
  const titleSlide = useSlideUp(25, 35, 50);
  const subSlide = useSlideUp(45, 30, 40);
  const fadeOut = interpolate(frame, [250, 270], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: bgOpacity * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      {/* Top accent bar */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />

      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 0 }}>
        {/* Logo icon */}
        <div style={{ ...logoSlide, marginBottom: 24 }}>
          <div style={{
            width: 96, height: 96, borderRadius: 24,
            background: COLORS.primary,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: `0 12px 40px ${COLORS.primary}40`,
          }}>
            <span style={{ color: '#fff', fontSize: 52, fontWeight: 800, fontFamily: 'monospace' }}>&lt;/&gt;</span>
          </div>
        </div>

        {/* Title */}
        <div style={{ ...titleSlide, textAlign: 'center' }}>
          <div style={{ fontSize: 96, fontWeight: 800, color: COLORS.text, letterSpacing: '-2px', lineHeight: 1 }}>
            Skillberry Store
          </div>
        </div>

        {/* Subtitle */}
        <div style={{ ...subSlide, textAlign: 'center', marginTop: 24 }}>
          <div style={{ fontSize: 36, color: COLORS.textMuted, fontWeight: 400 }}>
            A smart skills repository for agentic workflows
          </div>
        </div>

        {/* Version pill */}
        <div style={{
          ...useSlideUp(65, 25, 30),
          marginTop: 36,
          padding: '10px 28px',
          background: COLORS.primaryLight,
          borderRadius: 24,
          fontSize: 22,
          color: COLORS.primary,
          fontWeight: 600,
          border: `1px solid ${COLORS.primary}40`,
        }}>
          branch-0.2.0
        </div>
      </div>

      {/* Bottom line */}
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 3, background: `linear-gradient(90deg, ${COLORS.primary}, ${COLORS.accent})` }} />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 02 – WHAT IS SBS  (450 frames, 15s)
// ════════════════════════════════════════
export const SceneWhatIs: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [430, 450], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const features = [
    { icon: '🛠️', text: 'Manage tools for agentic workloads — add, update, delete, execute', delay: 30 },
    { icon: '🔍', text: 'Semantic and full-text search across skills, tools, and snippets', delay: 60 },
    { icon: '🔄', text: 'Tools lifecycle management with state, visibility, and versioning', delay: 90 },
    { icon: '🌐', text: 'MCP frontend — expose virtual MCP servers for any subset of tools', delay: 120 },
    { icon: '🗂️', text: 'Virtual NFS / WebDAV servers — mount skill files as a filesystem', delay: 150 },
    { icon: '🔌', text: 'Extensible plugin system for AI-powered analysis and optimization', delay: 180 },
    { icon: '📊', text: 'Observability — Prometheus metrics and OpenTelemetry traces', delay: 210 },
  ];

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />

      <div style={{ position: 'absolute', inset: 0, padding: '80px 120px', display: 'flex', gap: 100 }}>
        {/* Left */}
        <div style={{ flex: '0 0 560px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ ...useSlideUp(5, 25, 40) }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: COLORS.primary, letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 14 }}>
              What is it?
            </div>
            <div style={{ fontSize: 62, fontWeight: 800, color: COLORS.text, lineHeight: 1.1, marginBottom: 24 }}>
              A Smart Skills Repository
            </div>
            <div style={{ fontSize: 28, color: COLORS.textMuted, lineHeight: 1.6 }}>
              Skillberry Store (SBS) centralises every tool your AI agents need. Upload once, execute anywhere, manage everything from one place.
            </div>
          </div>
        </div>

        {/* Right – feature bullets */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 4 }}>
          {features.map((f, i) => (
            <FeatureBullet key={i} icon={f.icon} text={f.text} delay={f.delay} />
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 03 – INSTALLATION  (600 frames, 20s)
// ════════════════════════════════════════
export const SceneInstall: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [580, 600], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const tw = (text: string, start: number, fpc = 2) => {
    const chars = Math.max(0, Math.floor((frame - start) / fpc));
    return text.slice(0, chars);
  };

  const C = (color: string, text: string) => <span style={{ color }}>{text}</span>;
  const cursor = <span style={{ borderLeft: '2px solid #0066CC', marginLeft: 1 }}/>;

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />

      <div style={{ position: 'absolute', inset: 0, padding: '72px 120px', display: 'flex', gap: 80, alignItems: 'center' }}>
        {/* Left – title + options */}
        <div style={{ flex: '0 0 480px', display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ ...useSlideUp(5, 25, 40) }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: COLORS.primary, letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 14 }}>Installation</div>
            <div style={{ fontSize: 62, fontWeight: 800, color: COLORS.text, lineHeight: 1.1 }}>Get Started<br />in Seconds</div>
          </div>

          {/* Prereqs */}
          <div style={{ ...useSlideUp(40, 20, 30), marginTop: 16 }}>
            <div style={{ fontSize: 22, fontWeight: 600, color: COLORS.text, marginBottom: 8 }}>Prerequisites</div>
            {['Python 3.10+', 'Docker or Podman', 'Node.js 18+ (for UI)'].map((p, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, opacity: interpolate(frame, [50 + i * 15, 65 + i * 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS.primary }} />
                <span style={{ fontSize: 24, color: COLORS.textMuted }}>{p}</span>
              </div>
            ))}
          </div>

          {/* Endpoints */}
          <div style={{ ...useSlideUp(100, 20, 30), marginTop: 4 }}>
            <div style={{ fontSize: 22, fontWeight: 600, color: COLORS.text, marginBottom: 10 }}>Endpoints after start</div>
            {[
              { label: 'Web UI', url: 'http://localhost:8002' },
              { label: 'REST API', url: 'http://localhost:8000' },
              { label: 'MCP Control', url: 'http://localhost:8000/control_sse' },
            ].map((e, i) => (
              <div key={i} style={{ display: 'flex', gap: 12, marginBottom: 8, opacity: interpolate(frame, [110 + i * 12, 125 + i * 12], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) }}>
                <span style={{ fontSize: 21, color: COLORS.textMuted, width: 110 }}>{e.label}</span>
                <span style={{ fontSize: 21, color: COLORS.primary, fontFamily: 'monospace' }}>{e.url}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right – terminal */}
        <div style={{ flex: 1, ...useSlideUp(15, 30, 50) }}>
          <div style={{
            borderRadius: 10, overflow: 'hidden', background: COLORS.codeBg,
            boxShadow: '0 20px 60px rgba(0,0,0,0.4)', border: '1px solid #333',
          }}>
            <div style={{ background: '#2D2D2D', padding: '11px 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ display: 'flex', gap: 7 }}>
                {['#FF5F57','#FFBD2E','#28CA42'].map((c, i) => <div key={i} style={{ width: 14, height: 14, borderRadius: '50%', background: c }} />)}
              </div>
              <span style={{ flex: 1, textAlign: 'center', fontSize: 14, color: '#8A8A8A', fontFamily: 'monospace' }}>bash</span>
            </div>
            <div style={{ padding: '28px 32px', fontFamily: "'JetBrains Mono', 'Fira Code', monospace", fontSize: 26, lineHeight: 2 }}>
              {frame >= 30 && <div>{C('#6A9955', '# Minimal install')}</div>}
              {frame >= 45 && <div>{C('#569CD6', '$ ')}{C('#CE9178', tw('pip install skillberry-store', 45))}{frame < 120 && cursor}</div>}
              {frame >= 130 && <div style={{ marginTop: 8 }}>{C('#6A9955', '# With all plugins')}</div>}
              {frame >= 145 && <div>{C('#569CD6', '$ ')}{C('#CE9178', tw('pip install skillberry-store[plugins-all]', 145))}{frame < 230 && cursor}</div>}
              {frame >= 245 && <div style={{ marginTop: 16 }}>{C('#6A9955', '# Run with Docker')}</div>}
              {frame >= 258 && <div>{C('#569CD6', '$ ')}{C('#DCDCAA', tw('make docker-run', 258))}{frame >= 258 && frame < 330 && cursor}</div>}
              {frame >= 350 && <div style={{ marginTop: 16 }}>{C('#6A9955', tw('# or locally:', 350))}</div>}
              {frame >= 380 && <div>{C('#569CD6', '$ ')}{C('#DCDCAA', tw('make run', 380))}{frame >= 380 && frame < 450 && cursor}</div>}
              {/* Success */}
              {frame >= 460 && (
                <div style={{ marginTop: 16, color: COLORS.codeGreen }}>
                  ✓  Skillberry Store is running
                </div>
              )}
              {frame >= 475 && <div style={{ color: '#9CDCFE', fontSize: 22 }}>  Web UI  →  http://localhost:8002</div>}
              {frame >= 490 && <div style={{ color: '#9CDCFE', fontSize: 22 }}>  REST API →  http://localhost:8000/docs</div>}
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
