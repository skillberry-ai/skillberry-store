import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, Img, staticFile } from 'remotion';
import { COLORS } from './constants';
import { useSlideUp, FeatureBullet } from './components';

// ════════════════════════════════════════
//  SCENE 23 – CLI EXECUTE TOOL  (480 frames, 16s)
// ════════════════════════════════════════
export const SceneCLIExecuteTool: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [460, 480], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const tw = (text: string, start: number, fpc = 2) => text.slice(0, Math.max(0, Math.floor((frame - start) / fpc)));

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 64, alignItems: 'center' }}>
        {/* Left */}
        <div style={{ flex: '0 0 460px', display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ ...useSlideUp(5, 25, 40) }}>
            <div style={{ fontSize: 21, fontWeight: 700, color: COLORS.primary, letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 12 }}>CLI Execution</div>
            <div style={{ fontSize: 56, fontWeight: 800, color: COLORS.text, lineHeight: 1.1, marginBottom: 16 }}>Run a Tool from the CLI</div>
            <div style={{ fontSize: 24, color: COLORS.textMuted, lineHeight: 1.6 }}>
              <code style={{ background: COLORS.bgAlt, padding: '2px 8px', borderRadius: 4 }}>sbs execute-tool</code> accepts JSON parameters and returns structured results. Same Docker sandbox as the UI.
            </div>
          </div>
          <div style={{ ...useSlideUp(70, 20, 28) }}>
            {[
              { text: 'Semantic search before execution: find the right tool', delay: 80 },
              { text: 'Scriptable — pipe results into jq, files, or CI pipelines', delay: 110 },
              { text: 'All operations: list, get, create, update, delete, execute', delay: 140 },
            ].map((b, i) => (
              <div key={i} style={{
                opacity: interpolate(frame, [b.delay, b.delay + 18], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
                display: 'flex', gap: 12, marginBottom: 12, alignItems: 'flex-start',
              }}>
                <span style={{ color: COLORS.primary, fontWeight: 700, marginTop: 3 }}>→</span>
                <span style={{ fontSize: 22, color: COLORS.textMuted, lineHeight: 1.5 }}>{b.text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right: terminal */}
        <div style={{ flex: 1, ...useSlideUp(20, 30, 45) }}>
          <div style={{
            borderRadius: 10, overflow: 'hidden', background: COLORS.codeBg,
            boxShadow: '0 20px 60px rgba(0,0,0,0.4)', border: '1px solid #333',
          }}>
            <div style={{ background: '#2D2D2D', padding: '11px 16px', display: 'flex', gap: 7 }}>
              {['#FF5F57','#FFBD2E','#28CA42'].map((c, i) => <div key={i} style={{ width: 14, height: 14, borderRadius: '50%', background: c }} />)}
              <span style={{ flex: 1, textAlign: 'center', fontSize: 14, color: '#8A8A8A', fontFamily: 'monospace' }}>bash — sbs</span>
            </div>
            <div style={{ padding: '24px 28px', fontFamily: "monospace", fontSize: 23, lineHeight: 1.8 }}>
              {frame >= 30 && <div style={{ color: '#6A9955' }}># Search for the right tool first</div>}
              {frame >= 45 && <div style={{ color: '#569CD6' }}>$ <span style={{ color: '#CE9178' }}>{tw('sbs search-tools "bullet summary"', 45, 3)}</span></div>}
              {frame >= 120 && <div style={{ color: '#9CDCFE', marginTop: 8 }}>create_bullet_summary  (summarizer)</div>}
              {frame >= 135 && <div style={{ color: '#9CDCFE' }}>create_executive_summary  (summarizer)</div>}
              {frame >= 160 && <div style={{ marginTop: 16, color: '#6A9955' }}># Execute with JSON params</div>}
              {frame >= 175 && <div style={{ color: '#569CD6' }}>$ <span style={{ color: '#CE9178' }}>{tw('sbs execute-tool create_bullet_summary \\', 175, 3)}</span></div>}
              {frame >= 240 && <div style={{ color: '#9CDCFE', paddingLeft: 16 }}>{tw("  --body='{\"params\":{\"text\":\"...\"}}'", 240, 3)}</div>}
              {frame >= 310 && <div style={{ marginTop: 14, color: '#6A9955' }}>✓ Docker sandbox — executed in 1.4s</div>}
              {frame >= 335 && (
                <div style={{ color: '#D4D4D4', fontSize: 21, marginTop: 8 }}>
                  <div>result: [</div>
                  <div style={{ paddingLeft: 16, color: '#CE9178' }}>"Extractive &amp; abstractive techniques",</div>
                  <div style={{ paddingLeft: 16, color: '#CE9178' }}>"Multiple output formats",</div>
                  <div style={{ paddingLeft: 16, color: '#CE9178' }}>"Automated Python scripts"</div>
                  <div>]</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 24 – OBSERVABILITY  (420 frames, 14s)
// ════════════════════════════════════════
export const SceneObservability: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [400, 420], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 64, alignItems: 'center' }}>
        <div style={{ flex: 1, height: '85%', ...useSlideUp(20, 35, 50), overflow: 'hidden', borderRadius: 14, boxShadow: '0 20px 60px rgba(0,0,0,0.18)', border: `1px solid ${COLORS.border}` }}>
          <Img src={staticFile('screenshots/sbs-observability.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 20, justifyContent: 'center' }}>
          <div style={{ ...useSlideUp(5, 25, 40) }}>
            <div style={{ fontSize: 42, fontWeight: 800, color: COLORS.text, marginBottom: 12 }}>Observability</div>
            <div style={{ fontSize: 24, color: COLORS.textMuted, lineHeight: 1.6 }}>Built-in Prometheus metrics and OpenTelemetry traces — with a live time-series dashboard in the UI.</div>
          </div>
          {[
            { icon: '📊', text: 'Skills, Tools, Snippets, VMCP Metrics tabs — all live', delay: 50 },
            { icon: '⏱️', text: 'System Metrics: uptime, request rates, latency histograms', delay: 80 },
            { icon: '🔍', text: 'Jaeger traces for every tool execution', delay: 110 },
            { icon: '🎯', text: 'Prometheus scrape endpoint on :8090 — integrate with Grafana', delay: 140 },
          ].map((f, i) => <FeatureBullet key={i} icon={f.icon} text={f.text} delay={f.delay} />)}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 25 – ARCHITECTURE  (480 frames, 16s)
// ════════════════════════════════════════
export const SceneArchitecture: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [460, 480], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const blocks = [
    { label: 'Web UI', sub: 'React / PatternFly :8002', color: COLORS.primary, x: 760, y: 60, w: 400, delay: 20 },
    { label: 'REST API', sub: 'FastAPI / OpenAPI :8000', color: COLORS.primary, x: 760, y: 200, w: 400, delay: 40 },
    { label: 'MCP Frontend', sub: ':8000/control_sse', color: COLORS.accent, x: 180, y: 200, w: 380, delay: 60 },
    { label: 'vNFS WebDAV/NFS', sub: 'Mountable filesystem', color: '#7B5CD8', x: 1340, y: 200, w: 380, delay: 80 },
    { label: 'Skills / Tools / Snippets', sub: 'Core data model', color: COLORS.textMuted, x: 640, y: 360, w: 640, delay: 100 },
    { label: 'Docker Sandbox', sub: 'Tool execution', color: COLORS.warning, x: 200, y: 520, w: 380, delay: 120 },
    { label: 'Storage', sub: 'Filesystem / GitHub', color: COLORS.textMuted, x: 640, y: 520, w: 380, delay: 140 },
    { label: 'Plugins', sub: 'Creator · Evaluator · Security · Dedupe · Optimizer', color: '#7B5CD8', x: 1100, y: 520, w: 620, delay: 160 },
  ];

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />
      <div style={{ position: 'absolute', top: 50, left: 80 }}>
        <div style={{ ...useSlideUp(0, 22, 35), fontSize: 42, fontWeight: 800, color: COLORS.text }}>Architecture Overview</div>
        <div style={{ ...useSlideUp(8, 18, 25), fontSize: 22, color: COLORS.textMuted }}>Layered, pluggable, and observable</div>
      </div>

      {blocks.map((b, i) => (
        <div key={i} style={{
          position: 'absolute',
          left: b.x,
          top: b.y + 130,
          width: b.w,
          opacity: interpolate(frame, [b.delay, b.delay + 22], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          transform: `translateY(${interpolate(frame, [b.delay, b.delay + 22], [18, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })}px)`,
          background: COLORS.bg,
          border: `2px solid ${b.color}`,
          borderRadius: 10,
          padding: '14px 18px',
          boxShadow: `0 4px 16px ${b.color}18`,
        }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: b.color }}>{b.label}</div>
          <div style={{ fontSize: 18, color: COLORS.textMuted, marginTop: 4 }}>{b.sub}</div>
        </div>
      ))}
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 26 – OUTRO  (480 frames, 16s)
// ════════════════════════════════════════
export const SceneOutro: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const items = [
    { icon: '🌐', label: 'Web UI', val: 'http://localhost:8002', delay: 40 },
    { icon: '📚', label: 'REST API', val: 'http://localhost:8000/docs', delay: 60 },
    { icon: '🔌', label: 'MCP Control', val: 'http://localhost:8000/control_sse', delay: 80 },
    { icon: '📦', label: 'pip install', val: 'skillberry-store[plugins-all]', delay: 100 },
    { icon: '🐳', label: 'Docker', val: 'make docker-run', delay: 120 },
  ];

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: `linear-gradient(90deg, ${COLORS.primary}, ${COLORS.accent})` }} />
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 0 }}>
        {/* Logo mark */}
        <div style={{ ...useSlideUp(10, 30, 50), marginBottom: 20 }}>
          <div style={{ width: 80, height: 80, borderRadius: 20, background: COLORS.primary, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 12px 40px ${COLORS.primary}40` }}>
            <span style={{ color: '#fff', fontSize: 44, fontWeight: 800, fontFamily: 'monospace' }}>&lt;/&gt;</span>
          </div>
        </div>
        <div style={{ ...useSlideUp(15, 30, 45), textAlign: 'center' }}>
          <div style={{ fontSize: 80, fontWeight: 900, color: COLORS.text, letterSpacing: '-1px', lineHeight: 1 }}>Skillberry Store</div>
          <div style={{ fontSize: 28, color: COLORS.textMuted, marginTop: 16 }}>Manage · Execute · Organize · Publish your agent skills</div>
        </div>

        {/* Quick-start links */}
        <div style={{ marginTop: 40, display: 'flex', gap: 24, flexWrap: 'wrap', justifyContent: 'center', maxWidth: 1400 }}>
          {items.map((item, i) => (
            <div key={i} style={{
              opacity: interpolate(frame, [item.delay, item.delay + 18], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
              transform: `translateY(${interpolate(frame, [item.delay, item.delay + 22], [20, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })}px)`,
              padding: '16px 22px', background: COLORS.bgAlt, borderRadius: 10, border: `1px solid ${COLORS.border}`,
              display: 'flex', gap: 12, alignItems: 'center',
            }}>
              <span style={{ fontSize: 26 }}>{item.icon}</span>
              <div>
                <div style={{ fontSize: 18, fontWeight: 700, color: COLORS.textMuted }}>{item.label}</div>
                <div style={{ fontSize: 20, color: COLORS.primary, fontFamily: 'monospace' }}>{item.val}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Stars CTA */}
        <div style={{
          opacity: interpolate(frame, [180, 210], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          marginTop: 36, padding: '16px 40px', background: COLORS.primaryLight,
          borderRadius: 12, fontSize: 26, color: COLORS.primary, fontWeight: 600,
          border: `1px solid ${COLORS.primary}40`,
        }}>
          github.com/skillberry-ai/skillberry-store
        </div>
      </div>
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 3, background: `linear-gradient(90deg, ${COLORS.primary}, ${COLORS.accent})` }} />
    </AbsoluteFill>
  );
};
