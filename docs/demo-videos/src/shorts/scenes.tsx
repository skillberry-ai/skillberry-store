import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, Img, staticFile } from 'remotion';
import { COLORS } from './constants';

// ── shared animation helpers (scene-local frames) ─────────────────────────
const clampOpts = { extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const };
const useUp = (start = 0, dur = 18, dist = 32) => {
  const f = useCurrentFrame();
  return {
    opacity: interpolate(f, [start, start + dur * 0.6], [0, 1], clampOpts),
    transform: `translateY(${interpolate(f, [start, start + dur], [dist, 0], clampOpts)}px)`,
  };
};
const useFadeIn = (start = 0, dur = 14) => {
  const f = useCurrentFrame();
  return interpolate(f, [start, start + dur], [0, 1], clampOpts);
};
const fadeOut = (total: number, dur = 12) => {
  const f = useCurrentFrame();
  return interpolate(f, [total - dur, total], [1, 0], clampOpts);
};
const appear = (start: number, dur = 14) => {
  const f = useCurrentFrame();
  return interpolate(f, [start, start + dur], [0, 1], clampOpts);
};

const FONT = "'Segoe UI', system-ui, sans-serif";

// ── inline SVG icons (headless Chromium has no color-emoji font) ──────────
const ICON_PATHS: Record<string, React.ReactNode> = {
  link: (<><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></>),
  box: (<><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><path d="m3.27 6.96 8.73 5.05 8.73-5.05" /><path d="M12 22.08V12" /></>),
  folder: (<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />),
  plug: (<><path d="M9 2v6" /><path d="M15 2v6" /><path d="M6 8h12v3a6 6 0 0 1-12 0z" /><path d="M12 17v5" /></>),
  drive: (<><line x1="22" y1="12" x2="2" y2="12" /><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" /><line x1="6" y1="16" x2="6.01" y2="16" /><line x1="10" y1="16" x2="10.01" y2="16" /></>),
  chart: (<><line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /></>),
  globe: (<><circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></>),
  book: (<><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" /><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" /></>),
  download: (<><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></>),
};
const Icon = ({ name, size = 24, color = COLORS.primary, strokeWidth = 2 }: { name: keyof typeof ICON_PATHS; size?: number; color?: string; strokeWidth?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
    {ICON_PATHS[name]}
  </svg>
);

// ── presentational sub-components ─────────────────────────────────────────
const Bar = ({ color = COLORS.primary }: { color?: string }) => (
  <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: color }} />
);
const BottomBar = () => (
  <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 3, background: `linear-gradient(90deg,${COLORS.primary},${COLORS.accent})` }} />
);
const Tag = ({ label, color = COLORS.tagText, bg = COLORS.tagBg }: { label: string; color?: string; bg?: string }) => (
  <span style={{ display: 'inline-block', padding: '3px 12px', borderRadius: 20, background: bg, color, fontSize: 21, fontWeight: 500, border: `1px solid ${color}28`, margin: '3px 4px', whiteSpace: 'nowrap' }}>
    {label}
  </span>
);
const ScoreBar = ({ label, score, delay = 0 }: { label: string; score: number; delay?: number }) => {
  const f = useCurrentFrame();
  const c = score >= 8 ? COLORS.success : score >= 6 ? COLORS.warning : COLORS.danger;
  const w = interpolate(f, [delay, delay + 30], [0, score * 10], clampOpts);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 14 }}>
      <span style={{ width: 170, fontSize: 22, color: COLORS.textMuted }}>{label}</span>
      <div style={{ flex: 1, height: 13, background: COLORS.border, borderRadius: 7, overflow: 'hidden' }}>
        <div style={{ width: `${w}%`, height: '100%', background: c, borderRadius: 7 }} />
      </div>
      <span style={{ width: 60, fontSize: 22, fontWeight: 700, color: c, textAlign: 'right' }}>{score}/10</span>
    </div>
  );
};

// ════════════════════════════════════════════════════════════
//  S1 — INTRO (108 frames, 3.6s)
// ════════════════════════════════════════════════════════════
export const TzIntro: React.FC = () => {
  const f = useCurrentFrame();
  const fo = fadeOut(108);
  const logoOp = interpolate(f, [0, 14], [0, 1], clampOpts);
  const lineW  = interpolate(f, [16, 60], [0, 560], clampOpts);
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fo, fontFamily: FONT }}>
      <Bar />
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ opacity: logoOp, marginBottom: 20 }}>
          <div style={{ width: 80, height: 80, borderRadius: 20, background: COLORS.primary, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 12px 36px ${COLORS.primary}40` }}>
            <span style={{ color: '#fff', fontSize: 42, fontWeight: 800, fontFamily: 'monospace' }}>&lt;/&gt;</span>
          </div>
        </div>
        <div style={{ ...useUp(6, 22, 42), textAlign: 'center' }}>
          <div style={{ fontSize: 96, fontWeight: 900, color: COLORS.text, letterSpacing: '-2px', lineHeight: 1 }}>Skillberry Store</div>
        </div>
        <div style={{ width: lineW, height: 4, background: `linear-gradient(90deg,${COLORS.primary},${COLORS.accent})`, borderRadius: 2, margin: '24px 0' }} />
        <div style={{ ...useUp(30, 18, 28), fontSize: 30, color: COLORS.textMuted }}>One service for every skill your agents need</div>
      </div>
      <BottomBar />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
//  S2 — IMPORT (168 frames, 5.6s)
// ════════════════════════════════════════════════════════════
export const TzImport: React.FC = () => {
  const f = useCurrentFrame();
  const fo = fadeOut(168);
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fo, fontFamily: FONT }}>
      <Bar />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div style={{ ...useUp(3, 16, 26), display: 'flex', alignItems: 'baseline', gap: 20 }}>
          <div style={{ fontSize: 46, fontWeight: 800, color: COLORS.text }}>Import an Anthropic Skill</div>
          <div style={{ fontSize: 22, color: COLORS.textMuted }}>— GitHub URL · ZIP · Local Folder</div>
        </div>
        <div style={{ flex: 1, display: 'flex', gap: 48 }}>
          <div style={{ flex: 1.1, ...useUp(8, 22, 36), overflow: 'hidden', borderRadius: 12, boxShadow: '0 16px 48px rgba(0,0,0,0.16)', border: `1px solid ${COLORS.border}` }}>
            <Img src={staticFile('screenshots/sbs-import-local-folder.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
          </div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 16 }}>
            {[
              { icon: 'link' as const, t: 'GitHub URL — any Anthropic skills repo', d: 18 },
              { icon: 'box' as const, t: 'ZIP File — for air-gapped environments', d: 32 },
              { icon: 'folder' as const, t: 'Local Folder — ideal for CI/CD pipelines', d: 46 },
            ].map((b, i) => (
              <div key={i} style={{ opacity: appear(b.d, 14), display: 'flex', gap: 16, alignItems: 'center', padding: '14px 18px', borderRadius: 10, background: COLORS.bgAlt, border: `1px solid ${COLORS.border}` }}>
                <Icon name={b.icon} size={30} color={COLORS.primary} />
                <span style={{ fontSize: 24, color: COLORS.text, lineHeight: 1.45 }}>{b.t}</span>
              </div>
            ))}
            <div style={{ opacity: appear(70, 16), transform: `scale(${interpolate(f, [70, 92], [0.9, 1], clampOpts)})`, padding: '16px 20px', background: COLORS.successLight, borderRadius: 10, border: `1px solid ${COLORS.success}40`, fontSize: 24, color: COLORS.success, fontWeight: 700 }}>
              ✓ 66 tools + 43 snippets imported in one click
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
//  S3 — AI SCORING (168 frames, 5.6s)
// ════════════════════════════════════════════════════════════
export const TzScoring: React.FC = () => {
  const f = useCurrentFrame();
  const fo = fadeOut(168);
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fo, fontFamily: FONT }}>
      <Bar color="#2E8B57" />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 80, alignItems: 'center' }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ ...useUp(3, 16, 30) }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#2E8B57', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 10 }}>AI Plugins</div>
            <div style={{ fontSize: 52, fontWeight: 800, color: COLORS.text, lineHeight: 1.1, marginBottom: 16 }}>Auto-Scored<br />on Import</div>
            <div style={{ fontSize: 24, color: COLORS.textMuted, lineHeight: 1.6 }}>LLM-powered analysis tags every skill with quality, performance, and security scores — automatically.</div>
          </div>
          <div style={{ ...useUp(40, 18, 26) }}>
            <div style={{ fontSize: 20, fontWeight: 600, color: COLORS.textMuted, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.1em' }}>summarizer — auto scores</div>
            <ScoreBar label="Quality"     score={9} delay={48} />
            <ScoreBar label="Performance" score={8} delay={62} />
            <ScoreBar label="Security"    score={8} delay={76} />
          </div>
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 14 }}>
          {[
            { name: 'Content Evaluator', desc: 'Quality, performance & security scores', color: '#2E8B57', delay: 18, enabled: true },
            { name: 'Security Evaluator', desc: 'Vulnerability analysis with CVE checks', color: COLORS.danger, delay: 34, enabled: true },
            { name: 'SAST Scanner', desc: 'Static code analysis via Bandit engine', color: COLORS.warning, delay: 50, enabled: false },
          ].map((p, i) => (
            <div key={i} style={{ opacity: appear(p.delay, 14), border: `2px solid ${p.color}`, borderRadius: 10, padding: '16px 20px', background: `${p.color}08` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 22, fontWeight: 700, color: COLORS.text }}>{p.name}</span>
                <span style={{ fontSize: 16, fontWeight: 600, color: p.enabled ? COLORS.success : COLORS.danger, background: p.enabled ? COLORS.successLight : COLORS.dangerLight, padding: '2px 10px', borderRadius: 10 }}>{p.enabled ? '✓ Enabled' : '⊗ Disabled'}</span>
              </div>
              <div style={{ fontSize: 20, color: COLORS.textMuted }}>{p.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
//  S4 — EXECUTE (150 frames, 5.0s)
// ════════════════════════════════════════════════════════════
export const TzExecute: React.FC = () => {
  const f = useCurrentFrame();
  const fo = fadeOut(150);
  const tw = (t: string, s: number) => t.slice(0, Math.max(0, Math.floor((f - s) * 2.2)));
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fo, fontFamily: FONT }}>
      <Bar />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 64, alignItems: 'center' }}>
        <div style={{ flex: 1, height: '82%', ...useUp(6, 22, 36), overflow: 'hidden', borderRadius: 12, boxShadow: '0 16px 48px rgba(0,0,0,0.16)', border: `1px solid ${COLORS.border}` }}>
          <Img src={staticFile('screenshots/sbs3-tool-execute-dialog.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ ...useUp(3, 16, 30) }}>
            <div style={{ fontSize: 46, fontWeight: 800, color: COLORS.text, marginBottom: 10 }}>Execute Tools</div>
            <div style={{ fontSize: 24, color: COLORS.textMuted, lineHeight: 1.6 }}>UI dialog or CLI — every run happens inside a Docker sandbox, fully isolated from the host.</div>
          </div>
          <div style={{ ...useUp(28, 18, 26), borderRadius: 10, overflow: 'hidden', background: COLORS.codeBg, border: '1px solid #333' }}>
            <div style={{ padding: '20px 24px', fontFamily: 'monospace', fontSize: 23, lineHeight: 1.85, minHeight: 120 }}>
              {f >= 34 && <div><span style={{ color: '#569CD6' }}>$ </span><span style={{ color: '#CE9178' }}>{tw('sbs execute-tool create_bullet_summary', 34)}</span></div>}
              {f >= 74 && <div style={{ color: '#9CDCFE', paddingLeft: 16 }}>{tw("  --body='{\"params\":{\"text\":\"...\"}}'", 74)}</div>}
              {f >= 108 && <div style={{ marginTop: 10, color: '#6A9955' }}>✓  Executed in 1.3s (Docker sandbox)</div>}
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
//  S5 — POWER FEATURES (150 frames, 5.0s)
// ════════════════════════════════════════════════════════════
export const TzPower: React.FC = () => {
  const f = useCurrentFrame();
  const fo = fadeOut(150);
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fo, fontFamily: FONT }}>
      <Bar />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div style={{ ...useUp(3, 16, 26) }}>
          <div style={{ fontSize: 46, fontWeight: 800, color: COLORS.text }}>Built for Real Workflows</div>
        </div>
        <div style={{ flex: 1, display: 'flex', gap: 28, alignItems: 'stretch' }}>
          {[
            { icon: 'plug' as const, title: 'Virtual MCP Servers', desc: 'Expose any skill as a standalone MCP endpoint with its own port and SSE URL. Plug into Claude, Cursor, or any AI client.', color: COLORS.primary, delay: 14 },
            { icon: 'drive' as const, title: 'Virtual NFS Servers', desc: 'Mount a skill as a read-only WebDAV or NFSv3 filesystem. Claude Code reads files directly — no REST API needed.', color: '#7B5CD8', delay: 30 },
            { icon: 'chart' as const, title: 'Observability', desc: 'Live metrics dashboard. Prometheus on :8090, OpenTelemetry traces to Jaeger. Grafana-ready out of the box.', color: COLORS.warning, delay: 46 },
          ].map((c, i) => (
            <div key={i} style={{ flex: 1, opacity: appear(c.delay, 16), transform: `translateY(${interpolate(f, [c.delay, c.delay + 18], [22, 0], clampOpts)}px)`, border: `2px solid ${c.color}`, borderRadius: 14, padding: '28px 28px', background: `${c.color}06`, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ width: 60, height: 60, borderRadius: 14, background: `${c.color}14`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon name={c.icon} size={34} color={c.color} strokeWidth={2} />
              </div>
              <div style={{ fontSize: 26, fontWeight: 800, color: COLORS.text }}>{c.title}</div>
              <div style={{ fontSize: 22, color: COLORS.textMuted, lineHeight: 1.55, flex: 1 }}>{c.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
//  S6 — OUTRO (156 frames, 5.2s)
// ════════════════════════════════════════════════════════════
export const TzOutro: React.FC = () => {
  const f = useCurrentFrame();
  const fi = useFadeIn(0, 16);
  const items = [
    { icon: 'globe' as const,    label: 'Web UI',   val: 'localhost:8002', delay: 34 },
    { icon: 'book' as const,     label: 'REST API', val: 'localhost:8000/docs', delay: 46 },
    { icon: 'download' as const, label: 'Install',  val: 'pip install skillberry-store', delay: 58 },
    { icon: 'box' as const,      label: 'Docker',   val: 'make docker-run', delay: 70 },
  ];
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fi, fontFamily: FONT }}>
      <Bar />
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ ...useUp(6, 24, 42), textAlign: 'center' }}>
          <div style={{ fontSize: 88, fontWeight: 900, color: COLORS.text, letterSpacing: '-1.5px' }}>Skillberry Store</div>
          <div style={{ fontSize: 28, color: COLORS.textMuted, marginTop: 14 }}>One service for every skill your agents need</div>
        </div>
        <div style={{ width: 480, height: 4, background: `linear-gradient(90deg,${COLORS.primary},${COLORS.accent})`, borderRadius: 2, margin: '28px 0' }} />
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', justifyContent: 'center', maxWidth: 1200 }}>
          {items.map((item, i) => (
            <div key={i} style={{ opacity: appear(item.delay, 14), transform: `translateY(${interpolate(f, [item.delay, item.delay + 16], [18, 0], clampOpts)}px)`, padding: '14px 20px', background: COLORS.bgAlt, borderRadius: 10, border: `1px solid ${COLORS.border}`, display: 'flex', gap: 14, alignItems: 'center' }}>
              <Icon name={item.icon} size={26} color={COLORS.primary} />
              <div>
                <div style={{ fontSize: 17, fontWeight: 700, color: COLORS.textMuted }}>{item.label}</div>
                <div style={{ fontSize: 20, color: COLORS.primary, fontFamily: 'monospace' }}>{item.val}</div>
              </div>
            </div>
          ))}
        </div>
        <div style={{ opacity: appear(96, 20), marginTop: 28, padding: '14px 36px', background: COLORS.primaryLight, borderRadius: 12, fontSize: 24, color: COLORS.primary, fontWeight: 600, border: `1px solid ${COLORS.primary}40` }}>
          github.com/skillberry-ai/skillberry-store
        </div>
      </div>
      <BottomBar />
    </AbsoluteFill>
  );
};
