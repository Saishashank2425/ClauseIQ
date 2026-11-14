import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity, ArrowUp, ArrowUpRight, BookOpen, Check, ChevronDown, CircleHelp,
  File, FilePlus2, FileText, FolderOpen, Gauge, LayoutDashboard, LoaderCircle,
  LogOut, Menu, MessageSquare, MoreHorizontal, Paperclip, Plus, Search, Send,
  Shield, ShieldAlert, ShieldCheck, Sparkles, UploadCloud, UserRound, X
} from "lucide-react";

const API = (import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")).replace(/\/$/, "");
const suggestions = [
  "What are the biggest risks in this agreement?",
  "Can either party terminate early?",
  "Is there a liability cap?",
  "When does this contract renew?"
];

export default function App() {
  const [authConfig, setAuthConfig] = useState({google_enabled:false, google_client_id:""});
  const [user, setUser] = useState(() => { try { return JSON.parse(sessionStorage.getItem("clauseiq_user") || "null"); } catch { return null; } });
  const [token, setToken] = useState(() => sessionStorage.getItem("clauseiq_token") || "");
  const [showLogin, setShowLogin] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [isDemo, setIsDemo] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [ocr, setOcr] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [toast, setToast] = useState("");
  const fileInput = useRef(null);
  const chatEnd = useRef(null);
  const textarea = useRef(null);

  useEffect(() => {
    fetch(API + "/api/v1/auth/config").then(r=>r.json()).then(setAuthConfig).catch(()=>{});
  }, []);
  useEffect(() => {
    if (!authConfig.google_enabled || !authConfig.google_client_id) return;
    if (window.google?.accounts?.id) return;
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);
    return () => {};
  }, [authConfig]);
  useEffect(() => { chatEnd.current?.scrollIntoView({behavior:"smooth"}); }, [messages, busy]);
  useEffect(() => {
    const el = textarea.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 150) + "px";
  }, [input]);

  const login = useCallback(() => {
    setLoginError("");
    if (!authConfig.google_enabled) {
      setLoginError("Google sign-in is not connected yet. Add your Google OAuth Web Client ID to the Render service to enable it.");
      return;
    }
    const begin = () => {
      if (!window.google?.accounts?.id) { setLoginError("Google Identity Services is still loading. Try again in a moment."); return; }
      window.google.accounts.id.initialize({
        client_id: authConfig.google_client_id,
        callback: async (response) => {
          try {
            const result = await fetch(API + "/api/v1/auth/google", {
              method:"POST", headers:{"Content-Type":"application/json"},
              body:JSON.stringify({credential:response.credential})
            });
            const data = await result.json();
            if (!result.ok) throw new Error(data.detail || "Google sign-in failed.");
            setUser(data.user); setToken(response.credential);
            sessionStorage.setItem("clauseiq_user", JSON.stringify(data.user));
            sessionStorage.setItem("clauseiq_token", response.credential);
            setShowLogin(false); setLoginError("");
          } catch (e) { setLoginError(e.message); }
        }
      });
      window.google.accounts.id.prompt();
    };
    if (window.google?.accounts?.id) begin();
    else {
      const timer = setInterval(() => { if (window.google?.accounts?.id) { clearInterval(timer); begin(); } }, 250);
      setTimeout(() => clearInterval(timer), 8000);
    }
  }, [authConfig]);

  const logout = () => {
    setUser(null); setToken(""); sessionStorage.removeItem("clauseiq_user"); sessionStorage.removeItem("clauseiq_token");
    setToast("Signed out"); setTimeout(()=>setToast(""),2200);
  };

  const loadDemo = async () => {
    setBusy(true); setError(""); setMessages([]);
    try {
      const response = await fetch(API + "/api/v1/demo");
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load the sample workspace.");
      setAnalysis(data); setFile(null); setIsDemo(true); setActiveTab("overview");
      setMessages([{role:"assistant",content:"I’ve loaded the **Northstar SaaS Services Agreement**, a synthetic five-page sample contract. I can help you inspect the indemnity language, termination rights, renewal mechanics and other clauses. Answers are grounded in retrieved passages, with source references shown below.",evidence:[]}]);
    } catch(e) { setError(e.message); }
    finally { setBusy(false); setMobileMenu(false); }
  };

  const uploadDocument = async (selected) => {
    if (!selected) return;
    if (!user || !token) { setFile(selected); setShowLogin(true); return; }
    if (!/\.(pdf|docx)$/i.test(selected.name)) { setError("Please choose a PDF or DOCX document."); return; }
    if (selected.size > 20 * 1024 * 1024) { setError("This file is larger than the 20 MB limit."); return; }
    setFile(selected); setIsDemo(false); setAnalysis(null); setMessages([]); setBusy(true); setError("");
    const form = new FormData(); form.append("file", selected);
    try {
      const response = await fetch(API + "/api/v1/analyze?enable_ocr=" + ocr, {method:"POST",headers:{Authorization:"Bearer "+token},body:form});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Document analysis failed.");
      setAnalysis(data);
      setMessages([{role:"assistant",content:"Your document has been indexed for this session. Ask me about obligations, liability, renewal, termination or any specific wording. I’ll retrieve relevant clauses and show the evidence used.",evidence:[]}]);
    } catch(e) { setError(e.message); setFile(null); }
    finally { setBusy(false); }
  };

  const sendMessage = async (text = input) => {
    const question = text.trim();
    if (!question || busy) return;
    if (!analysis) { setError("Load the sample contract or upload a document first."); return; }
    setInput(""); setError("");
    setMessages(prev=>[...prev,{role:"user",content:question}]);
    setBusy(true);
    try {
      let response;
      if (isDemo) {
        response = await fetch(API + "/api/v1/demo/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question})});
      } else {
        if (!token) { setShowLogin(true); throw new Error("Sign in with Google to query uploaded documents."); }
        const form = new FormData(); form.append("file",file); form.append("question",question);
        response = await fetch(API + "/api/v1/ask?enable_ocr=" + ocr,{method:"POST",headers:{Authorization:"Bearer "+token},body:form});
      }
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not answer this question.");
      setMessages(prev=>[...prev,{role:"assistant",content:data.answer,evidence:data.evidence||[],abstained:data.abstained,mode:data.mode}]);
    } catch(e) {
      setMessages(prev=>[...prev,{role:"assistant",content:"I couldn’t complete that request: "+e.message,evidence:[],error:true}]);
    } finally { setBusy(false); }
  };

  const newChat = () => { setMessages(analysis?[{role:"assistant",content:"New conversation started. Ask a question about the current document and I’ll retrieve supporting clauses.",evidence:[]}]:[]); setError(""); };
  const summary = analysis?.summary || {high:0,medium:0,low:0};
  const totalRisks = summary.high + summary.medium;
  const openLogin = () => { setLoginError(""); setShowLogin(true); };

  return <div className="shell">
    <aside className={"sidebar "+(mobileMenu?"sidebar-open":"")}>
      <div className="side-brand"><div className="brand-icon"><ShieldCheck size={19}/></div><span>Clause<span>IQ</span></span><button className="mobile-close icon-btn" onClick={()=>setMobileMenu(false)}><X size={17}/></button></div>
      <button className="new-chat" onClick={newChat}><Plus size={16}/> New conversation <span>⌘ K</span></button>
      <div className="side-section"><div className="side-label">WORKSPACE</div>
        <button className="side-link selected"><MessageSquare size={16}/> Ask ClauseIQ</button>
        <button className="side-link" onClick={()=>setActiveTab("overview")}><LayoutDashboard size={16}/> Overview</button>
        <button className="side-link" onClick={()=>fileInput.current?.click()}><FolderOpen size={16}/> Documents</button>
        <button className="side-link" onClick={()=>setActiveTab("risks")}><ShieldAlert size={16}/> Risk register {analysis&&<span className="side-count">{totalRisks}</span>}</button>
      </div>
      <div className="side-section recent-section"><div className="side-label">RECENT</div>
        {analysis?<button className="recent-file" onClick={()=>setActiveTab("overview")}><FileText size={15}/><span>{analysis.filename.replace("_DEMO","").replaceAll("_"," ")}</span></button>:<div className="empty-recent">Your recent documents appear here.</div>}
        <button className="sample-link" onClick={loadDemo}><BookOpen size={15}/><span>Try sample agreement</span><ArrowUpRight size={13}/></button>
      </div>
      <div className="sidebar-bottom">
        <div className="privacy-note"><Shield size={15}/><span>Session-based analysis<br/><small>Uploaded files are not saved by this demo.</small></span></div>
        <div className="profile">
          {user?.picture?<img src={user.picture} alt=""/>:<div className="avatar"><UserRound size={16}/></div>}
          <div className="profile-copy"><strong>{user?.name || "Guest workspace"}</strong><small>{user?.email || "Demo access"}</small></div>
          {user?<button className="icon-btn" title="Sign out" onClick={logout}><LogOut size={15}/></button>:<button className="sign-in-small" onClick={openLogin}>Sign in</button>}
        </div>
      </div>
    </aside>

    <main className="main-area">
      <header className="topbar">
        <div className="top-left"><button className="mobile-menu icon-btn" onClick={()=>setMobileMenu(!mobileMenu)}><Menu size={18}/></button><span className="crumb">Workspace</span><span className="crumb-sep">/</span><strong>Ask ClauseIQ</strong></div>
        <div className="top-right"><span className="secure-status"><i/> Secure session</span><button className="help-btn" title="About ClauseIQ"><CircleHelp size={17}/></button>{user?<button className="user-pill" onClick={logout}>{user.picture?<img src={user.picture} alt=""/>:<UserRound size={15}/>}<span>{user.name?.split(" ")[0]||"Account"}</span><ChevronDown size={13}/></button>:<button className="top-signin" onClick={openLogin}>Sign in <ArrowUpRight size={14}/></button>}</div>
      </header>

      <div className="workspace">
        <section className="chat-column">
          <div className="chat-heading">
            <div><div className="product-kicker"><Sparkles size={13}/> CONTRACT INTELLIGENCE</div><h1>Ask your contract anything.</h1><p>Grounded answers. Traceable evidence. Less time in the fine print.</p></div>
            <div className="model-pill"><span className="model-dot"/>{isDemo?"Sample RAG workspace":"Hybrid retrieval"}<ChevronDown size={13}/></div>
          </div>
          <div className="chat-scroll">
            {!analysis&&!busy&&<div className="welcome">
              <div className="welcome-orb"><ShieldCheck size={30}/></div>
              <div className="welcome-label">YOUR LEGAL DOCUMENT COPILOT</div>
              <h2>Good work starts with<br/><em>the right questions.</em></h2>
              <p>Upload a contract or explore the sample workspace to see how ClauseIQ retrieves clauses, highlights risk indicators and answers with source evidence.</p>
              <div className="welcome-actions"><button className="upload-cta" onClick={()=>user?fileInput.current?.click():openLogin()}><UploadCloud size={16}/> Upload a contract</button><button className="demo-cta" onClick={loadDemo}><BookOpen size={16}/> Explore sample contract</button></div>
              <div className="capability-row"><span><Search size={13}/> Hybrid search</span><span><FileText size={13}/> Clause citations</span><span><ShieldCheck size={13}/> Risk signals</span></div>
            </div>}
            {analysis&&messages.length===0&&!busy&&<div className="welcome compact-welcome"><div className="welcome-orb"><Sparkles size={26}/></div><h2>What would you like to know?</h2><p>Ask a question about <strong>{analysis.filename}</strong>. Responses include the clauses used as evidence.</p><div className="suggestion-grid">{suggestions.map(s=><button key={s} onClick={()=>sendMessage(s)}>{s}<ArrowUpRight size={13}/></button>)}</div></div>}
            {messages.map((m,i)=><div className={"message-row "+m.role} key={i}>
              <div className={"message-avatar "+(m.role==="assistant"?"assistant-avatar":"user-avatar")}>{m.role==="assistant"?<ShieldCheck size={16}/>:user?.picture?<img src={user.picture} alt=""/>:<UserRound size={15}/>}</div>
              <div className="message-body"><div className="message-author">{m.role==="assistant"?"ClauseIQ":"You"} <span>{m.role==="assistant"?"· Evidence assistant":""}</span></div><div className={"message-content "+(m.error?"message-error":"")}>{m.content.split(/\*\*(.*?)\*\*/g).map((part,j)=>j%2?<strong key={j}>{part}</strong>:part)}</div>
                {m.abstained&&<div className="abstain-note"><ShieldAlert size={13}/> Not enough supporting evidence to answer confidently.</div>}
                {m.evidence?.length>0&&<div className="source-block"><div className="source-title"><span><BookOpen size={13}/> SOURCES RETRIEVED</span><span>{m.evidence.length} passages</span></div>{m.evidence.map((ev,j)=><div className="source-card" key={j}><div className="source-card-head"><strong>{ev.clause_id}</strong><span>{ev.page?"Page "+ev.page:"Contract passage"}</span><span className="relevance">{Math.round((ev.relevance_score||0)*100)}% match</span></div><p>{ev.text}</p></div>)}</div>}
                {m.role==="assistant"&&!m.error&&<div className="message-tools"><span><Check size={12}/> Evidence-linked response</span><button onClick={()=>navigator.clipboard?.writeText(m.content)} title="Copy response"><File size={13}/> Copy</button></div>}
              </div>
            </div>)}
            {busy&&<div className="message-row assistant"><div className="message-avatar assistant-avatar"><ShieldCheck size={16}/></div><div className="message-body"><div className="message-author">ClauseIQ <span>· Working</span></div><div className="thinking"><span/><span/><span/> Retrieving relevant passages</div></div></div>}
            <div ref={chatEnd}/>
          </div>
          {error&&<div className="inline-error"><ShieldAlert size={14}/>{error}<button onClick={()=>setError("")}><X size={13}/></button></div>}
          <div className="composer-wrap">
            {analysis&&<div className="active-doc-chip"><FileText size={13}/><span>{analysis.filename}</span><span className="indexed-dot"/> {isDemo?"Sample indexed":"Analyzed"}</div>}
            <div className="composer">
              <textarea ref={textarea} value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendMessage();}}} placeholder={analysis?"Ask a follow-up about this agreement…":"Load a contract to start a conversation…"} rows={1} disabled={!analysis||busy}/>
              <div className="composer-bottom"><div className="composer-tools"><button onClick={()=>user?fileInput.current?.click():openLogin()} title="Attach a contract"><Paperclip size={16}/></button><span>Answers are grounded in the selected document</span></div><button className="send-btn" disabled={!input.trim()||!analysis||busy} onClick={()=>sendMessage()}><ArrowUp size={17}/></button></div>
            </div>
            <div className="composer-disclaimer">ClauseIQ can make mistakes. Verify important clauses with qualified legal counsel.</div>
          </div>
        </section>

        <aside className="context-panel">
          <div className="context-header"><div><span className="panel-kicker">DOCUMENT CONTEXT</span><h3>Review panel</h3></div><button className="icon-btn"><MoreHorizontal size={17}/></button></div>
          <div className="context-tabs"><button className={activeTab==="overview"?"active":""} onClick={()=>setActiveTab("overview")}>Overview</button><button className={activeTab==="risks"?"active":""} onClick={()=>setActiveTab("risks")}>Risk signals</button></div>
          {!analysis?<div className="context-empty"><div><FilePlus2 size={22}/></div><strong>No document selected</strong><p>Upload a contract or load the sample agreement to see extracted clauses and review signals here.</p><button onClick={loadDemo}>Load sample data <ArrowUpRight size={13}/></button></div>:activeTab==="overview"?<div className="context-content">
            <div className="document-card"><div className="doc-icon"><FileText size={20}/></div><div className="doc-name"><strong>{analysis.filename.replaceAll("_"," ")}</strong><small>{isDemo?"Synthetic sample · 5 pages":analysis.pages+" pages"} · {analysis.word_count.toLocaleString()} words</small></div><span className="doc-check"><Check size={13}/></span></div>
            <div className="index-status"><div><span className="indexed-dot"/> {isDemo?"Sample corpus ready":"Document analyzed"}</div><span>Ready</span></div>
            <div className="panel-divider"/>
            <div className="panel-section-title">RISK OVERVIEW <span>RULE-BASED</span></div>
            <div className="risk-score"><div className="risk-score-num">{totalRisks}<small> / {analysis.clauses.length}</small></div><div><strong>Review indicators</strong><small>Clauses flagged for attention</small></div></div>
            <div className="risk-bars"><div><span>High</span><div><i className="bar-high" style={{width:(summary.high/Math.max(analysis.clauses.length,1)*100)+"%"}}/></div><b>{summary.high}</b></div><div><span>Medium</span><div><i className="bar-medium" style={{width:(summary.medium/Math.max(analysis.clauses.length,1)*100)+"%"}}/></div><b>{summary.medium}</b></div><div><span>Low</span><div><i className="bar-low" style={{width:(summary.low/Math.max(analysis.clauses.length,1)*100)+"%"}}/></div><b>{summary.low}</b></div></div>
            <div className="panel-divider"/>
            <div className="panel-section-title">EXTRACTED CLAUSES <span>{analysis.clauses.length} FOUND</span></div>
            <div className="clause-mini-list">{analysis.clauses.slice(0,6).map(c=><div className="clause-mini" key={c.clause_id}><span className={"mini-risk "+c.risk_level}/><div><strong>{c.category.replaceAll("_"," ")}</strong><small>{c.clause_id} · {c.page?"Page "+c.page:"Page n/a"}</small></div><span className="mini-level">{c.risk_level}</span></div>)}</div>
            <div className="context-foot"><ShieldCheck size={14}/> Source text retained for this session only.</div>
          </div>:<div className="context-content"><div className="panel-section-title">CLAUSES TO REVIEW <span>{totalRisks} FLAGGED</span></div>{analysis.clauses.filter(c=>c.risk_level!=="low").map(c=><div className="risk-item" key={c.clause_id}><div><span className={"risk-label "+c.risk_level}>{c.risk_level} review</span><strong>{c.category.replaceAll("_"," ")}</strong><small>{c.clause_id} · {c.page?"Page "+c.page:"Page n/a"}</small></div><p>{c.explanation}</p></div>)}<p className="risk-disclaimer">These indicators are heuristic review prompts, not legal conclusions or a substitute for counsel.</p></div>}
          <div className="context-bottom"><div className="engine-line"><Activity size={14}/><span>Retrieval pipeline</span><strong>{analysis?"Ready":"Idle"}</strong></div><div className="engine-sub">BM25 + TF-IDF · Optional dense reranking</div></div>
        </aside>
      </div>
      <input ref={fileInput} type="file" accept=".pdf,.docx" hidden onChange={e=>uploadDocument(e.target.files?.[0])}/>
    </main>

    {showLogin&&<div className="modal-backdrop" onClick={()=>setShowLogin(false)}><div className="login-modal" onClick={e=>e.stopPropagation()}><button className="modal-close icon-btn" onClick={()=>setShowLogin(false)}><X size={17}/></button><div className="login-mark"><ShieldCheck size={25}/></div><div className="panel-kicker">CLAUSEIQ WORKSPACE</div><h2>Sign in to continue</h2><p>Use your Google account to securely access document uploads and private contract analysis.</p><button className="google-button" onClick={login}><svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.74 7.18l7.65 5.93c4.46-4.12 7.13-10.19 7.13-17.58z"/><path fill="#FBBC05" d="M10.53 28.59A14.4 14.4 0 0 1 9.75 24c0-1.59.27-3.13.76-4.59l-7.98-6.19A23.9 23.9 0 0 0 0 24c0 3.88.93 7.56 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.9-5.87l-7.65-5.93c-2.12 1.42-4.84 2.27-8.25 2.27-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>Continue with Google</button>{loginError&&<div className="login-error">{loginError}</div>}{!authConfig.google_enabled&&<div className="setup-hint">Google OAuth is not configured on the server yet. You can still explore the sample RAG workspace without signing in.</div>}<button className="demo-under" onClick={()=>{setShowLogin(false);if(!analysis)loadDemo();}}>Continue with sample workspace</button><small className="login-legal">Your Google ID token is verified by the ClauseIQ API. Do not upload confidential contracts to this prototype.</small></div></div>}
    {toast&&<div className="toast"><Check size={14}/>{toast}</div>}
  </div>;
}
