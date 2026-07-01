import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, Img, staticFile } from 'remotion';
import { COLORS } from './constants';
import { useSlideUp, Tag } from './components';

// ════════════════════════════════════════
//  SCENE 11 – UI TOOLS  (480 frames, 16s)
// ════════════════════════════════════════
export const SceneUITools: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [460, 480], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', flexDirection: 'column', gap: 28 }}>
        <div style={{ ...useSlideUp(5, 22, 35) }}>
          <div style={{ fontSize: 42, fontWeight: 800, color: COLORS.text }}>Tools Registry</div>
          <div style={{ fontSize: 22, color: COLORS.textMuted }}>95 tools across 2 skills — sortable, filterable, executable</div>
        </div>
        <div style={{ flex: 1, ...useSlideUp(20, 35, 50), overflow: 'hidden', borderRadius: 14, boxShadow: '0 20px 60px rgba(0,0,0,0.18)', border: `1px solid ${COLORS.border}` }}>
          <Img src={staticFile('screenshots/sbs2-tools-populated.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 12 – TOOL DETAIL  (390 frames, 13s)
// ════════════════════════════════════════
export const SceneToolDetail: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [370, 390], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', flexDirection: 'column', gap: 28 }}>
        <div style={{ ...useSlideUp(5, 22, 35) }}>
          <div style={{ fontSize: 42, fontWeight: 800, color: COLORS.text }}>Tool Detail — create_bullet_summary</div>
          <div style={{ fontSize: 22, color: COLORS.textMuted }}>Full metadata: state, tags, module name, dependencies, parameter schema</div>
        </div>
        <div style={{ flex: 1, ...useSlideUp(20, 35, 50), overflow: 'hidden', borderRadius: 14, boxShadow: '0 20px 60px rgba(0,0,0,0.18)', border: `1px solid ${COLORS.border}` }}>
          <Img src={staticFile('screenshots/sbs3-tool-detail-create-bullet-summary.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 13 – TOOL EXECUTE  (480 frames, 16s)
// ════════════════════════════════════════
export const SceneToolExecute: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [460, 480], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const tw = (text: string, start: number, fpc = 2) => text.slice(0, Math.max(0, Math.floor((frame - start) / fpc)));

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 64, alignItems: 'center' }}>
        {/* Left: screenshot */}
        <div style={{ flex: 1.1, height: '85%', ...useSlideUp(10, 35, 50), overflow: 'hidden', borderRadius: 14, boxShadow: '0 20px 60px rgba(0,0,0,0.18)', border: `1px solid ${COLORS.border}` }}>
          <Img src={staticFile('screenshots/sbs3-tool-execute-dialog.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
        </div>
        {/* Right: CLI execution + result */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 24, height: '85%', justifyContent: 'center' }}>
          <div style={{ ...useSlideUp(5, 22, 35) }}>
            <div style={{ fontSize: 36, fontWeight: 800, color: COLORS.text, marginBottom: 8 }}>Execute a Tool</div>
            <div style={{ fontSize: 22, color: COLORS.textMuted, lineHeight: 1.5 }}>Tools run sandboxed in Docker. Pass parameters as JSON — via UI dialog or the CLI.</div>
          </div>
          {/* CLI execution */}
          <div style={{ ...useSlideUp(50, 25, 35) }}>
            <div style={{ borderRadius: 10, overflow: 'hidden', background: COLORS.codeBg, border: '1px solid #333' }}>
              <div style={{ background: '#2D2D2D', padding: '10px 14px', display: 'flex', gap: 7 }}>
                {['#FF5F57','#FFBD2E','#28CA42'].map((c, i) => <div key={i} style={{ width: 13, height: 13, borderRadius: '50%', background: c }} />)}
              </div>
              <div style={{ padding: '20px 24px', fontFamily: 'monospace', fontSize: 22, lineHeight: 1.8 }}>
                {frame >= 60 && <div style={{ color: '#569CD6' }}>$ <span style={{ color: '#CE9178' }}>{tw('sbs execute-tool create_bullet_summary \\', 60, 3)}</span></div>}
                {frame >= 120 && <div style={{ color: '#9CDCFE', paddingLeft: 16 }}>{tw("--body='{\"params\":{\"text\":\"<article>\"}}'", 120, 3)}</div>}
                {frame >= 220 && <div style={{ marginTop: 12, color: '#6A9955' }}>✓ Execution complete (1.2s)</div>}
                {frame >= 240 && (
                  <div style={{ marginTop: 8, color: '#D4D4D4', fontSize: 20 }}>
                    <div>{'{'}</div>
                    <div style={{ paddingLeft: 16 }}>"result": [</div>
                    <div style={{ paddingLeft: 32, color: '#CE9178' }}>"Summarizer provides extractive &amp; abstractive techniques",</div>
                    <div style={{ paddingLeft: 32, color: '#CE9178' }}>"Multiple output formats: bullets, executive, structured",</div>
                    <div style={{ paddingLeft: 32, color: '#CE9178' }}>"Python helper scripts for automated processing"</div>
                    <div style={{ paddingLeft: 16 }}>]</div>
                    <div>{'}'}</div>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div style={{ ...useSlideUp(280, 20, 28), padding: '14px 20px', background: COLORS.primaryLight, borderRadius: 8, fontSize: 22, color: COLORS.primary, lineHeight: 1.5 }}>
            Docker sandbox — zero host contamination. Each tool runs in an isolated container.
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 14 – UI SNIPPETS  (300 frames, 10s)
// ════════════════════════════════════════
export const SceneUISnippets: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [280, 300], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', flexDirection: 'column', gap: 28 }}>
        <div style={{ ...useSlideUp(5, 22, 35) }}>
          <div style={{ fontSize: 42, fontWeight: 800, color: COLORS.text }}>Snippets</div>
          <div style={{ fontSize: 22, color: COLORS.textMuted }}>Store and reuse code snippets with syntax highlighting</div>
        </div>
        <div style={{ flex: 1, ...useSlideUp(20, 35, 50), overflow: 'hidden', borderRadius: 14, boxShadow: '0 20px 60px rgba(0,0,0,0.18)', border: `1px solid ${COLORS.border}` }}>
          <Img src={staticFile('screenshots/sbs2-snippets-populated.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 15 – VMCP  (330 frames, 11s)
// ════════════════════════════════════════
export const SceneVMCP: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [310, 330], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 60, alignItems: 'center' }}>
        <div style={{ flex: 1, ...useSlideUp(20, 35, 50), overflow: 'hidden', borderRadius: 14, boxShadow: '0 20px 60px rgba(0,0,0,0.18)', border: `1px solid ${COLORS.border}` }}>
          <Img src={staticFile('screenshots/sbs-vmcp.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 20 }}>
          <div style={{ ...useSlideUp(5, 25, 40) }}>
            <div style={{ fontSize: 42, fontWeight: 800, color: COLORS.text, marginBottom: 12 }}>Virtual MCP Servers</div>
            <div style={{ fontSize: 24, color: COLORS.textMuted, lineHeight: 1.6 }}>Expose a specific skill's tools as a standalone MCP endpoint. Each vMCP gets its own port and SSE URL — plug it into Claude, Cursor, or any MCP client.</div>
          </div>
          <div style={{ ...useSlideUp(60, 20, 30), background: COLORS.codeBg, borderRadius: 8, padding: '16px 20px', fontFamily: 'monospace', fontSize: 21, color: '#CE9178' }}>
            http://localhost:&lt;port&gt;/sse
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 16 – VNFS  (300 frames, 10s)
// ════════════════════════════════════════
export const SceneVNFS: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [280, 300], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 60, alignItems: 'center' }}>
        <div style={{ flex: 1, ...useSlideUp(20, 35, 50), overflow: 'hidden', borderRadius: 14, boxShadow: '0 20px 60px rgba(0,0,0,0.18)', border: `1px solid ${COLORS.border}` }}>
          <Img src={staticFile('screenshots/sbs-vnfs.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 20 }}>
          <div style={{ ...useSlideUp(5, 25, 40) }}>
            <div style={{ fontSize: 42, fontWeight: 800, color: COLORS.text, marginBottom: 12 }}>Virtual NFS Servers</div>
            <div style={{ fontSize: 24, color: COLORS.textMuted, lineHeight: 1.6 }}>Mount a skill as a read-only filesystem over <strong>WebDAV</strong> or <strong>NFSv3</strong>. Claude Code and other tools can read skill files directly via <code>rclone mount</code> or <code>davfs2</code> — no REST API needed.</div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
