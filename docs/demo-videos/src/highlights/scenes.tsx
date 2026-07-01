import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, Img, staticFile } from 'remotion';
import { COLORS } from './constants';

// ── shared animation helpers ─────────────────────────────────────────────
const useIn = (start = 0, dur = 18) => {
  const f = useCurrentFrame();
  return interpolate(f, [start, start + dur], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
};
const useUp = (start = 0, dur = 20, dist = 35) => {
  const f = useCurrentFrame();
  return {
    opacity: interpolate(f, [start, start + dur * 0.55], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
    transform: `translateY(${interpolate(f, [start, start + dur], [dist, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })}px)`,
  };
};
const fadeOut = (total: number, dur = 12) => {
  const f = useCurrentFrame();
  return interpolate(f, [total - dur, total], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
};

// ── thin top accent bar ───────────────────────────────────────────────────
const Bar = ({ color = COLORS.primary }: { color?: string }) => (
  <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: color }} />
);

// ── chip tag ─────────────────────────────────────────────────────────────
const Tag = ({ label, color = COLORS.tagText, bg = COLORS.tagBg }: { label: string; color?: string; bg?: string }) => (
  <span style={{ display: 'inline-block', padding: '3px 12px', borderRadius: 20, background: bg, color, fontSize: 21, fontWeight: 500, border: `1px solid ${color}28`, margin: '3px 4px', whiteSpace: 'nowrap' }}>
    {label}
  </span>
);

// ── animated score bar ────────────────────────────────────────────────────
const ScoreBar = ({ label, score, delay = 0 }: { label: string; score: number; delay?: number }) => {
  const f = useCurrentFrame();
  const c = score >= 8 ? COLORS.success : score >= 6 ? COLORS.warning : COLORS.danger;
  const w = interpolate(f, [delay, delay + 40], [0, score * 10], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
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
//  S1 — INTRO  (150 frames, 5s)
// ════════════════════════════════════════════════════════════
export const HlIntro: React.FC = () => {
  const f = useCurrentFrame();
  const fo = fadeOut(150);
  const logoOp = interpolate(f, [0, 18], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const lineW  = interpolate(f, [22, 80], [0, 560], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fo, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <Bar />
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 0 }}>
        <div style={{ opacity: logoOp, display: 'flex', alignItems: 'center', gap: 18, marginBottom: 20 }}>
          <div style={{ width: 80, height: 80, borderRadius: 20, background: COLORS.primary, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 12px 36px ${COLORS.primary}40` }}>
            <span style={{ color: '#fff', fontSize: 42, fontWeight: 800, fontFamily: 'monospace' }}>&lt;/&gt;</span>
          </div>
        </div>
        <div style={{ ...useUp(8, 25, 45), textAlign: 'center' }}>
          <div style={{ fontSize: 96, fontWeight: 900, color: COLORS.text, letterSpacing: '-2px', lineHeight: 1 }}>Skillberry Store</div>
        </div>
        <div style={{ width: lineW, height: 4, background: `linear-gradient(90deg,${COLORS.primary},${COLORS.accent})`, borderRadius: 2, margin: '24px 0' }} />
        <div style={{ ...useUp(35, 22, 30), fontSize: 30, color: COLORS.textMuted }}>Feature Highlights</div>
      </div>
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 3, background: `linear-gradient(90deg,${COLORS.primary},${COLORS.accent})` }} />
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
//  S2 — INSTALL  (180 frames, 6s)
// ════════════════════════════════════════════════════════════
export const HlInstall: React.FC = () => {
  const f = useCurrentFrame();
  const fo = fadeOut(180);
  const tw = (t: string, s: number) => t.slice(0, Math.max(0, Math.floor((f - s) * 18)));
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fo, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <Bar />
      <div style={{ position: 'absolute', inset: 0, padding: '80px 160px', display: 'flex', gap: 80, alignItems: 'center' }}>
        <div style={{ flex: '0 0 460px', ...useUp(5, 25, 40) }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: COLORS.primary, letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 12 }}>Install</div>
          <div style={{ fontSize: 64, fontWeight: 800, color: COLORS.text, lineHeight: 1.1, marginBottom: 20 }}>Up in 60 seconds</div>
          <div style={{ fontSize: 26, color: COLORS.textMuted, lineHeight: 1.6 }}>pip install, then make docker-run. Web UI on <span style={{ color: COLORS.primary, fontFamily: 'monospace' }}>:8002</span>, REST API on <span style={{ color: COLORS.primary, fontFamily: 'monospace' }}>:8000</span>.</div>
        </div>
        <div style={{ flex: 1, ...useUp(15, 28, 50) }}>
          <div style={{ borderRadius: 10, overflow: 'hidden', background: COLORS.codeBg, boxShadow: '0 16px 48px rgba(0,0,0,0.4)', border: '1px solid #333' }}>
            <div style={{ background: '#2D2D2D', padding: '11px 16px', display: 'flex', gap: 7 }}>
              {['#FF5F57','#FFBD2E','#28CA42'].map((c,i) => <div key={i} style={{ width: 13, height: 13, borderRadius: '50%', background: c }} />)}
            </div>
            <div style={{ padding: '24px 28px', fontFamily: 'monospace', fontSize: 26, lineHeight: 2 }}>
              {f >= 20 && <div><span style={{ color: '#6A9955' }}># install</span></div>}
              {f >= 28 && <div><span style={{ color: '#569CD6' }}>$ </span><span style={{ color: '#CE9178' }}>{tw('pip install skillberry-store[plugins-all]', 28)}</span></div>}
              {f >= 80 && <div style={{ marginTop: 12 }}><span style={{ color: '#6A9955' }}># start</span></div>}
              {f >= 90 && <div><span style={{ color: '#569CD6' }}>$ </span><span style={{ color: '#DCDCAA' }}>{tw('make docker-run', 90)}</span></div>}
              {f >= 140 && <div style={{ marginTop: 12, color: '#6A9955' }}>✓  Live on localhost:8002</div>}
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
//  S3 — IMPORT SKILL  (210 frames, 7s)
// ════════════════════════════════════════════════════════════
export const HlImport: React.FC = () => {
  const f = useCurrentFrame();
  const fo = fadeOut(210);
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fo, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <Bar />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div style={{ ...useUp(5, 22, 30), display: 'flex', alignItems: 'baseline', gap: 20 }}>
          <div style={{ fontSize: 44, fontWeight: 800, color: COLORS.text }}>Import an Anthropic Skill</div>
          <div style={{ fontSize: 22, color: COLORS.textMuted }}>— GitHub URL · ZIP · Local Folder</div>
        </div>
        <div style={{ flex: 1, display: 'flex', gap: 48 }}>
          <div style={{ flex: 1.1, ...useUp(15, 30, 40), overflow: 'hidden', borderRadius: 12, boxShadow: '0 16px 48px rgba(0,0,0,0.16)', border: `1px solid ${COLORS.border}` }}>
            <Img src={staticFile('screenshots/sbs-import-local-folder.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
          </div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 16 }}>
            {[
              { icon: '🔗', t: 'GitHub URL — point at any Anthropic skills repo', d: 40 },
              { icon: '📦', t: 'ZIP File — works in air-gapped environments', d: 70 },
              { icon: '📁', t: 'Local Folder — ideal for CI/CD pipelines', d: 100 },
            ].map((b, i) => (
              <div key={i} style={{ opacity: interpolate(f, [b.d, b.d + 18], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), display: 'flex', gap: 14, alignItems: 'flex-start', padding: '14px 18px', borderRadius: 10, background: COLORS.bgAlt, border: `1px solid ${COLORS.border}` }}>
                <span style={{ fontSize: 28 }}>{b.icon}</span>
                <span style={{ fontSize: 24, color: COLORS.text, lineHeight: 1.45 }}>{b.t}</span>
              </div>
            ))}
            <div style={{ opacity: interpolate(f, [160, 178], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), padding: '12px 18px', background: COLORS.successLight, borderRadius: 10, border: `1px solid ${COLORS.success}40`, fontSize: 22, color: COLORS.success, fontWeight: 600 }}>
              ✓ 66 tools + 43 snippets imported in one click
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
//  S4 — SKILLS UI  (210 frames, 7s)
// ════════════════════════════════════════════════════════════
export const HlSkillsUI: React.FC = () => {
  const f = useCurrentFrame();
  const fo = fadeOut(210);
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fo, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <Bar />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div style={{ ...useUp(5, 20, 30) }}>
          <div style={{ fontSize: 44, fontWeight: 800, color: COLORS.text }}>Skills, Tools &amp; Snippets</div>
          <div style={{ fontSize: 22, color: COLORS.textMuted }}>— sortable, filterable, executable</div>
        </div>
        <div style={{ flex: 1, display: 'flex', gap: 32 }}>
          <div style={{ flex: 1.3, ...useUp(15, 30, 40), overflow: 'hidden', borderRadius: 12, boxShadow: '0 16px 48px rgba(0,0,0,0.16)', border: `1px solid ${COLORS.border}` }}>
            <Img src={staticFile('screenshots/sbs2-skills-populated.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
          </div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 16 }}>
            <div style={{ opacity: interpolate(f, [40, 58], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), border: `2px solid ${COLORS.border}`, borderRadius: 12, padding: '20px 24px', background: COLORS.bgAlt }}>
              <div style={{ fontSize: 26, fontWeight: 700, color: COLORS.text, marginBottom: 8 }}>pptx</div>
              <div style={{ fontSize: 21, color: COLORS.textMuted, marginBottom: 10 }}>🔧 66 tools &nbsp; 📄 43 snippets</div>
              <div><Tag label="anthropic" /><Tag label="quality-score:8" color={COLORS.success} bg={COLORS.successLight} /><Tag label="security-score:4" color={COLORS.danger} bg={COLORS.dangerLight} /></div>
            </div>
            <div style={{ opacity: interpolate(f, [75, 93], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), border: `2px solid ${COLORS.border}`, borderRadius: 12, padding: '20px 24px', background: COLORS.bgAlt }}>
              <div style={{ fontSize: 26, fontWeight: 700, color: COLORS.text, marginBottom: 8 }}>summarizer</div>
              <div style={{ fontSize: 21, color: COLORS.textMuted, marginBottom: 10 }}>🔧 29 tools &nbsp; 📄 2 snippets</div>
              <div><Tag label="anthropic" /><Tag label="quality-score:9" color={COLORS.success} bg={COLORS.successLight} /><Tag label="security-score:8" color={COLORS.success} bg={COLORS.successLight} /></div>
            </div>
            <div style={{ opacity: interpolate(f, [140, 158], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), padding: '14px 18px', background: COLORS.primaryLight, borderRadius: 10, fontSize: 22, color: COLORS.primary, lineHeight: 1.5 }}>
              Text search, semantic search, and UUID lookup — all in the same bar.
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
//  S5 — EXECUTE TOOL  (210 frames, 7s)
// ════════════════════════════════════════════════════════════
export const HlExecute: React.FC = () => {
  const f = useCurrentFrame();
  const fo = fadeOut(210);
  const tw = (t: string, s: number) => t.slice(0, Math.max(0, Math.floor((f - s) * 15)));
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fo, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <Bar />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 64, alignItems: 'center' }}>
        <div style={{ flex: 1, height: '82%', ...useUp(10, 30, 40), overflow: 'hidden', borderRadius: 12, boxShadow: '0 16px 48px rgba(0,0,0,0.16)', border: `1px solid ${COLORS.border}` }}>
          <Img src={staticFile('screenshots/sbs3-tool-execute-dialog.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ ...useUp(5, 22, 35) }}>
            <div style={{ fontSize: 44, fontWeight: 800, color: COLORS.text, marginBottom: 10 }}>Execute Tools</div>
            <div style={{ fontSize: 24, color: COLORS.textMuted, lineHeight: 1.6 }}>UI dialog or CLI — both run in a Docker sandbox, fully isolated from the host.</div>
          </div>
          <div style={{ ...useUp(45, 22, 30), borderRadius: 10, overflow: 'hidden', background: COLORS.codeBg, border: '1px solid #333' }}>
            <div style={{ padding: '20px 24px', fontFamily: 'monospace', fontSize: 23, lineHeight: 1.85 }}>
              {f >= 50 && <div><span style={{ color: '#569CD6' }}>$ </span><span style={{ color: '#CE9178' }}>{tw('sbs execute-tool create_bullet_summary', 50)}</span></div>}
              {f >= 110 && <div style={{ color: '#9CDCFE', paddingLeft: 16 }}>{tw("  --body='{\"params\":{\"text\":\"...\"}}'", 110)}</div>}
              {f >= 165 && <div style={{ marginTop: 10, color: '#6A9955' }}>✓  Executed in 1.3s (Docker sandbox)</div>}
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
//  S6 — PLUGIN EVALUATOR  (210 frames, 7s)
// ════════════════════════════════════════════════════════════
export const HlPluginEval: React.FC = () => {
  const f = useCurrentFrame();
  const fo = fadeOut(210);
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fo, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <Bar color="#2E8B57" />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 80, alignItems: 'center' }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ ...useUp(5, 22, 35) }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#2E8B57', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 10 }}>AI Plugins</div>
            <div style={{ fontSize: 52, fontWeight: 800, color: COLORS.text, lineHeight: 1.1, marginBottom: 16 }}>Content Evaluator<br />+ Security Scanner</div>
            <div style={{ fontSize: 24, color: COLORS.textMuted, lineHeight: 1.6 }}>LLM-powered analysis auto-tags every skill with quality, performance, and security scores on import.</div>
          </div>
          <div style={{ ...useUp(55, 20, 28) }}>
            <div style={{ fontSize: 20, fontWeight: 600, color: COLORS.textMuted, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.1em' }}>summarizer — auto scores</div>
            <ScoreBar label="Quality"     score={9} delay={65} />
            <ScoreBar label="Performance" score={8} delay={85} />
            <ScoreBar label="Security"    score={8} delay={105} />
          </div>
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 14 }}>
          {[
            { name: 'Content Evaluator', desc: 'Quality, performance & security scores', color: '#2E8B57', delay: 30, enabled: true },
            { name: 'Security Evaluator', desc: 'Vulnerability analysis with CVE checks', color: COLORS.danger, delay: 65, enabled: true },
            { name: 'SAST Scanner', desc: 'Static code analysis via Bandit engine', color: COLORS.warning, delay: 100, enabled: false },
          ].map((p, i) => (
            <div key={i} style={{ opacity: interpolate(f, [p.delay, p.delay + 18], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), border: `2px solid ${p.color}`, borderRadius: 10, padding: '16px 20px', background: `${p.color}08` }}>
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
//  S7 — PLUGIN SECURITY detail  (180 frames, 6s)
// ════════════════════════════════════════════════════════════
export const HlPluginSec: React.FC = () => {
  const f = useCurrentFrame();
  const fo = fadeOut(180);
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fo, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <Bar color={COLORS.danger} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 80, alignItems: 'center' }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ ...useUp(5, 22, 35) }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: COLORS.danger, letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 10 }}>Dedupe · Creator · Optimizer</div>
            <div style={{ fontSize: 52, fontWeight: 800, color: COLORS.text, lineHeight: 1.1, marginBottom: 16 }}>Three More<br />AI Plugins</div>
          </div>
          {[
            { icon: '🔁', name: 'Skill Deduplicator', desc: 'LLM semantic comparison — finds near-identical skills, prompts Keep or Delete', delay: 40 },
            { icon: '✍️', name: 'Snippet Creator', desc: 'Natural language → production code, auto-tagged and saved to the store', delay: 75 },
            { icon: '🤖', name: 'Skill Optimizer', desc: 'Claude Code in RunSpace — exports, optimizes, re-imports with rationale', delay: 110 },
          ].map((p, i) => (
            <div key={i} style={{ opacity: interpolate(f, [p.delay, p.delay + 18], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), transform: `translateX(${interpolate(f, [p.delay, p.delay + 20], [-24, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })}px)`, display: 'flex', gap: 16, alignItems: 'flex-start', padding: '14px 18px', borderRadius: 10, background: COLORS.bgAlt, border: `1px solid ${COLORS.border}` }}>
              <span style={{ fontSize: 30 }}>{p.icon}</span>
              <div>
                <div style={{ fontSize: 23, fontWeight: 700, color: COLORS.text, marginBottom: 4 }}>{p.name}</div>
                <div style={{ fontSize: 21, color: COLORS.textMuted, lineHeight: 1.45 }}>{p.desc}</div>
              </div>
            </div>
          ))}
        </div>
        <div style={{ flex: 1, ...useUp(20, 30, 40), overflow: 'hidden', borderRadius: 12, boxShadow: '0 16px 48px rgba(0,0,0,0.16)', border: `1px solid ${COLORS.border}` }}>
          <Img src={staticFile('screenshots/sbs2-plugins-populated.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
//  S8 — VMCP / VNFS / OBSERVABILITY  (180 frames, 6s)
// ════════════════════════════════════════════════════════════
export const HlVMCP: React.FC = () => {
  const f = useCurrentFrame();
  const fo = fadeOut(180);
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fo, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <Bar />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div style={{ ...useUp(5, 20, 30) }}>
          <div style={{ fontSize: 44, fontWeight: 800, color: COLORS.text }}>More Power Features</div>
        </div>
        <div style={{ flex: 1, display: 'flex', gap: 28, alignItems: 'stretch' }}>
          {[
            { icon: '🔌', title: 'Virtual MCP Servers', desc: 'Expose any skill as a standalone MCP endpoint with its own port and SSE URL. Plug into Claude, Cursor, or any AI client.', color: COLORS.primary, delay: 25 },
            { icon: '🗂️', title: 'Virtual NFS Servers', desc: 'Mount a skill as a read-only WebDAV or NFSv3 filesystem. Claude Code reads files directly — no REST API needed.', color: '#7B5CD8', delay: 55 },
            { icon: '📊', title: 'Observability', desc: 'Live metrics dashboard. Prometheus on :8090, OpenTelemetry traces to Jaeger. Grafana-ready out of the box.', color: COLORS.warning, delay: 85 },
          ].map((c, i) => (
            <div key={i} style={{ flex: 1, opacity: interpolate(f, [c.delay, c.delay + 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), transform: `translateY(${interpolate(f, [c.delay, c.delay + 22], [24, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })}px)`, border: `2px solid ${c.color}`, borderRadius: 14, padding: '28px 28px', background: `${c.color}06`, display: 'flex', flexDirection: 'column', gap: 14 }}>
              <span style={{ fontSize: 44 }}>{c.icon}</span>
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
//  S9 — OUTRO  (270 frames, 9s)
// ════════════════════════════════════════════════════════════
export const HlOutro: React.FC = () => {
  const f = useCurrentFrame();
  const fi = useIn(0, 18);
  const items = [
    { icon: '🌐', label: 'Web UI',    val: 'localhost:8002', delay: 50 },
    { icon: '📚', label: 'REST API',  val: 'localhost:8000/docs', delay: 70 },
    { icon: '📦', label: 'Install',   val: 'pip install skillberry-store', delay: 90 },
    { icon: '🐳', label: 'Docker',    val: 'make docker-run', delay: 110 },
  ];
  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fi, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <Bar />
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 0 }}>
        <div style={{ ...useUp(8, 28, 45), textAlign: 'center' }}>
          <div style={{ fontSize: 88, fontWeight: 900, color: COLORS.text, letterSpacing: '-1.5px' }}>Skillberry Store</div>
          <div style={{ fontSize: 28, color: COLORS.textMuted, marginTop: 14 }}>One service for every skill your agents need</div>
        </div>
        <div style={{ width: 480, height: 4, background: `linear-gradient(90deg,${COLORS.primary},${COLORS.accent})`, borderRadius: 2, margin: '28px 0' }} />
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', justifyContent: 'center', maxWidth: 1200 }}>
          {items.map((item, i) => (
            <div key={i} style={{ opacity: interpolate(f, [item.delay, item.delay + 16], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), transform: `translateY(${interpolate(f, [item.delay, item.delay + 18], [18, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })}px)`, padding: '14px 20px', background: COLORS.bgAlt, borderRadius: 10, border: `1px solid ${COLORS.border}`, display: 'flex', gap: 12, alignItems: 'center' }}>
              <span style={{ fontSize: 26 }}>{item.icon}</span>
              <div>
                <div style={{ fontSize: 17, fontWeight: 700, color: COLORS.textMuted }}>{item.label}</div>
                <div style={{ fontSize: 20, color: COLORS.primary, fontFamily: 'monospace' }}>{item.val}</div>
              </div>
            </div>
          ))}
        </div>
        <div style={{ opacity: interpolate(f, [160, 185], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), marginTop: 28, padding: '14px 36px', background: COLORS.primaryLight, borderRadius: 12, fontSize: 24, color: COLORS.primary, fontWeight: 600, border: `1px solid ${COLORS.primary}40` }}>
          github.com/skillberry-ai/skillberry-store
        </div>
      </div>
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 3, background: `linear-gradient(90deg,${COLORS.primary},${COLORS.accent})` }} />
    </AbsoluteFill>
  );
};
