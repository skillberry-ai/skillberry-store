import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, Img, staticFile } from 'remotion';
import { COLORS } from './constants';
import { useSlideUp, ScoreBadge, PluginCard, FeatureBullet } from './components';

// ════════════════════════════════════════
//  SCENE 17 – PLUGINS OVERVIEW  (420 frames, 14s)
// ════════════════════════════════════════
export const ScenePluginsOverview: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [400, 420], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.primary }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', flexDirection: 'column', gap: 28 }}>
        <div style={{ ...useSlideUp(5, 22, 35) }}>
          <div style={{ fontSize: 42, fontWeight: 800, color: COLORS.text }}>Plugin Ecosystem</div>
          <div style={{ fontSize: 22, color: COLORS.textMuted }}>Extensible AI-powered capabilities — install only what you need</div>
        </div>
        <div style={{ flex: 1, ...useSlideUp(20, 35, 50), overflow: 'hidden', borderRadius: 14, boxShadow: '0 20px 60px rgba(0,0,0,0.18)', border: `1px solid ${COLORS.border}` }}>
          <Img src={staticFile('screenshots/sbs2-plugins-populated.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 18 – PLUGIN: CONTENT EVALUATOR  (480 frames, 16s)
// ════════════════════════════════════════
export const ScenePluginEvaluator: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [460, 480], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: '#2E8B57' }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 64, alignItems: 'center' }}>
        {/* Left */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div style={{ ...useSlideUp(5, 25, 40) }}>
            <div style={{ fontSize: 21, fontWeight: 700, color: '#2E8B57', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 12 }}>Plugin: Evaluator</div>
            <div style={{ fontSize: 58, fontWeight: 800, color: COLORS.text, lineHeight: 1.1, marginBottom: 16 }}>Content<br />Evaluator</div>
            <div style={{ fontSize: 24, color: COLORS.textMuted, lineHeight: 1.6 }}>
              Uses LLM to analyse skills and tools, then auto-tags them with <strong>quality</strong>, <strong>security</strong>, and <strong>performance</strong> scores.
            </div>
          </div>

          {/* Animated score bars */}
          <div style={{ ...useSlideUp(60, 20, 30), marginTop: 8 }}>
            <div style={{ fontSize: 20, fontWeight: 600, color: COLORS.textMuted, marginBottom: 14, textTransform: 'uppercase', letterSpacing: '0.1em' }}>summarizer skill — scores</div>
            <ScoreBadge label="Quality" score={9} delay={80} />
            <ScoreBadge label="Performance" score={8} delay={110} />
            <ScoreBadge label="Security" score={8} delay={140} />
          </div>
        </div>

        {/* Right: feature list */}
        <div style={{ flex: 1.1, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[
            { icon: '🏷️', text: 'Returns quality-score:N, performance-score:N, security-score:N tags', delay: 40 },
            { icon: '📝', text: 'Adds a detailed written evaluation for each dimension', delay: 70 },
            { icon: '🎯', text: 'Works on skills, tools, and snippets individually', delay: 100 },
            { icon: '🔁', text: 'Triggered on import or on-demand via the Plugins panel', delay: 130 },
            { icon: '🔌', text: 'Configurable LLM backend (OpenAI / LiteLLM / IBM WatsonX)', delay: 160 },
          ].map((f, i) => <FeatureBullet key={i} icon={f.icon} text={f.text} delay={f.delay} />)}

          {/* Plugin card */}
          <div style={{ marginTop: 8 }}>
            <PluginCard
              name="Content Evaluator"
              description="Evaluate content quality and performance using LLM"
              enabled={true}
              tag="evaluator"
              delay={200}
              highlight={true}
              actionLabel="Evaluate"
            />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 19 – PLUGIN: SECURITY  (480 frames, 16s)
// ════════════════════════════════════════
export const ScenePluginSecurity: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [460, 480], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.danger }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 64, alignItems: 'center' }}>
        {/* Left */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div style={{ ...useSlideUp(5, 25, 40) }}>
            <div style={{ fontSize: 21, fontWeight: 700, color: COLORS.danger, letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 12 }}>Plugin: Security</div>
            <div style={{ fontSize: 58, fontWeight: 800, color: COLORS.text, lineHeight: 1.1, marginBottom: 16 }}>Security<br />Evaluator</div>
            <div style={{ fontSize: 24, color: COLORS.textMuted, lineHeight: 1.6 }}>
              LLM-based security evaluation: finds vulnerabilities, path traversal risks, injection vectors, and missing auth checks — and scores your skill 1–10.
            </div>
          </div>

          {/* Animated score bars */}
          <div style={{ ...useSlideUp(60, 20, 30), marginTop: 8 }}>
            <div style={{ fontSize: 20, fontWeight: 600, color: COLORS.textMuted, marginBottom: 14, textTransform: 'uppercase', letterSpacing: '0.1em' }}>pptx skill — security score</div>
            <ScoreBadge label="Security" score={4} delay={80} />
            <div style={{ opacity: interpolate(frame, [130, 155], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), fontSize: 21, color: COLORS.danger, lineHeight: 1.5, marginTop: 8, padding: '12px 18px', background: COLORS.dangerLight, borderRadius: 8 }}>
              ⚠ No input validation — arbitrary .pptx files accepted. No sandboxing or auth specified. Path-traversal risk.
            </div>
          </div>
        </div>

        {/* Right */}
        <div style={{ flex: 1.1, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[
            { icon: '🔒', text: 'Generates a security-score:N tag (1 = critical, 10 = very safe)', delay: 40 },
            { icon: '📋', text: 'Detailed paragraph explaining specific vulnerabilities found', delay: 70 },
            { icon: '🛡️', text: 'Checks for injection, auth, path traversal, data leakage, CVEs', delay: 100 },
            { icon: '🔬', text: 'SAST companion plugin (Bandit engine) for static code analysis', delay: 130 },
            { icon: '✅', text: 'Score auto-applied as tag — filterable in search and list views', delay: 160 },
          ].map((f, i) => <FeatureBullet key={i} icon={f.icon} text={f.text} delay={f.delay} />)}

          <div style={{ marginTop: 8 }}>
            <PluginCard
              name="Security Evaluator"
              description="Evaluate content security posture using LLM"
              enabled={true}
              tag="evaluator"
              delay={200}
              highlight={true}
              actionLabel="Evaluate Security"
            />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 20 – PLUGIN: DEDUPE  (480 frames, 16s)
// ════════════════════════════════════════
export const ScenePluginDedupe: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [460, 480], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.warning }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 64, alignItems: 'center' }}>
        {/* Left */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div style={{ ...useSlideUp(5, 25, 40) }}>
            <div style={{ fontSize: 21, fontWeight: 700, color: '#B8860B', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 12 }}>Plugin: Dedupe</div>
            <div style={{ fontSize: 58, fontWeight: 800, color: COLORS.text, lineHeight: 1.1, marginBottom: 16 }}>Skill<br />Deduplicator</div>
            <div style={{ fontSize: 24, color: COLORS.textMuted, lineHeight: 1.6 }}>
              Detects semantically duplicate skills using LLM-based comparison. Flags near-copies automatically and lets you decide: keep or delete.
            </div>
          </div>

          {/* Mock decision notification panel */}
          <div style={{ ...useSlideUp(70, 20, 28), marginTop: 4 }}>
            <div style={{ fontSize: 21, fontWeight: 600, color: COLORS.textMuted, marginBottom: 12 }}>Pending duplicate decision</div>
            {[
              { a: 'pptx', b: 'pptx-old', similarity: '94%', delay: 90 },
            ].map((d, i) => (
              <div key={i} style={{
                opacity: interpolate(frame, [d.delay, d.delay + 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
                padding: '18px 22px', background: '#FFF5D4', border: `2px solid ${COLORS.warning}`, borderRadius: 10, fontSize: 22,
              }}>
                <div style={{ fontWeight: 700, marginBottom: 8, color: COLORS.text }}>⚠ Potential duplicate detected</div>
                <div style={{ color: COLORS.textMuted, marginBottom: 12 }}>
                  <span style={{ fontWeight: 600, color: COLORS.text }}>{d.a}</span> and <span style={{ fontWeight: 600, color: COLORS.text }}>{d.b}</span> are <strong>{d.similarity} semantically similar</strong>
                </div>
                <div style={{ display: 'flex', gap: 12 }}>
                  <div style={{ padding: '8px 20px', background: COLORS.primary, color: '#fff', borderRadius: 6, fontSize: 20, fontWeight: 600 }}>Keep Both</div>
                  <div style={{ padding: '8px 20px', background: COLORS.danger, color: '#fff', borderRadius: 6, fontSize: 20, fontWeight: 600 }}>Delete Duplicate</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right */}
        <div style={{ flex: 1.1, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[
            { icon: '🔁', text: 'Uses LLM semantic comparison — not just name matching', delay: 40 },
            { icon: '🏷️', text: "Adds duplicate: tag to near-copies with analysis metadata", delay: 70 },
            { icon: '🔔', text: 'Interactive mode: notification panel with Keep / Delete buttons', delay: 100 },
            { icon: '📡', text: 'Decision management API: /decisions, /keep, /delete', delay: 130 },
            { icon: '🧹', text: 'Keeps your skills library clean and non-redundant', delay: 160 },
          ].map((f, i) => <FeatureBullet key={i} icon={f.icon} text={f.text} delay={f.delay} />)}

          <div style={{ marginTop: 8 }}>
            <PluginCard
              name="Skill Deduplicator"
              description="Detect semantically duplicate skills using LLM and tag them"
              enabled={false}
              tag="evaluator"
              delay={210}
            />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 21 – PLUGIN: CREATOR  (480 frames, 16s)
// ════════════════════════════════════════
export const ScenePluginCreator: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [460, 480], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const tw = (text: string, start: number, fpc = 2) => text.slice(0, Math.max(0, Math.floor((frame - start) / fpc)));

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: COLORS.accent }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 64, alignItems: 'center' }}>
        {/* Left */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ ...useSlideUp(5, 25, 40) }}>
            <div style={{ fontSize: 21, fontWeight: 700, color: '#1A7F64', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 12 }}>Plugin: Creator</div>
            <div style={{ fontSize: 58, fontWeight: 800, color: COLORS.text, lineHeight: 1.1, marginBottom: 16 }}>Snippet<br />Creator</div>
            <div style={{ fontSize: 24, color: COLORS.textMuted, lineHeight: 1.6 }}>
              Describe what you want in plain English — the LLM generates the code, infers metadata (language, tags), and saves it directly to the store.
            </div>
          </div>

          {/* Mock input → output flow */}
          <div style={{ ...useSlideUp(60, 20, 28), display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 21, fontWeight: 600, color: COLORS.textMuted, marginBottom: 4 }}>Example flow</div>
            <div style={{ padding: '14px 18px', background: COLORS.bgAlt, borderRadius: 8, border: `1px solid ${COLORS.border}`, fontSize: 22, color: COLORS.text, lineHeight: 1.5 }}>
              <span style={{ color: COLORS.primary, fontWeight: 600 }}>Description:</span> "A Python function that converts a list of dicts to a Markdown table"
            </div>
            {frame >= 140 && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28, color: COLORS.primary }}>↓ LLM generates</div>
            )}
            {frame >= 160 && (
              <div style={{ padding: '14px 18px', background: COLORS.codeBg, borderRadius: 8, fontFamily: 'monospace', fontSize: 20, color: '#9CDCFE', lineHeight: 1.7 }}>
                <div style={{ color: '#6A9955' }}># Auto-generated by Creator plugin</div>
                <div>{tw('def dicts_to_markdown_table(data: list[dict]) -> str:', 165, 3)}</div>
                {frame >= 230 && <div style={{ color: '#CE9178', paddingLeft: 16 }}>{tw("    '''Convert list of dicts → Markdown table'''", 230, 3)}</div>}
                {frame >= 280 && <div style={{ paddingLeft: 16 }}>{tw('    headers = data[0].keys()', 280, 3)}</div>}
                {frame >= 330 && <div style={{ paddingLeft: 16, color: '#6A9955' }}>    ...</div>}
              </div>
            )}
          </div>
        </div>

        {/* Right */}
        <div style={{ flex: 1.1, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[
            { icon: '✍️', text: 'Natural language description → production-ready code snippet', delay: 40 },
            { icon: '🏷️', text: 'Automatically infers programming language, purpose, and tags', delay: 70 },
            { icon: '💾', text: 'Created snippet is saved directly to the Skillberry Store', delay: 100 },
            { icon: '🔌', text: 'LLM-agnostic — works with OpenAI, LiteLLM, IBM WatsonX', delay: 130 },
            { icon: '⚡', text: 'Eliminates boilerplate: describe once, reuse forever', delay: 160 },
          ].map((f, i) => <FeatureBullet key={i} icon={f.icon} text={f.text} delay={f.delay} />)}

          <div style={{ marginTop: 8 }}>
            <PluginCard
              name="Snippet Creator"
              description="Create code snippets using LLM from natural language descriptions"
              enabled={false}
              tag="creator"
              delay={200}
            />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════
//  SCENE 22 – PLUGIN: SKILL OPTIMIZER  (480 frames, 16s)
// ════════════════════════════════════════
export const ScenePluginOptimizer: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [460, 480], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: fadeIn * fadeOut, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 6, background: '#7B5CD8' }} />
      <div style={{ position: 'absolute', inset: 0, padding: '60px 80px', display: 'flex', gap: 64, alignItems: 'center' }}>
        {/* Left */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ ...useSlideUp(5, 25, 40) }}>
            <div style={{ fontSize: 21, fontWeight: 700, color: '#7B5CD8', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 12 }}>Plugin: Optimizer</div>
            <div style={{ fontSize: 58, fontWeight: 800, color: COLORS.text, lineHeight: 1.1, marginBottom: 16 }}>Skill<br />Optimizer</div>
            <div style={{ fontSize: 24, color: COLORS.textMuted, lineHeight: 1.6 }}>
              Exports a skill to a temp directory, launches a <strong>Claude Code RunSpace</strong> session, applies optimizations, then imports the result as a new versioned skill.
            </div>
          </div>

          {/* Flow diagram */}
          <div style={{ ...useSlideUp(65, 20, 28) }}>
            {[
              { step: '1', label: 'Export skill to temp dir', delay: 75 },
              { step: '2', label: 'Claude Code optimizes in RunSpace container', delay: 105 },
              { step: '3', label: 'Import as <name>_optimized with rationale tags', delay: 135 },
            ].map((s, i) => (
              <div key={i} style={{
                opacity: interpolate(frame, [s.delay, s.delay + 18], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
                display: 'flex', alignItems: 'center', gap: 16, marginBottom: 14,
              }}>
                <div style={{ width: 40, height: 40, borderRadius: '50%', background: '#7B5CD8', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 20, fontWeight: 700, flexShrink: 0 }}>{s.step}</div>
                <span style={{ fontSize: 24, color: COLORS.text, lineHeight: 1.4 }}>{s.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right */}
        <div style={{ flex: 1.1, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[
            { icon: '🤖', text: 'Powered by Claude Code in an isolated container (RunSpace)', delay: 40 },
            { icon: '📝', text: 'Records optimization rationale, changes made, and issues addressed', delay: 70 },
            { icon: '🔗', text: 'Links optimized skill back to source via UUID metadata', delay: 100 },
            { icon: '🔄', text: 'Re-running is safe — auto-handles name collision', delay: 130 },
            { icon: '🖥️', text: 'Also supports local mode (no Docker) for development', delay: 160 },
          ].map((f, i) => <FeatureBullet key={i} icon={f.icon} text={f.text} delay={f.delay} />)}

          <div style={{ marginTop: 8 }}>
            <PluginCard
              name="Skill Optimizer"
              description="Optimize existing skills using RunSpace-powered Claude Code"
              enabled={true}
              tag="optimizer"
              delay={200}
              highlight={true}
              actionLabel="Optimize Skill"
            />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
