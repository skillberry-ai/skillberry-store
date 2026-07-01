import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, Img, staticFile } from 'remotion';
import { COLORS } from './constants';
import { useSlideUp, Tag } from './components';

// ════════════════════════════════════════
//  SCENE 04 – CLI INTRO  (540 frames, 18s)
// ════════════════════════════════════════
export const SceneCLIIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [520, 540], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const L = (color: string, text: string) => <span style={{ color }}>{text}</span>;

  const helpText = [
    { start: 40, text: '$ sbs --help', color: '#569CD6' },
    { start: 70, text: 'http://localhost:8000', color: '#8A8A8A', indent: true },
    { start: 85, text: '', color: '' },
    { start: 90, text: 'Usage: sbs [command]', color: '#D4D4D4' },
    { start: 100, text: '', color: '' },
    { start: 105, text: 'Skills Commands:', color: '#DCDCAA', bold: true },
    { start: 115, text: '  list-skills   import-anthropic-skill   export-anthropic-skill', color: '#9CDCFE', indent: false },
    { start: 140, text: '', color: '' },
    { start: 145, text: 'Tools Commands:', color: '#DCDCAA', bold: true },
    { start: 155, text: '  list-tools   get-tool   execute-tool   search-tools', color: '#9CDCFE' },
    { start: 180, text: '', color: '' },
    { start: 185, text: 'VMCP / vNFS / Plugins / Admin  ...', color: '#6A9955' },
  ];

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />

      <div style={{ position: 'absolute', inset: 0, padding: '72px 120px', display: 'flex', gap: 80, alignItems: 'flex-start' }}>
        {/* Left */}
        <div style={{ flex: '0 0 460px', paddingTop: 40 }}>
          <div style={{ ...useSlideUp(5, 25, 40) }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: COLORS.primary, letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 14 }}>CLI</div>
            <div style={{ fontSize: 62, fontWeight: 800, color: COLORS.text, lineHeight: 1.1, marginBottom: 24 }}>Command Line Interface</div>
            <div style={{ fontSize: 26, color: COLORS.textMuted, lineHeight: 1.6 }}>Auto-generated from the OpenAPI spec via <strong>restish</strong>. Every REST operation is available as a single <code style={{ background: COLORS.bgAlt, padding: '2px 8px', borderRadius: 4 }}>sbs</code> command.</div>
          </div>

          <div style={{ marginTop: 32, ...useSlideUp(60, 20, 30) }}>
            <div style={{ fontSize: 21, fontWeight: 600, marginBottom: 12, color: COLORS.text }}>Install</div>
            <div style={{ background: COLORS.codeBg, borderRadius: 8, padding: '14px 20px', fontFamily: 'monospace', fontSize: 22, color: '#CE9178' }}>
              pip install skillberry-store-sdk
            </div>
          </div>

          <div style={{ marginTop: 24, ...useSlideUp(100, 20, 30) }}>
            <div style={{ fontSize: 21, fontWeight: 600, marginBottom: 12, color: COLORS.text }}>Connect to a server</div>
            <div style={{ background: COLORS.codeBg, borderRadius: 8, padding: '14px 20px', fontFamily: 'monospace', fontSize: 22, color: '#9CDCFE' }}>
              sbs connect http://prod:8000
            </div>
          </div>
        </div>

        {/* Right – terminal */}
        <div style={{ flex: 1, ...useSlideUp(20, 30, 50), paddingTop: 20 }}>
          <div style={{
            borderRadius: 10, overflow: 'hidden', background: COLORS.codeBg,
            boxShadow: '0 20px 60px rgba(0,0,0,0.4)', border: '1px solid #333',
          }}>
            <div style={{ background: '#2D2D2D', padding: '11px 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ display: 'flex', gap: 7 }}>
                {['#FF5F57','#FFBD2E','#28CA42'].map((c, i) => <div key={i} style={{ width: 14, height: 14, borderRadius: '50%', background: c }} />)}
              </div>
              <span style={{ flex: 1, textAlign: 'center', fontSize: 14, color: '#8A8A8A', fontFamily: 'monospace' }}>bash — sbs</span>
            </div>
            <div style={{ padding: '24px 28px', fontFamily: "'JetBrains Mono', monospace", fontSize: 23, lineHeight: 1.8 }}>
              {helpText.map((line, i) => (
                frame >= line.start ? (
                  <div key={i} style={{ color: line.color || 'transparent', fontWeight: (line as any).bold ? 600 : 400, minHeight: '1.8em' }}>
                    {line.text}
                  </div>
                ) : null
              ))}
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 05 – CLI IMPORT  (480 frames, 16s)
// ════════════════════════════════════════
export const SceneCLIImport: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [460, 480], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const tw = (text: string, start: number, fpc = 2) => text.slice(0, Math.max(0, Math.floor((frame - start) / fpc)));

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />

      <div style={{ position: 'absolute', inset: 0, padding: '72px 120px', display: 'flex', gap: 80, alignItems: 'center' }}>
        {/* Left */}
        <div style={{ flex: '0 0 480px' }}>
          <div style={{ ...useSlideUp(5, 25, 40) }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: COLORS.primary, letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 14 }}>CLI Import</div>
            <div style={{ fontSize: 62, fontWeight: 800, color: COLORS.text, lineHeight: 1.1, marginBottom: 24 }}>Importing an Anthropic Skill</div>
            <div style={{ fontSize: 26, color: COLORS.textMuted, lineHeight: 1.6 }}>
              Three import paths: <strong>GitHub URL</strong>, <strong>ZIP file</strong>, or <strong>local folder</strong>. We'll use the PPTX skill from a local directory.
            </div>
          </div>
          <div style={{ marginTop: 28, ...useSlideUp(50, 20, 30) }}>
            <div style={{ fontSize: 21, color: COLORS.textMuted, marginBottom: 6 }}>Source path</div>
            <div style={{ background: COLORS.codeBg, borderRadius: 8, padding: '12px 18px', fontFamily: 'monospace', fontSize: 21, color: '#CE9178', wordBreak: 'break-all' }}>
              /mnt/c/.../Downloads/pptx
            </div>
          </div>
        </div>

        {/* Right – terminal showing API import */}
        <div style={{ flex: 1, ...useSlideUp(20, 30, 50) }}>
          <div style={{
            borderRadius: 10, overflow: 'hidden', background: COLORS.codeBg,
            boxShadow: '0 20px 60px rgba(0,0,0,0.4)', border: '1px solid #333',
          }}>
            <div style={{ background: '#2D2D2D', padding: '11px 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
              {['#FF5F57','#FFBD2E','#28CA42'].map((c, i) => <div key={i} style={{ width: 14, height: 14, borderRadius: '50%', background: c }} />)}
              <span style={{ flex: 1, textAlign: 'center', fontSize: 14, color: '#8A8A8A', fontFamily: 'monospace' }}>bash</span>
            </div>
            <div style={{ padding: '24px 28px', fontFamily: "'JetBrains Mono', monospace", fontSize: 23, lineHeight: 1.85 }}>
              {frame >= 30 && <div style={{ color: '#6A9955' }}># Import via local folder</div>}
              {frame >= 45 && <div style={{ color: '#569CD6' }}>$ <span style={{ color: '#CE9178' }}>{tw('curl -s -X POST \\', 45)}</span></div>}
              {frame >= 95 && <div style={{ color: '#CE9178', paddingLeft: 16 }}>  {tw('"http://localhost:8000/skills/import-anthropic" \\', 95)}</div>}
              {frame >= 160 && <div style={{ color: '#9CDCFE', paddingLeft: 16 }}>  {tw('-F "source_type=folder" \\', 160)}</div>}
              {frame >= 200 && <div style={{ color: '#9CDCFE', paddingLeft: 16 }}>  {tw('-F "folder_path=/mnt/.../pptx"', 200)}</div>}
              {frame >= 280 && (
                <div style={{ marginTop: 16 }}>
                  <div style={{ color: '#6A9955' }}>✓  Import successful</div>
                  {frame >= 300 && <div style={{ color: '#D4D4D4', fontSize: 22, marginTop: 8 }}>{'{'}</div>}
                  {frame >= 310 && <div style={{ color: '#9CDCFE', paddingLeft: 16, fontSize: 22 }}>"skill_name": <span style={{ color: '#CE9178' }}>"pptx"</span>,</div>}
                  {frame >= 320 && <div style={{ color: '#9CDCFE', paddingLeft: 16, fontSize: 22 }}>"tools_created": <span style={{ color: '#B5CEA8' }}>66</span>,</div>}
                  {frame >= 330 && <div style={{ color: '#9CDCFE', paddingLeft: 16, fontSize: 22 }}>"snippets_created": <span style={{ color: '#B5CEA8' }}>43</span></div>}
                  {frame >= 340 && <div style={{ color: '#D4D4D4', fontSize: 22 }}>{'}'}</div>}
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
//  SCENE 06 – UI HOME  (300 frames, 10s)
// ════════════════════════════════════════
export const SceneUIHome: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [280, 300], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const imgScale = interpolate(frame, [20, 60], [1.04, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />

      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', flexDirection: 'column', gap: 32 }}>
        {/* Title */}
        <div style={{ ...useSlideUp(5, 22, 35), display: 'flex', alignItems: 'center', gap: 24 }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: COLORS.primary, letterSpacing: '0.14em', textTransform: 'uppercase' }}>Web UI</div>
          <div style={{ fontSize: 42, fontWeight: 800, color: COLORS.text }}>The Skillberry Store Dashboard</div>
          <div style={{ marginLeft: 'auto', padding: '8px 20px', background: COLORS.primaryLight, borderRadius: 8, fontSize: 20, color: COLORS.primary, fontFamily: 'monospace' }}>localhost:8002</div>
        </div>

        {/* Screenshot */}
        <div style={{ flex: 1, ...useSlideUp(15, 30, 40), overflow: 'hidden', borderRadius: 14, boxShadow: '0 24px 80px rgba(0,0,0,0.2)', border: `1px solid ${COLORS.border}` }}>
          <Img
            src={staticFile('screenshots/sbs-home.png')}
            style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top', transform: `scale(${imgScale})`, transformOrigin: 'top left' }}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};
