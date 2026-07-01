import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, Img, staticFile } from 'remotion';
import { COLORS } from './constants';
import { useSlideUp, Tag } from './components';

// ════════════════════════════════════════
//  SCENE 07 – UI SKILLS (420 frames, 14s)
// ════════════════════════════════════════
export const SceneUISkills: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [400, 420], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', flexDirection: 'column', gap: 28 }}>
        <div style={{ ...useSlideUp(5, 22, 35), display: 'flex', alignItems: 'center', gap: 24 }}>
          <div style={{ fontSize: 42, fontWeight: 800, color: COLORS.text }}>Skills Library</div>
          <div style={{ fontSize: 22, color: COLORS.textMuted, marginLeft: 8 }}>— Organize tools &amp; snippets into reusable packages</div>
        </div>
        {/* Two-pane: screenshot left, callouts right */}
        <div style={{ flex: 1, display: 'flex', gap: 48 }}>
          <div style={{ flex: 1.4, ...useSlideUp(15, 30, 40), overflow: 'hidden', borderRadius: 14, boxShadow: '0 20px 60px rgba(0,0,0,0.18)', border: `1px solid ${COLORS.border}` }}>
            <Img src={staticFile('screenshots/sbs2-skills-populated.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
          </div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 20, paddingLeft: 20 }}>
            {[
              { title: 'pptx', tools: 66, snippets: 43, tags: ['anthropic','imported','quality-score:8'], delay: 40 },
              { title: 'summarizer', tools: 29, snippets: 2, tags: ['anthropic','imported','security-score:8'], delay: 80 },
            ].map((skill, i) => (
              <div key={i} style={{
                opacity: interpolate(frame, [skill.delay, skill.delay + 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
                transform: `translateY(${interpolate(frame, [skill.delay, skill.delay + 25], [25, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })}px)`,
                border: `2px solid ${COLORS.border}`, borderRadius: 12, padding: '24px 28px', background: COLORS.bgAlt,
              }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: COLORS.text, marginBottom: 8 }}>{skill.title}</div>
                <div style={{ display: 'flex', gap: 24, marginBottom: 12 }}>
                  <span style={{ fontSize: 22, color: COLORS.textMuted }}>🔧 {skill.tools} tools</span>
                  <span style={{ fontSize: 22, color: COLORS.textMuted }}>📄 {skill.snippets} snippets</span>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {skill.tags.map((t, j) => <Tag key={j} label={t} />)}
                </div>
              </div>
            ))}
            <div style={{ opacity: interpolate(frame, [140, 160], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), fontSize: 24, color: COLORS.textMuted, lineHeight: 1.6, paddingLeft: 8 }}>
              Skills are auto-tagged with quality, security, and performance scores from the evaluator plugin.
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 08 – IMPORT DIALOG  (540 frames, 18s)
// ════════════════════════════════════════
export const SceneImportDialog: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [520, 540], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', flexDirection: 'column', gap: 28 }}>
        <div style={{ ...useSlideUp(5, 22, 35), display: 'flex', alignItems: 'center', gap: 24 }}>
          <div style={{ fontSize: 42, fontWeight: 800, color: COLORS.text }}>Import Anthropic Skill</div>
          <div style={{ fontSize: 22, color: COLORS.textMuted }}>— via the UI Import dialog</div>
        </div>
        <div style={{ flex: 1, display: 'flex', gap: 64, alignItems: 'center' }}>
          {/* Left: screenshot of dialog */}
          <div style={{ flex: 1.1, ...useSlideUp(20, 30, 40), overflow: 'hidden', borderRadius: 14, boxShadow: '0 20px 60px rgba(0,0,0,0.2)', border: `1px solid ${COLORS.border}` }}>
            <Img src={staticFile('screenshots/sbs-import-local-folder.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
          </div>
          {/* Right: import sources explained */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 20 }}>
            {[
              { icon: '🔗', title: 'GitHub URL', desc: 'Point to any Anthropic skills repo folder — e.g. github.com/anthropics/skills/tree/main/skills/pptx', delay: 40 },
              { icon: '📦', title: 'ZIP File', desc: 'Upload a .zip archive of the skill directory — great for air-gapped environments', delay: 80 },
              { icon: '📁', title: 'Local Folder', desc: 'Provide an absolute path on the server host — ideal for CI/CD pipelines', delay: 120 },
            ].map((src, i) => (
              <div key={i} style={{
                opacity: interpolate(frame, [src.delay, src.delay + 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
                transform: `translateX(${interpolate(frame, [src.delay, src.delay + 22], [30, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })}px)`,
                display: 'flex', gap: 18, alignItems: 'flex-start',
                padding: '18px 22px', borderRadius: 10, background: COLORS.bgAlt, border: `1px solid ${COLORS.border}`,
              }}>
                <span style={{ fontSize: 32 }}>{src.icon}</span>
                <div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: COLORS.text, marginBottom: 6 }}>{src.title}</div>
                  <div style={{ fontSize: 21, color: COLORS.textMuted, lineHeight: 1.5 }}>{src.desc}</div>
                </div>
              </div>
            ))}
            <div style={{ opacity: interpolate(frame, [200, 220], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), padding: '16px 22px', background: COLORS.successLight, borderRadius: 10, border: `1px solid ${COLORS.success}40` }}>
              <span style={{ fontSize: 22, color: COLORS.success, fontWeight: 600 }}>✓ Result: 66 tools + 43 snippets imported in one click</span>
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 09 – IMPORT RESULT  (420 frames, 14s)
// ════════════════════════════════════════
export const SceneImportResult: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [400, 420], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', flexDirection: 'column', gap: 28 }}>
        <div style={{ ...useSlideUp(5, 22, 35) }}>
          <div style={{ fontSize: 42, fontWeight: 800, color: COLORS.text }}>Skill Detail — pptx</div>
          <div style={{ fontSize: 22, color: COLORS.textMuted, marginTop: 4 }}>66 tools · 43 snippets · auto-tagged · version 1.0.0</div>
        </div>
        <div style={{ flex: 1, ...useSlideUp(20, 35, 50), overflow: 'hidden', borderRadius: 14, boxShadow: '0 20px 60px rgba(0,0,0,0.18)', border: `1px solid ${COLORS.border}` }}>
          <Img src={staticFile('screenshots/sbs2-skill-pptx-detail.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 10 – SKILL DETAIL  (420 frames, 14s)
// ════════════════════════════════════════
export const SceneSkillDetail: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [400, 420], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', flexDirection: 'column', gap: 28 }}>
        <div style={{ ...useSlideUp(5, 22, 35) }}>
          <div style={{ fontSize: 42, fontWeight: 800, color: COLORS.text }}>Skill Detail — summarizer</div>
        </div>
        <div style={{ flex: 1, ...useSlideUp(20, 35, 50), overflow: 'hidden', borderRadius: 14, boxShadow: '0 20px 60px rgba(0,0,0,0.18)', border: `1px solid ${COLORS.border}` }}>
          <Img src={staticFile('screenshots/sbs2-skill-summarizer-detail.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
