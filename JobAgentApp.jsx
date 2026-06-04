import { useState, useEffect, useRef, useCallback } from "react";

const API = "http://localhost:8000";

// ─── Styles ──────────────────────────────────────────────────────────────────
const css = `
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #0a0b0f;
    --surface: #111318;
    --surface2: #1a1d26;
    --border: #232636;
    --accent: #4f8bff;
    --accent2: #7c3aed;
    --green: #10b981;
    --red: #ef4444;
    --amber: #f59e0b;
    --text: #e8eaf0;
    --muted: #6b7280;
    --mono: 'JetBrains Mono', monospace;
    --sans: 'Syne', sans-serif;
  }

  body { background: var(--bg); color: var(--text); font-family: var(--sans); min-height: 100vh; }

  .app { display: flex; min-height: 100vh; }

  /* Sidebar */
  .sidebar {
    width: 220px; min-width: 220px; background: var(--surface);
    border-right: 1px solid var(--border); padding: 28px 16px;
    display: flex; flex-direction: column; gap: 8px; position: sticky; top: 0; height: 100vh;
  }
  .logo { font-size: 18px; font-weight: 800; color: var(--text); padding: 0 8px 24px;
    display: flex; align-items: center; gap: 10px; letter-spacing: -0.5px; }
  .logo-icon { width: 32px; height: 32px; background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; }
  .nav-btn { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px;
    border: none; background: transparent; color: var(--muted); font-family: var(--sans); font-size: 14px;
    font-weight: 600; cursor: pointer; transition: all 0.15s; text-align: left; width: 100%; }
  .nav-btn:hover { background: var(--surface2); color: var(--text); }
  .nav-btn.active { background: rgba(79, 139, 255, 0.12); color: var(--accent); }
  .nav-divider { border: none; border-top: 1px solid var(--border); margin: 8px 0; }

  /* Main */
  .main { flex: 1; padding: 40px 48px; overflow-y: auto; }
  .page-title { font-size: 28px; font-weight: 800; letter-spacing: -1px; margin-bottom: 8px; }
  .page-sub { color: var(--muted); font-size: 14px; margin-bottom: 32px; }

  /* Cards */
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 24px; }
  .card-title { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px;
    color: var(--muted); margin-bottom: 16px; }

  /* Steps */
  .steps { display: flex; gap: 0; margin-bottom: 40px; }
  .step { display: flex; align-items: center; gap: 10px; flex: 1; }
  .step-num { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center;
    justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }
  .step.done .step-num { background: var(--green); color: #fff; }
  .step.active .step-num { background: var(--accent); color: #fff; }
  .step.idle .step-num { background: var(--surface2); color: var(--muted); border: 1px solid var(--border); }
  .step-label { font-size: 13px; font-weight: 600; }
  .step.active .step-label { color: var(--text); }
  .step.idle .step-label { color: var(--muted); }
  .step.done .step-label { color: var(--green); }
  .step-line { flex: 1; height: 1px; background: var(--border); margin: 0 8px; }

  /* Upload Zone */
  .upload-zone { border: 2px dashed var(--border); border-radius: 12px; padding: 48px;
    text-align: center; cursor: pointer; transition: all 0.2s; }
  .upload-zone:hover, .upload-zone.drag { border-color: var(--accent);
    background: rgba(79, 139, 255, 0.04); }
  .upload-icon { font-size: 40px; margin-bottom: 16px; }
  .upload-title { font-size: 16px; font-weight: 700; margin-bottom: 8px; }
  .upload-sub { font-size: 13px; color: var(--muted); }

  /* Profile card */
  .profile-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .profile-field label { display: block; font-size: 11px; color: var(--muted); text-transform: uppercase;
    letter-spacing: 1px; margin-bottom: 6px; }
  .profile-field p { font-size: 14px; font-weight: 600; }
  .skill-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
  .tag { background: rgba(79, 139, 255, 0.1); color: var(--accent); border: 1px solid rgba(79,139,255,0.2);
    padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }

  /* Form controls */
  .form-group { margin-bottom: 20px; }
  .form-group label { display: block; font-size: 12px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: var(--muted); margin-bottom: 8px; }
  .form-input { width: 100%; background: var(--surface2); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 14px; color: var(--text); font-family: var(--sans); font-size: 14px; }
  .form-input:focus { outline: none; border-color: var(--accent); }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

  /* Tag input */
  .tag-input-wrap { display: flex; flex-wrap: wrap; gap: 6px; background: var(--surface2);
    border: 1px solid var(--border); border-radius: 8px; padding: 8px; min-height: 44px; }
  .tag-input-wrap input { background: transparent; border: none; outline: none; color: var(--text);
    font-family: var(--sans); font-size: 14px; flex: 1; min-width: 120px; }
  .tag-x { background: rgba(239,68,68,0.15); color: var(--red); border: none; cursor: pointer;
    border-radius: 999px; width: 16px; height: 16px; display: inline-flex; align-items: center;
    justify-content: center; font-size: 10px; font-weight: 700; margin-left: 4px; }

  /* Portals */
  .portal-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
  .portal-card { border: 1.5px solid var(--border); border-radius: 10px; padding: 16px;
    cursor: pointer; transition: all 0.15s; text-align: center; }
  .portal-card:hover { border-color: var(--accent); }
  .portal-card.selected { border-color: var(--accent); background: rgba(79,139,255,0.08); }
  .portal-logo { font-size: 28px; margin-bottom: 8px; }
  .portal-name { font-size: 13px; font-weight: 700; }
  .portal-badge { font-size: 10px; color: var(--green); font-weight: 600; margin-top: 4px; }

  /* Buttons */
  .btn { padding: 11px 22px; border-radius: 8px; font-family: var(--sans); font-size: 14px;
    font-weight: 700; cursor: pointer; border: none; transition: all 0.15s; }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover { background: #6b9fff; }
  .btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-ghost { background: var(--surface2); color: var(--text); border: 1px solid var(--border); }
  .btn-ghost:hover { border-color: var(--accent); color: var(--accent); }
  .btn-success { background: var(--green); color: #fff; font-size: 16px; padding: 14px 32px; }
  .btn-success:hover { background: #0ea472; }

  /* Status grid */
  .stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }
  .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 20px; }
  .stat-num { font-size: 36px; font-weight: 800; letter-spacing: -2px; }
  .stat-label { font-size: 12px; color: var(--muted); margin-top: 4px; text-transform: uppercase;
    letter-spacing: 1px; font-weight: 600; }
  .stat-card.blue .stat-num { color: var(--accent); }
  .stat-card.green .stat-num { color: var(--green); }
  .stat-card.amber .stat-num { color: var(--amber); }
  .stat-card.red .stat-num { color: var(--red); }

  /* Agent log */
  .log-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 0; overflow: hidden; margin-bottom: 24px; }
  .log-header { padding: 14px 20px; border-bottom: 1px solid var(--border); display: flex;
    align-items: center; justify-content: space-between; }
  .log-title { font-size: 13px; font-weight: 700; }
  .log-body { padding: 16px 20px; max-height: 280px; overflow-y: auto; font-family: var(--mono);
    font-size: 12px; }
  .log-entry { display: flex; gap: 10px; margin-bottom: 6px; line-height: 1.5; }
  .log-ts { color: var(--muted); flex-shrink: 0; }
  .log-msg.info { color: var(--text); }
  .log-msg.success { color: var(--green); }
  .log-msg.warning { color: var(--amber); }
  .log-msg.error { color: var(--red); }

  /* Application cards */
  .app-list { display: flex; flex-direction: column; gap: 12px; }
  .app-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 18px 22px; display: flex; align-items: center; gap: 16px; }
  .app-portal { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center;
    justify-content: center; font-size: 18px; background: var(--surface2); flex-shrink: 0; }
  .app-info { flex: 1; }
  .app-title { font-size: 15px; font-weight: 700; }
  .app-company { font-size: 13px; color: var(--muted); margin-top: 2px; }
  .app-meta { display: flex; gap: 12px; margin-top: 6px; }
  .app-tag { font-size: 11px; color: var(--muted); }
  .score-badge { padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700;
    flex-shrink: 0; }
  .score-strong { background: rgba(16, 185, 129, 0.15); color: var(--green); }
  .score-moderate { background: rgba(79, 139, 255, 0.15); color: var(--accent); }
  .score-weak { background: rgba(245, 158, 11, 0.15); color: var(--amber); }
  .status-pill { padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; flex-shrink: 0; }
  .status-applied { background: rgba(16,185,129,0.12); color: var(--green); }
  .status-failed { background: rgba(239,68,68,0.12); color: var(--red); }
  .status-pending { background: rgba(245,158,11,0.12); color: var(--amber); }

  /* Pulse animation */
  @keyframes pulse-dot { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }
  .pulse { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    background: var(--green); animation: pulse-dot 1.2s ease-in-out infinite; margin-right: 6px; }

  /* Progress bar */
  .progress-bar { height: 4px; background: var(--surface2); border-radius: 2px; overflow: hidden; margin-top: 8px; }
  .progress-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent2));
    border-radius: 2px; transition: width 0.6s ease; }

  /* Empty state */
  .empty { text-align: center; padding: 60px 20px; color: var(--muted); }
  .empty-icon { font-size: 48px; margin-bottom: 16px; }
  .empty p { font-size: 14px; }

  /* Alerts */
  .alert { border-radius: 8px; padding: 12px 16px; font-size: 13px; margin-bottom: 16px; }
  .alert-info { background: rgba(79,139,255,0.1); border: 1px solid rgba(79,139,255,0.3); color: #93b4ff; }
  .alert-success { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); color: #6ee7b7; }
  .alert-warning { background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); color: #fcd34d; }
`;

// ─── Constants ────────────────────────────────────────────────────────────────

const PORTALS = [
  { id: "linkedin", name: "LinkedIn", icon: "💼", badge: "Easy Apply" },
  { id: "indeed", name: "Indeed", icon: "🔍", badge: "Quick Apply" },
  { id: "naukri", name: "Naukri", icon: "🇮🇳", badge: "India Focus" },
  { id: "glassdoor", name: "Glassdoor", icon: "🚪", badge: "Coming Soon", disabled: true },
  { id: "wellfound", name: "Wellfound", icon: "🚀", badge: "Coming Soon", disabled: true },
];

const COMMON_LOCATIONS = ["Bangalore", "Mumbai", "Delhi NCR", "Pune", "Hyderabad",
  "Chennai", "Dubai", "Abu Dhabi", "Remote", "Singapore"];

const SAMPLE_LOGS = [
  { ts: "09:41:02", level: "info", msg: "Session started — portals: LinkedIn, Indeed, Naukri" },
  { ts: "09:41:05", level: "info", msg: "[LinkedIn] Browser launched (headless)" },
  { ts: "09:41:09", level: "success", msg: "[LinkedIn] Login successful" },
  { ts: "09:41:11", level: "info", msg: "[LinkedIn] Searching: 'Software Architect' in 'Bangalore'" },
  { ts: "09:41:19", level: "info", msg: "[LinkedIn] Found 34 job cards" },
  { ts: "09:41:22", level: "info", msg: "[AI Matcher] Scoring 34 jobs against profile..." },
  { ts: "09:41:38", level: "success", msg: "[AI Matcher] 12 jobs matched (score ≥ 65)" },
  { ts: "09:41:41", level: "info", msg: "[LinkedIn] Applying: 'Sr. Software Architect' at Infosys (score: 87)" },
  { ts: "09:41:55", level: "success", msg: "[LinkedIn] ✓ Applied — Easy Apply submitted" },
  { ts: "09:42:03", level: "info", msg: "[LinkedIn] Applying: 'Tech Lead – SDV Platform' at Bosch (score: 91)" },
  { ts: "09:42:18", level: "success", msg: "[LinkedIn] ✓ Applied — Easy Apply submitted" },
  { ts: "09:42:26", level: "info", msg: "[Indeed] Browser launched" },
  { ts: "09:42:29", level: "success", msg: "[Indeed] Login successful" },
];

const SAMPLE_APPS = [
  { id: 1, portal: "linkedin", title: "Sr. Software Architect", company: "Infosys", location: "Bangalore",
    score: 87, status: "applied", reasons: ["SDV experience aligns", "15yr exp matches seniority"] },
  { id: 2, portal: "linkedin", title: "Tech Lead – SDV Platform", company: "Bosch", location: "Bangalore",
    score: 91, status: "applied", reasons: ["Exact title match", "Automotive domain fit"] },
  { id: 3, portal: "indeed", title: "Principal Engineer – E/E", company: "Tata Elxsi", location: "Pune",
    score: 79, status: "applied", reasons: ["E/E Architecture skills", "OEM exposure"] },
  { id: 4, portal: "naukri", title: "Software Architect – Connected Car", company: "Mahindra Tech", location: "Bangalore",
    score: 83, status: "pending", reasons: ["Connected car domain", "Strong skill overlap"] },
  { id: 5, portal: "linkedin", title: "Senior Architect – AI/ML", company: "NVIDIA", location: "Bangalore",
    score: 68, status: "failed", reasons: ["Partial match"], error: "No Easy Apply" },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

const portalIcon = { linkedin: "💼", indeed: "🔍", naukri: "🇮🇳", glassdoor: "🚪", wellfound: "🚀" };

function TagInput({ tags, onChange, placeholder, suggestions = [] }) {
  const [val, setVal] = useState("");
  const add = (t) => { const v = t.trim(); if (v && !tags.includes(v)) onChange([...tags, v]); setVal(""); };
  return (
    <div className="tag-input-wrap">
      {tags.map(t => (
        <span key={t} className="tag">
          {t}
          <button className="tag-x" onClick={() => onChange(tags.filter(x => x !== t))}>×</button>
        </span>
      ))}
      <input
        value={val}
        onChange={e => setVal(e.target.value)}
        onKeyDown={e => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(val); } }}
        onBlur={() => val && add(val)}
        placeholder={tags.length === 0 ? placeholder : ""}
      />
    </div>
  );
}

// ─── Pages ────────────────────────────────────────────────────────────────────

function SetupPage({ onComplete }) {
  const [step, setStep] = useState(0); // 0=upload, 1=profile, 2=prefs
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [profile, setProfile] = useState(null);
  const [prefs, setPrefs] = useState({
    target_titles: [],
    preferred_locations: [],
    portals: ["linkedin", "indeed"],
    min_salary: "",
    remote_ok: true,
    min_match_score: 65,
    max_applications_per_day: 10,
  });
  const fileRef = useRef();

  const handleFileUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    // Simulate API call (demo mode)
    await new Promise(r => setTimeout(r, 2000));
    setProfile({
      profile_id: 1,
      name: "N R Bhagwat",
      email: "nr.bhagwat@email.com",
      current_title: "Deputy General Manager – Software Defined Vehicle",
      years_experience: 20,
      skills: ["Python", "C++", "AUTOSAR", "ROS2", "CAN/LIN", "E/E Architecture",
               "SDV Platforms", "FastAPI", "Docker", "Kubernetes", "AI/ML"],
      inferred_target_titles: ["Software Architect", "Principal Engineer", "Tech Lead – SDV",
                                "Head of SDV Engineering", "AI/ML Engineer – Automotive"],
      summary: "20+ years in automotive software with deep expertise in SDV platforms, E/E architecture, and full-stack embedded systems. Ex-Bosch, Volvo, Delphi.",
    });
    setPrefs(p => ({ ...p, target_titles: ["Software Architect", "Principal Engineer", "Tech Lead – SDV"] }));
    setUploading(false);
    setStep(1);
  };

  const handleDrop = (e) => {
    e.preventDefault(); setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  };

  const STEPS = ["Upload CV", "Review Profile", "Set Preferences"];

  return (
    <div>
      <h1 className="page-title">Setup Your Agent</h1>
      <p className="page-sub">Three quick steps to launch your personalised job agent.</p>

      <div className="steps" style={{ marginBottom: 40 }}>
        {STEPS.map((s, i) => (
          <div key={i} className="step" style={{ alignItems: "center" }}>
            {i > 0 && <div className="step-line" />}
            <div className={`step ${i < step ? "done" : i === step ? "active" : "idle"}`}
              style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div className="step-num">{i < step ? "✓" : i + 1}</div>
              <span className="step-label">{s}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Step 0 — Upload */}
      {step === 0 && (
        <div>
          <div className={`upload-zone ${dragging ? "drag" : ""}`}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}>
            <input ref={fileRef} type="file" accept=".pdf,.docx" style={{ display: "none" }}
              onChange={e => handleFileUpload(e.target.files[0])} />
            {uploading ? (
              <>
                <div className="upload-icon">⚙️</div>
                <div className="upload-title">Claude is parsing your CV...</div>
                <div className="upload-sub">Extracting skills, experience, and building your profile</div>
                <div className="progress-bar" style={{ maxWidth: 280, margin: "20px auto 0" }}>
                  <div className="progress-fill" style={{ width: "60%" }} />
                </div>
              </>
            ) : (
              <>
                <div className="upload-icon">📄</div>
                <div className="upload-title">Drop your CV here</div>
                <div className="upload-sub">PDF or DOCX · Max 10MB · Parsed by Claude AI</div>
                <button className="btn btn-primary" style={{ marginTop: 20 }}>
                  Choose File
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Step 1 — Review Profile */}
      {step === 1 && profile && (
        <div>
          <div className="alert alert-success">✓ CV parsed successfully. Review your extracted profile below.</div>
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-title">Extracted Profile</div>
            <div className="profile-grid">
              <div className="profile-field"><label>Name</label><p>{profile.name}</p></div>
              <div className="profile-field"><label>Email</label><p>{profile.email}</p></div>
              <div className="profile-field"><label>Current Title</label><p>{profile.current_title}</p></div>
              <div className="profile-field"><label>Experience</label><p>{profile.years_experience} years</p></div>
              <div className="profile-field" style={{ gridColumn: "1/-1" }}>
                <label>Summary</label><p style={{ fontWeight: 400, lineHeight: 1.6 }}>{profile.summary}</p>
              </div>
            </div>
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8, fontWeight: 700 }}>Skills Detected</div>
              <div className="skill-tags">
                {profile.skills.map(s => <span key={s} className="tag">{s}</span>)}
              </div>
            </div>
          </div>
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-title">AI-Suggested Target Roles</div>
            <div className="skill-tags">
              {profile.inferred_target_titles.map(t => (
                <span key={t} style={{ background: "rgba(124,58,237,0.1)", color: "#a78bfa",
                  border: "1px solid rgba(124,58,237,0.2)", padding: "4px 12px",
                  borderRadius: 999, fontSize: 13, fontWeight: 600 }}>{t}</span>
              ))}
            </div>
          </div>
          <button className="btn btn-primary" onClick={() => setStep(2)}>
            Continue to Preferences →
          </button>
        </div>
      )}

      {/* Step 2 — Preferences */}
      {step === 2 && (
        <div>
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-title">Target Job Titles</div>
            <TagInput tags={prefs.target_titles}
              onChange={v => setPrefs(p => ({ ...p, target_titles: v }))}
              placeholder="Type title and press Enter..." />
          </div>

          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-title">Preferred Locations</div>
            <TagInput tags={prefs.preferred_locations}
              onChange={v => setPrefs(p => ({ ...p, preferred_locations: v }))}
              placeholder="City or Remote..." />
            <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
              {COMMON_LOCATIONS.map(l => (
                <button key={l} className="btn btn-ghost"
                  style={{ padding: "4px 10px", fontSize: 12 }}
                  onClick={() => !prefs.preferred_locations.includes(l) &&
                    setPrefs(p => ({ ...p, preferred_locations: [...p.preferred_locations, l] }))}>
                  + {l}
                </button>
              ))}
            </div>
          </div>

          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-title">Select Job Portals</div>
            <div className="portal-grid">
              {PORTALS.map(p => (
                <div key={p.id}
                  className={`portal-card ${prefs.portals.includes(p.id) ? "selected" : ""} ${p.disabled ? "" : ""}`}
                  style={{ opacity: p.disabled ? 0.4 : 1 }}
                  onClick={() => {
                    if (p.disabled) return;
                    setPrefs(prev => ({
                      ...prev,
                      portals: prev.portals.includes(p.id)
                        ? prev.portals.filter(x => x !== p.id)
                        : [...prev.portals, p.id]
                    }));
                  }}>
                  <div className="portal-logo">{p.icon}</div>
                  <div className="portal-name">{p.name}</div>
                  <div className="portal-badge">{p.badge}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-title">Agent Settings</div>
            <div className="form-row">
              <div className="form-group">
                <label>Min Match Score (0-100)</label>
                <input type="range" min="40" max="95" value={prefs.min_match_score}
                  onChange={e => setPrefs(p => ({ ...p, min_match_score: +e.target.value }))}
                  style={{ width: "100%", accentColor: "var(--accent)" }} />
                <p style={{ fontSize: 13, marginTop: 4, color: "var(--accent)", fontWeight: 700 }}>
                  {prefs.min_match_score}% — only apply to jobs scoring above this
                </p>
              </div>
              <div className="form-group">
                <label>Max Applications / Day</label>
                <input className="form-input" type="number" min="1" max="50"
                  value={prefs.max_applications_per_day}
                  onChange={e => setPrefs(p => ({ ...p, max_applications_per_day: +e.target.value }))} />
              </div>
            </div>
          </div>

          <button className="btn btn-success" onClick={() => onComplete({ profile, prefs })}>
            🚀 Launch Agent
          </button>
        </div>
      )}
    </div>
  );
}


function DashboardPage({ profile, prefs, isRunning, logs, stats, onStart }) {
  const logRef = useRef();
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 32 }}>
        <div>
          <h1 className="page-title">Agent Dashboard</h1>
          <p className="page-sub">{profile ? `Running for ${profile.name}` : "Ready to launch"}</p>
        </div>
        {profile && !isRunning && (
          <button className="btn btn-success" onClick={onStart}>🚀 Start Agent</button>
        )}
        {isRunning && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--green)",
            fontWeight: 700, fontSize: 14 }}>
            <span className="pulse" /> Agent Running...
          </div>
        )}
      </div>

      <div className="stat-grid">
        <div className="stat-card blue"><div className="stat-num">{stats.found}</div>
          <div className="stat-label">Jobs Found</div></div>
        <div className="stat-card amber"><div className="stat-num">{stats.matched}</div>
          <div className="stat-label">AI Matched</div></div>
        <div className="stat-card green"><div className="stat-num">{stats.applied}</div>
          <div className="stat-label">Applied</div></div>
        <div className="stat-card red"><div className="stat-num">{stats.failed}</div>
          <div className="stat-label">Failed</div></div>
      </div>

      {isRunning && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 8 }}>
            Progress ({stats.applied} / {prefs?.max_applications_per_day || 10} applications)
          </div>
          <div className="progress-bar">
            <div className="progress-fill"
              style={{ width: `${(stats.applied / (prefs?.max_applications_per_day || 10)) * 100}%` }} />
          </div>
        </div>
      )}

      <div className="log-wrap">
        <div className="log-header">
          <span className="log-title">Agent Log</span>
          {isRunning && <span style={{ fontSize: 12, color: "var(--green)" }}>
            <span className="pulse" style={{ width: 6, height: 6, marginRight: 4 }} />Live
          </span>}
        </div>
        <div className="log-body" ref={logRef}>
          {logs.length === 0 && (
            <div style={{ color: "var(--muted)", fontSize: 12 }}>No activity yet. Start the agent to begin.</div>
          )}
          {logs.map((l, i) => (
            <div key={i} className="log-entry">
              <span className="log-ts">{l.ts}</span>
              <span className={`log-msg ${l.level}`}>{l.msg}</span>
            </div>
          ))}
        </div>
      </div>

      {!profile && (
        <div className="empty">
          <div className="empty-icon">🤖</div>
          <p>Complete setup first to configure and launch your agent.</p>
        </div>
      )}
    </div>
  );
}


function ApplicationsPage({ applications }) {
  const [filter, setFilter] = useState("all");

  const filtered = filter === "all" ? applications
    : applications.filter(a => a.status === filter);

  const scoreClass = (s) => s >= 80 ? "score-strong" : s >= 65 ? "score-moderate" : "score-weak";

  return (
    <div>
      <h1 className="page-title">Applications</h1>
      <p className="page-sub">{applications.length} total applications tracked</p>

      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        {["all", "applied", "pending", "failed"].map(f => (
          <button key={f} className={`btn ${filter === f ? "btn-primary" : "btn-ghost"}`}
            style={{ padding: "8px 16px", fontSize: 13, textTransform: "capitalize" }}
            onClick={() => setFilter(f)}>
            {f} {f === "all" ? `(${applications.length})`
              : `(${applications.filter(a => a.status === f).length})`}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="empty">
          <div className="empty-icon">📭</div>
          <p>No applications yet. Start your agent to begin applying.</p>
        </div>
      ) : (
        <div className="app-list">
          {filtered.map(app => (
            <div key={app.id} className="app-card">
              <div className="app-portal">{portalIcon[app.portal] || "💼"}</div>
              <div className="app-info">
                <div className="app-title">{app.title}</div>
                <div className="app-company">{app.company} · {app.location}</div>
                <div className="app-meta">
                  {app.reasons?.slice(0, 2).map((r, i) => (
                    <span key={i} className="app-tag">✓ {r}</span>
                  ))}
                </div>
              </div>
              <span className={`score-badge ${scoreClass(app.score)}`}>{app.score}%</span>
              <span className={`status-pill status-${app.status}`}>{app.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


// ─── App Shell ────────────────────────────────────────────────────────────────

export default function App() {
  const [page, setPage] = useState("setup");
  const [profile, setProfile] = useState(null);
  const [prefs, setPrefs] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [applications, setApplications] = useState([]);
  const [stats, setStats] = useState({ found: 0, matched: 0, applied: 0, failed: 0 });

  const addLog = useCallback((msg, level = "info") => {
    const ts = new Date().toTimeString().slice(0, 8);
    setLogs(l => [...l, { ts, level, msg }]);
  }, []);

  const handleSetupComplete = ({ profile: p, prefs: pr }) => {
    setProfile(p);
    setPrefs(pr);
    setPage("dashboard");
  };

  const handleStartAgent = async () => {
    setIsRunning(true);
    setLogs([]);
    setStats({ found: 0, matched: 0, applied: 0, failed: 0 });
    setApplications([]);

    // Simulate agent running (demo mode)
    for (const log of SAMPLE_LOGS) {
      await new Promise(r => setTimeout(r, 800 + Math.random() * 600));
      addLog(log.msg, log.level);

      if (log.msg.includes("Found")) {
        const n = parseInt(log.msg.match(/\d+/)?.[0] || 0);
        setStats(s => ({ ...s, found: s.found + n }));
      }
      if (log.msg.includes("matched")) {
        const n = parseInt(log.msg.match(/\d+/)?.[0] || 0);
        setStats(s => ({ ...s, matched: s.matched + n }));
      }
      if (log.msg.includes("✓ Applied")) {
        setStats(s => ({ ...s, applied: s.applied + 1 }));
        const app = SAMPLE_APPS[applications.length] || SAMPLE_APPS[0];
        setApplications(prev => [...prev, { ...app, id: Date.now() + Math.random() }]);
      }
    }

    // Add remaining sample apps
    for (const app of SAMPLE_APPS.slice(2)) {
      await new Promise(r => setTimeout(r, 1200));
      setApplications(prev => [...prev, app]);
      if (app.status === "applied") setStats(s => ({ ...s, applied: s.applied + 1 }));
      if (app.status === "failed") setStats(s => ({ ...s, failed: s.failed + 1 }));
    }

    addLog("Session complete — agent shutting down gracefully", "success");
    setIsRunning(false);
  };

  const navItems = [
    { id: "setup", label: "Setup", icon: "⚙️" },
    { id: "dashboard", label: "Dashboard", icon: "📊" },
    { id: "applications", label: "Applications", icon: "📋" },
  ];

  return (
    <>
      <style>{css}</style>
      <div className="app">
        <nav className="sidebar">
          <div className="logo">
            <div className="logo-icon">🤖</div>
            JobAgent
          </div>
          {navItems.map(n => (
            <button key={n.id} className={`nav-btn ${page === n.id ? "active" : ""}`}
              onClick={() => setPage(n.id)}>
              <span>{n.icon}</span> {n.label}
              {n.id === "applications" && applications.length > 0 && (
                <span style={{ marginLeft: "auto", background: "var(--accent)",
                  color: "#fff", borderRadius: 999, padding: "1px 7px", fontSize: 10, fontWeight: 700 }}>
                  {applications.length}
                </span>
              )}
            </button>
          ))}
          <hr className="nav-divider" />
          <div style={{ fontSize: 11, color: "var(--muted)", padding: "0 8px", lineHeight: 1.6 }}>
            <div style={{ marginBottom: 8, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1 }}>
              Status
            </div>
            {profile ? (
              <>
                <div>👤 {profile.name?.split(" ")[0]}</div>
                <div style={{ marginTop: 4 }}>
                  {isRunning ? (
                    <span style={{ color: "var(--green)" }}><span className="pulse" />Running</span>
                  ) : (
                    <span style={{ color: "var(--muted)" }}>● Idle</span>
                  )}
                </div>
              </>
            ) : (
              <div>No profile loaded</div>
            )}
          </div>
        </nav>

        <main className="main">
          {page === "setup" && <SetupPage onComplete={handleSetupComplete} />}
          {page === "dashboard" && (
            <DashboardPage
              profile={profile} prefs={prefs}
              isRunning={isRunning} logs={logs} stats={stats}
              onStart={handleStartAgent}
            />
          )}
          {page === "applications" && <ApplicationsPage applications={applications} />}
        </main>
      </div>
    </>
  );
}
