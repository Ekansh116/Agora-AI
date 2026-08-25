import { useState, useEffect, useRef } from "react";
import { 
  LayoutDashboard,
  MessageSquare, 
  FileText,
  BarChart3,
  Users,
  Database,
  Settings,
  Bell,
  Sun,
  Moon,
  Search,
  Menu,
  X,
  UploadCloud, 
  Trash2, 
  ShieldAlert, 
  ChevronRight,
  ChevronDown, 
  ChevronUp, 
  Calendar, 
  Sparkles, 
  Loader,
  Check,
  Award,
  Sliders,
  Clock
} from "lucide-react";
import { api } from "./utils/api";
import type { Source, DashboardData, ChatResponse, ReportResponse, MessageExplorerItem, ExplorerStats } from "./utils/api";

type Tab = "dashboard" | "chat" | "report" | "sources" | "analytics" | "members" | "settings" | "explorer";

const suggestedQuestions = [
  "Why are members becoming inactive?",
  "What topics generate the most discussion?",
  "Summarize this month's conversations.",
  "Who are the most active contributors?",
  "What should we organize next?",
  "What trends have emerged recently?"
];

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");
  const [sources, setSources] = useState<Source[]>([]);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [chat, setChat] = useState<{ query: string; response: ChatResponse }[]>([]);
  
  // Settings configurability
  const [ollamaUrl, setOllamaUrl] = useState("http://localhost:11434");
  const [llmModel, setLlmModel] = useState("qwen2.5:1.5b");

  // UI States
  const [theme, setTheme] = useState<"light" | "dark">(
    () => (localStorage.getItem("theme") as "light" | "dark") || "light"
  );
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [queryInput, setQueryInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [health, setHealth] = useState<{ online: boolean; ollamaConnected: boolean } | null>(null);
  const [expandedEvidence, setExpandedEvidence] = useState<{ [key: number]: boolean }>({});
  
  // Conversation Explorer States
  const [explorerMessages, setExplorerMessages] = useState<MessageExplorerItem[]>([]);
  const [explorerCount, setExplorerCount] = useState(0);
  const [explorerStats, setExplorerStats] = useState<ExplorerStats | null>(null);
  const [explorerLoading, setExplorerLoading] = useState(false);
  const [explorerError, setExplorerError] = useState<string | null>(null);

  const [expRange, setExpRange] = useState("all");
  const [expStartDate, setExpStartDate] = useState("");
  const [expEndDate, setExpEndDate] = useState("");
  const [expSender, setExpSender] = useState("");
  const [expKeyword, setExpKeyword] = useState("");
  const [expMedia, setExpMedia] = useState("all");
  const [expLimit, setExpLimit] = useState(50);
  const [expOffset, setExpOffset] = useState(0);

  const loadExplorerMessages = async (resetOffset = false) => {
    setExplorerLoading(true);
    setExplorerError(null);
    const targetOffset = resetOffset ? 0 : expOffset;
    if (resetOffset) {
      setExpOffset(0);
    }
    
    try {
      const res = await api.getExplorerMessages({
        sourceId: selectedSource?.id || null,
        relativeRange: expRange,
        startDate: expRange === "custom" && expStartDate ? new Date(expStartDate).toISOString() : undefined,
        endDate: expRange === "custom" && expEndDate ? new Date(expEndDate).toISOString() : undefined,
        sender: expSender.trim() || undefined,
        keyword: expKeyword.trim() || undefined,
        hasMedia: expMedia === "media_only" ? true : expMedia === "text_only" ? false : null,
        limit: expLimit,
        offset: targetOffset
      });
      setExplorerMessages(res.messages);
      setExplorerCount(res.total_count);
      setExplorerStats(res.stats);
    } catch (err: any) {
      setExplorerError(err.message || "Failed to load explorer messages");
    } finally {
      setExplorerLoading(false);
    }
  };

  // Trigger loads when filters or selections change
  useEffect(() => {
    if (activeTab === "explorer") {
      loadExplorerMessages(true);
    }
  }, [activeTab, selectedSource, expRange, expMedia, expLimit]);

  useEffect(() => {
    if (activeTab === "explorer") {
      loadExplorerMessages(false);
    }
  }, [expOffset]);
  
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync theme attribute with document root
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  // Initial loads
  useEffect(() => {
    checkHealth();
    loadSources();
  }, []);

  // Poll indexing tasks
  useEffect(() => {
    const isProcessing = sources.some(s => 
      s.status !== "ready" && !s.status.startsWith("failed")
    );
    if (isProcessing) {
      const interval = setInterval(() => {
        loadSources();
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [sources]);

  // Load dashboard on source update
  useEffect(() => {
    loadDashboard();
    setReport(null);
  }, [selectedSource]);

  // Scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat, chatLoading]);

  const checkHealth = async () => {
    try {
      const data = await api.getHealth();
      setHealth({ online: true, ollamaConnected: data.ollama_online });
    } catch {
      setHealth({ online: false, ollamaConnected: false });
    }
  };

  const loadSources = async () => {
    try {
      const list = await api.getSources();
      setSources(list);
    } catch (e) {
      console.error(e);
    }
  };

  const loadDashboard = async () => {
    try {
      const data = await api.getDashboard(selectedSource?.id || null);
      setDashboard(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    
    setUploadLoading(true);
    try {
      const newSource = await api.uploadSource(file);
      setSources(prev => [newSource, ...prev]);
      setSelectedSource(newSource);
      setActiveTab("sources"); // Open sources tab to view timeline
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setUploadLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDeleteSource = async (id: number) => {
    if (!confirm("Are you sure you want to delete this community source? This deletes all parsed conversations and vector store indexes.")) return;
    try {
      await api.deleteSource(id);
      if (selectedSource?.id === id) {
        setSelectedSource(null);
      }
      loadSources();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleGenerateReport = async () => {
    setReportLoading(true);
    try {
      const data = await api.getCommunityReport(selectedSource?.id || null);
      setReport(data);
    } catch (err: any) {
      alert(`Report generation failed: ${err.message}`);
    } finally {
      setReportLoading(false);
    }
  };

  const handleChatSubmit = async (queryText: string) => {
    if (!queryText.trim() || chatLoading) return;
    const userQuery = queryText;
    setQueryInput("");
    setChatLoading(true);
    
    setChat(prev => [...prev, { query: userQuery, response: {
      observation: "", inference: "", recommendation: "", evidence: [], confidence: "Low", confidence_reason: "Retrieving..."
    }}]);

    try {
      const answer = await api.queryChat(userQuery, selectedSource?.id || null);
      setChat(prev => {
        const next = [...prev];
        next[next.length - 1].response = answer;
        return next;
      });
    } catch (err: any) {
      setChat(prev => {
        const next = [...prev];
        next[next.length - 1].response = {
          observation: `Failed: ${err.message}`,
          inference: "Network failed.",
          recommendation: "Verify API status.",
          evidence: [],
          confidence: "Low",
          confidence_reason: "API error"
        };
        return next;
      });
    } finally {
      setChatLoading(false);
    }
  };

  const toggleEvidence = (idx: number) => {
    setExpandedEvidence(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const toggleTheme = () => {
    setTheme(prev => prev === "light" ? "dark" : "light");
  };

  // SVGs scaling
  const maxVolume = dashboard?.message_volume.length
    ? Math.max(...dashboard.message_volume.map(v => v.count), 1)
    : 1;

  const maxHourCount = dashboard?.active_hours.length
    ? Math.max(...dashboard.active_hours.map(h => h.count), 1)
    : 1;

  const maxSenderCount = dashboard?.top_senders.length
    ? Math.max(...dashboard.top_senders.map(s => s.count), 1)
    : 1;
  return (
    <div className="app-layout">
      {/* MOBILE SIDEBAR OVERLAY */}
      <div 
        className={`sidebar-overlay ${sidebarOpen ? "open" : ""}`} 
        onClick={() => setSidebarOpen(false)}
      />

      {/* LEFT PERMANENT SIDEBAR */}
      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div>
          <div className="sidebar-logo">
            <Sparkles size={24} color="var(--primary)" />
            <span className="logo-text">Comm AI Platform</span>
          </div>

          <nav className="sidebar-nav">
            <button 
              className={`nav-item ${activeTab === "dashboard" ? "active" : ""}`}
              onClick={() => { setActiveTab("dashboard"); setSidebarOpen(false); }}
            >
              <LayoutDashboard size={18} />
              Dashboard
            </button>
            <button 
              className={`nav-item ${activeTab === "chat" ? "active" : ""}`}
              onClick={() => { setActiveTab("chat"); setSidebarOpen(false); }}
            >
              <MessageSquare size={18} />
              AI Chat
            </button>
            <button 
              className={`nav-item ${activeTab === "report" ? "active" : ""}`}
              onClick={() => { setActiveTab("report"); setSidebarOpen(false); }}
            >
              <FileText size={18} />
              Community Report
            </button>
            <button 
              className={`nav-item ${activeTab === "analytics" ? "active" : ""}`}
              onClick={() => { setActiveTab("analytics"); setSidebarOpen(false); }}
            >
              <BarChart3 size={18} />
              Analytics
            </button>
            <button 
              className={`nav-item ${activeTab === "members" ? "active" : ""}`}
              onClick={() => { setActiveTab("members"); setSidebarOpen(false); }}
            >
              <Users size={18} />
              Members
            </button>
            <button 
              className={`nav-item ${activeTab === "sources" ? "active" : ""}`}
              onClick={() => { setActiveTab("sources"); setSidebarOpen(false); }}
            >
              <Database size={18} />
              Data Sources
            </button>
            <button 
              className={`nav-item ${activeTab === "explorer" ? "active" : ""}`}
              onClick={() => { setActiveTab("explorer"); setSidebarOpen(false); }}
            >
              <Sliders size={18} />
              Conversation Explorer
            </button>
          </nav>
        </div>

        <div className="sidebar-footer">
          <button 
            className={`nav-item ${activeTab === "settings" ? "active" : ""}`}
            onClick={() => { setActiveTab("settings"); setSidebarOpen(false); }}
          >
            <Settings size={18} />
            Settings
          </button>
          
          {/* SaaS Pro Upgrade Card */}
          <div className="upgrade-card">
            <h4>Upgrade to Enterprise</h4>
            <p>Access Discord, Slack & multi-community parsing features.</p>
            <button className="upgrade-btn">Upgrade</button>
          </div>
          
          <span className="version-text">v1.0.0 (MVP)</span>
        </div>
      </aside>

      {/* RIGHT MAIN CONTAINER */}
      <div className="main-area">
        {/* TOP NAVIGATION BAR */}
        <header className="top-bar">
          <div className="top-left">
            <button className="hamburger" onClick={() => setSidebarOpen(true)}>
              <Menu size={22} />
            </button>
            
            <div className="search-container">
              <Search size={16} color="var(--text-muted)" />
              <input type="text" className="search-input" placeholder="Search workspace..." />
            </div>
          </div>

          <div className="top-right">
            {/* Ollama status indicators */}
            {health?.online ? (
              <div className={`status-indicator ${health.ollamaConnected ? "status-online" : "status-offline"}`}>
                <span className="pulse-dot"></span>
                {health.ollamaConnected ? "Ollama Connected" : "Ollama Refused"}
              </div>
            ) : (
              <div className="status-indicator status-offline">
                <span className="pulse-dot"></span>
                Backend Offline
              </div>
            )}

            <button className="icon-btn" onClick={toggleTheme} title="Toggle theme mode">
              {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
            </button>

            <button className="icon-btn" title="View notifications">
              <Bell size={18} />
            </button>

            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", borderLeft: "1px solid var(--border-color)", paddingLeft: "1rem" }}>
              <div className="avatar" style={{ display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.75rem", fontWeight: 700, color: "var(--primary)" }}>AI</div>
              <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>Analyst</span>
            </div>
          </div>
        </header>

        {/* WELCOME BANNER greeting */}
        <section className="greeting-section">
          <h2>{(() => {
            const h = new Date().getHours();
            return h < 12 ? "Good Morning!" : h < 18 ? "Good Afternoon!" : "Good Evening!";
          })()}</h2>
          <p>Here's what's happening in your community today.</p>
        </section>

        {/* MAIN PANEL CONTENT PORT */}
        <div className="content-wrapper">
          
          {/* TAB 1: DASHBOARD VIEW */}
          {activeTab === "dashboard" && (
            <>
              {/* Metric Cards Row (Enlarged by 30%) */}
              <section className="metrics-grid">
                <div className="card metric-card">
                  <div className="metric-icon-box" style={{ backgroundColor: "rgba(37, 99, 235, 0.08)", color: "var(--primary)" }}>
                    <Users size={24} />
                  </div>
                  <div className="metric-details">
                    <span className="metric-label">Community Members</span>
                    <span className="metric-value">{dashboard?.total_members ?? 0}</span>
                    <span className="metric-growth growth-up">+3% this month</span>
                  </div>
                </div>

                <div className="card metric-card">
                  <div className="metric-icon-box" style={{ backgroundColor: "rgba(16, 163, 74, 0.08)", color: "var(--success)" }}>
                    <MessageSquare size={24} />
                  </div>
                  <div className="metric-details">
                    <span className="metric-label">Parsed Messages</span>
                    <span className="metric-value">{dashboard?.total_messages ?? 0}</span>
                    <span className="metric-growth growth-up">+12% this week</span>
                  </div>
                </div>

                <div className="card metric-card">
                  <div className="metric-icon-box" style={{ backgroundColor: "rgba(139, 92, 246, 0.08)", color: "#8b5cf6" }}>
                    <Award size={24} />
                  </div>
                  <div className="metric-details">
                    <span className="metric-label">Top Contributor</span>
                    <span className="metric-value" style={{ fontSize: "1.1rem" }} title={dashboard?.most_active_member}>
                      {dashboard?.most_active_member ? dashboard.most_active_member.split(" (")[0] : "N/A"}
                    </span>
                    <span className="metric-growth" style={{ color: "var(--text-muted)" }}>Active participant</span>
                  </div>
                </div>

                <div className="card metric-card">
                  <div className="metric-icon-box" style={{ backgroundColor: "rgba(245, 158, 11, 0.08)", color: "var(--warning)" }}>
                    <Calendar size={24} />
                  </div>
                  <div className="metric-details">
                    <span className="metric-label">Peak Activity Date</span>
                    <span className="metric-value" style={{ fontSize: "1.1rem" }} title={dashboard?.most_active_day}>
                      {dashboard?.most_active_day ? dashboard.most_active_day.split(" (")[0] : "N/A"}
                    </span>
                    <span className="metric-growth growth-up">Highest chat load</span>
                  </div>
                </div>
              </section>

              {/* Graphical Overview Block */}
              {dashboard && dashboard.total_messages > 0 ? (
                <section className="charts-grid">
                  <div className="card">
                    <div className="chart-header">
                      <h3>Message Volume (Daily timeline)</h3>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Daily interaction levels</span>
                    </div>
                    {dashboard.message_volume.length > 0 ? (
                      <div className="chart-body" style={{ flexDirection: "column", height: "auto" }}>
                        <div style={{ position: "relative", width: "100%", height: "240px" }}>
                          <svg className="svg-chart" viewBox="0 0 500 240" preserveAspectRatio="none" style={{ height: "240px", width: "100%" }}>
                            <defs>
                              <linearGradient id="vol-gradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.15" />
                                <stop offset="100%" stopColor="var(--primary)" stopOpacity="0.0" />
                              </linearGradient>
                            </defs>
                            
                            {/* Y lines */}
                            <line x1="0" y1="60" x2="500" y2="60" className="chart-grid-line" />
                            <line x1="0" y1="120" x2="500" y2="120" className="chart-grid-line" />
                            <line x1="0" y1="180" x2="500" y2="180" className="chart-grid-line" />

                            {/* Y-axis Ticks & Labels */}
                            <text x="8" y="20" fill="var(--text-secondary)" fontSize="9" fontWeight="600">{maxVolume} msgs</text>
                            <text x="8" y="80" fill="var(--text-secondary)" fontSize="9" fontWeight="600">{Math.round(maxVolume * 0.75)}</text>
                            <text x="8" y="140" fill="var(--text-secondary)" fontSize="9" fontWeight="600">{Math.round(maxVolume * 0.5)}</text>
                            <text x="8" y="200" fill="var(--text-secondary)" fontSize="9" fontWeight="600">{Math.round(maxVolume * 0.25)}</text>
                            
                            {(() => {
                              const width = 500;
                              const height = 240;
                              const len = dashboard.message_volume.length;
                              const points = dashboard.message_volume.map((v, i) => {
                                const x = len > 1 ? (i * width) / (len - 1) : width / 2;
                                const y = height - (v.count / maxVolume) * (height - 30) - 15;
                                return { x, y, date: v.date, count: v.count };
                              });

                              const lineD = points.length > 0 ? `M ${points.map(p => `${p.x} ${p.y}`).join(" L ")}` : "";
                              const areaD = points.length > 0 ? `${lineD} L ${points[points.length - 1].x} ${height} L ${points[0].x} ${height} Z` : "";

                              return (
                                <>
                                  {areaD && <path d={areaD} fill="url(#vol-gradient)" />}
                                  {lineD && <path d={lineD} className="chart-line" />}
                                  {points.map((p, idx) => (
                                    <circle key={idx} cx={p.x} cy={p.y} r="3.5" className="chart-point">
                                      <title>{`${p.date}: ${p.count} messages`}</title>
                                    </circle>
                                  ))}
                                </>
                              );
                            })()}
                          </svg>
                          <div style={{ position: "absolute", bottom: -20, left: 0, right: 0, display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                            <span>{dashboard.message_volume[0]?.date}</span>
                            <span>{dashboard.message_volume[dashboard.message_volume.length - 1]?.date}</span>
                          </div>
                        </div>

                        {/* Legend & Explanation */}
                        <div style={{ marginTop: "2rem", borderTop: "1px solid var(--border-color)", paddingTop: "1rem" }}>
                          <div style={{ display: "flex", gap: "1rem", fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.5rem", alignItems: "center" }}>
                            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.25rem" }}>
                              <span style={{ width: "12px", height: "3px", backgroundColor: "var(--primary)", display: "inline-block" }}></span>
                              Daily message count timeline
                            </span>
                            <span style={{ color: "var(--text-muted)" }}>• Vertical axis displays count scale</span>
                          </div>
                          <p style={{ fontSize: "0.775rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                            <strong>Analysis Note:</strong> Tracks message counts chronologically. Spikes signify high engagement days (e.g., active topic debates or events), while troughs reflect standard off-hours. Hover dots show daily counts.
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "240px", color: "var(--text-muted)" }}>
                        No volume stats mapped.
                      </div>
                    )}
                  </div>

                  {/* Active Senders list */}
                  <div className="card">
                    <div className="chart-header">
                      <h3>Active Contributors</h3>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Top Senders</span>
                    </div>
                    <div className="senders-list">
                      {dashboard.top_senders.map((s, idx) => {
                        const percent = (s.count / maxSenderCount) * 100;
                        return (
                          <div key={idx} className="sender-row">
                            <div className="sender-avatar">
                              {s.sender.slice(0, 2).toUpperCase()}
                            </div>
                            <div className="sender-info-box">
                              <div className="sender-header">
                                <span className="sender-name" title={s.sender}>{s.sender}</span>
                                <span className="sender-count">{s.count} msgs</span>
                              </div>
                              <div className="sender-progress-bar">
                                <div className="sender-progress-fill" style={{ width: `${percent}%` }} />
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <div style={{ marginTop: "1.25rem", borderTop: "1px solid var(--border-color)", paddingTop: "0.75rem", fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.3 }}>
                      <strong>Participation Share:</strong> Shows message distributions of top contributors. Progress bars indicate count percentage relative to the most active sender.
                    </div>
                  </div>
                </section>
              ) : (
                // Dashboard empty state
                <section className="card" style={{ padding: "4rem", textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
                  <Database size={48} color="var(--text-muted)" style={{ opacity: 0.5 }} />
                  <h3 style={{ fontSize: "1.25rem", fontWeight: 600 }}>Get Started with Community Intelligence</h3>
                  <p style={{ color: "var(--text-secondary)", maxWidth: "460px", fontSize: "0.95rem" }}>
                    There are no knowledge base sources indexed yet. Please upload a WhatsApp chat export `.txt` file to initialize insights.
                  </p>
                  <button className="primary-btn" onClick={() => setActiveTab("sources")} style={{ marginTop: "1rem" }}>
                    <UploadCloud size={16} />
                    Import Chat Data
                  </button>
                </section>
              )}
            </>
          )}

          {/* TAB 2: AI RETRIEVAL CHAT */}
          {activeTab === "chat" && (
            <section className="card chat-container-box">
              <div className="chat-messages-area">
                {chat.map((item, idx) => (
                  <div key={idx} className="message-bubble-wrapper">
                    {/* User bubble */}
                    <div className="message-bubble bubble-user-style">{item.query}</div>
                    
                    {/* AI Bubble */}
                    <div className="message-bubble bubble-ai-style">
                      {item.response.observation ? (
                        <div className="ai-reasoning-container">
                          <div>
                            <div className="ai-reasoning-header obs">Factual Observations</div>
                            <div className="ai-reasoning-text">{item.response.observation}</div>
                          </div>
                          
                          {item.response.inference && (
                            <div>
                              <div className="ai-reasoning-header inf">Logical Inferences</div>
                              <div className="ai-reasoning-text">{item.response.inference}</div>
                            </div>
                          )}
                          
                          {item.response.recommendation && (
                            <div>
                              <div className="ai-reasoning-header rec">AI Recommendation</div>
                              <div className="ai-reasoning-text">{item.response.recommendation}</div>
                            </div>
                          )}

                          {/* Citations evidence */}
                          {item.response.evidence.length > 0 && (
                            <div className="evidence-section">
                              <div className="evidence-header" onClick={() => toggleEvidence(idx)}>
                                <span>View supporting logs ({item.response.evidence.length})</span>
                                {expandedEvidence[idx] ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                              </div>
                              {expandedEvidence[idx] && (
                                <div className="evidence-list">
                                  {item.response.evidence.map((ev, evIdx) => (
                                    <div key={evIdx} className="evidence-item">
                                      <div className="evidence-meta">
                                        {ev.sender} ({new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
                                      </div>
                                      <div className="evidence-text">"{ev.content}"</div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          <div className="chat-meta-footer">
                            <span className={`confidence-indicator confidence-${item.response.confidence.toLowerCase()}`}>
                              <ShieldAlert size={12} />
                              Confidence: {item.response.confidence}
                            </span>
                            <span>{item.response.confidence_reason}</span>
                          </div>
                        </div>
                      ) : (
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--text-secondary)", fontSize: "0.9rem" }}>
                          <Loader className="spinner" />
                          Context RAG Search in progress...
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                
                {chat.length === 0 && (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-secondary)", gap: "1rem", padding: "3rem" }}>
                    <MessageSquare size={44} style={{ color: "var(--text-muted)", opacity: 0.3 }} />
                    <h3 style={{ fontSize: "1.1rem", fontWeight: 600 }}>Interactive AI Assistant</h3>
                    <p style={{ textAlign: "center", fontSize: "0.85rem", maxWidth: "420px", color: "var(--text-secondary)" }}>
                      Ask questions grounded strictly in your community discussions. The platform uses semantic vector search and reconstructs full conversation threads to formulate answers.
                    </p>
                  </div>
                )}
                
                <div ref={chatEndRef} />
              </div>

              {/* Clickable suggested rounded cards */}
              <div className="suggested-section-grid" style={{ marginBottom: "1rem" }}>
                {suggestedQuestions.map((q: string, idx: number) => (
                  <div 
                    key={idx} 
                    className="suggested-question-card"
                    onClick={() => handleChatSubmit(q)}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                      <Sparkles size={14} color="var(--primary)" />
                      <span>{q}</span>
                    </div>
                    <ChevronRight size={14} color="var(--text-secondary)" />
                  </div>
                ))}
              </div>

              <div className="chat-input-row">
                <input 
                  type="text" 
                  className="chat-input-text" 
                  placeholder="Query conversation logs..." 
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleChatSubmit(queryInput)}
                  disabled={chatLoading || dashboard?.total_messages === 0}
                />
                <button 
                  className="primary-btn" 
                  onClick={() => handleChatSubmit(queryInput)}
                  disabled={chatLoading || !queryInput.trim() || dashboard?.total_messages === 0}
                >
                  Ask AI
                </button>
              </div>
            </section>
          )}

          {/* TAB 3: COMMUNITY REPORT */}
          {activeTab === "report" && (
            <section className="card">
              <div className="chart-header">
                <h3>Structured Community Intelligence Report</h3>
                <button 
                  className="primary-btn" 
                  onClick={handleGenerateReport} 
                  disabled={reportLoading || dashboard?.total_messages === 0}
                >
                  {reportLoading ? <Loader className="spinner" /> : <Sparkles size={16} />}
                  Generate Report
                </button>
              </div>

              {report ? (
                <div className="report-main-grid">
                  <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
                    <div className="report-card-section">
                      <span className="report-subtitle">Executive Summary</span>
                      <p className="report-text" style={{ fontSize: "1rem" }}>{report.executive_summary}</p>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
                      <div className="report-card-section">
                        <span className="report-subtitle">Most Discussed Topics</span>
                        <ul className="report-list">
                          {report.most_discussed_topics.map((t, idx) => (
                            <li key={idx} className="report-list-item">{t}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="report-card-section">
                        <span className="report-subtitle">Key Trends</span>
                        <ul className="report-list">
                          {report.interesting_trends.map((t, idx) => (
                            <li key={idx} className="report-list-item">{t}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem", borderLeft: "1px solid var(--border-color)", paddingLeft: "2.5rem" }}>
                    <div className="report-card-section">
                      <span className="report-subtitle">Community Mood & Tone</span>
                      <p className="report-text" style={{ fontStyle: "italic" }}>"{report.community_mood}"</p>
                    </div>

                    <div className="report-card-section">
                      <span className="report-subtitle">Top Contributors</span>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                        {report.active_contributors.map((c, idx) => (
                          <div key={idx} className="report-avatar-pill">
                            {c}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="report-card-section">
                      <span className="report-subtitle">Actionable Recommendations</span>
                      <ul className="report-list">
                        {report.ai_recommendations.map((r, idx) => (
                          <li key={idx} className="report-list-item" style={{ color: "var(--text-secondary)" }}>{r}</li>
                        ))}
                      </ul>
                    </div>

                    <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "1.25rem", marginTop: "auto", fontSize: "0.775rem", color: "var(--text-secondary)" }}>
                      <div>Report Confidence: <strong className="confidence-high">{report.confidence}</strong></div>
                      <div style={{ marginTop: "0.25rem" }}>{report.confidence_reason}</div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="report-empty-state">
                  <Sparkles size={48} color="var(--primary)" style={{ opacity: 0.8 }} />
                  <h4 className="report-empty-title">Generate Community Intelligence Report</h4>
                  <p className="report-empty-desc">
                    Generates a comprehensive analysis analyzing community mood, active contributors, trends, most discussed topics, and AI recommendations using local LLM synthesis.
                  </p>
                  <button 
                    className="primary-btn" 
                    onClick={handleGenerateReport} 
                    disabled={reportLoading || dashboard?.total_messages === 0}
                  >
                    {reportLoading && <Loader className="spinner" />}
                    Compile Report
                  </button>
                </div>
              )}
            </section>
          )}

          {/* TAB 4: ANALYTICS DETAIL */}
          {activeTab === "analytics" && (
            <section style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
              <div className="card" style={{ height: "auto" }}>
                <div className="chart-header">
                  <h3>Expanded Daily Message Volume</h3>
                  <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>Activity volume tracking</span>
                </div>
                {dashboard && dashboard.message_volume.length > 0 ? (
                  <div className="chart-body" style={{ height: "auto", flexDirection: "column" }}>
                    <div style={{ position: "relative", width: "100%", height: "300px" }}>
                      <svg className="svg-chart" viewBox="0 0 800 300" preserveAspectRatio="none" style={{ height: "300px", width: "100%" }}>
                        <defs>
                          <linearGradient id="vol-gradient-expanded" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.15" />
                            <stop offset="100%" stopColor="var(--primary)" stopOpacity="0.0" />
                          </linearGradient>
                        </defs>
                        <line x1="0" y1="75" x2="800" y2="75" className="chart-grid-line" />
                        <line x1="0" y1="150" x2="800" y2="150" className="chart-grid-line" />
                        <line x1="0" y1="225" x2="800" y2="225" className="chart-grid-line" />
                        
                        {/* Y-axis Ticks & Labels */}
                        <text x="10" y="25" fill="var(--text-secondary)" fontSize="10" fontWeight="600">{maxVolume} msgs</text>
                        <text x="10" y="95" fill="var(--text-secondary)" fontSize="10" fontWeight="600">{Math.round(maxVolume * 0.75)}</text>
                        <text x="10" y="170" fill="var(--text-secondary)" fontSize="10" fontWeight="600">{Math.round(maxVolume * 0.5)}</text>
                        <text x="10" y="245" fill="var(--text-secondary)" fontSize="10" fontWeight="600">{Math.round(maxVolume * 0.25)}</text>

                        {(() => {
                          const width = 800;
                          const height = 300;
                          const len = dashboard.message_volume.length;
                          const points = dashboard.message_volume.map((v, i) => {
                            const x = len > 1 ? (i * width) / (len - 1) : width / 2;
                            const y = height - (v.count / maxVolume) * (height - 40) - 20;
                            return { x, y, date: v.date, count: v.count };
                          });

                          const lineD = points.length > 0 ? `M ${points.map(p => `${p.x} ${p.y}`).join(" L ")}` : "";
                          const areaD = points.length > 0 ? `${lineD} L ${points[points.length - 1].x} ${height} L ${points[0].x} ${height} Z` : "";

                          return (
                            <>
                              {areaD && <path d={areaD} fill="url(#vol-gradient-expanded)" />}
                              {lineD && <path d={lineD} className="chart-line" strokeWidth="3" />}
                              {points.map((p, idx) => (
                                <circle key={idx} cx={p.x} cy={p.y} r="4" className="chart-point">
                                  <title>{`${p.date}: ${p.count} messages`}</title>
                                </circle>
                              ))}
                            </>
                          );
                        })()}
                      </svg>
                    </div>

                    {/* Legend & Explanation */}
                    <div style={{ marginTop: "1.5rem", borderTop: "1px solid var(--border-color)", paddingTop: "1rem", width: "100%" }}>
                      <div style={{ display: "flex", gap: "1rem", fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.5rem", alignItems: "center" }}>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: "0.25rem" }}>
                          <span style={{ width: "12px", height: "3px", backgroundColor: "var(--primary)", display: "inline-block" }}></span>
                          Daily Message Volume Curve
                        </span>
                        <span style={{ color: "var(--text-muted)" }}>• Visualizing active spikes over the custom workspace duration</span>
                      </div>
                      <p style={{ fontSize: "0.775rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                        <strong>Historical Overview:</strong> Shows daily frequency curves across all registered data sources. Spikes indicate peak event activity or intense group discussion threads, helping identify long-term engagement trends.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "300px", color: "var(--text-muted)" }}>
                    No data sources ready.
                  </div>
                )}
              </div>

              <div className="card" style={{ height: "auto" }}>
                <div className="chart-header">
                  <h3>Hourly Message Density</h3>
                  <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>Peak hourly distribution</span>
                </div>
                {dashboard && dashboard.active_hours.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                    <div style={{ display: "flex", gap: "1rem" }}>
                      {/* Y-axis indicator scale */}
                      <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", height: "240px", fontSize: "0.75rem", color: "var(--text-secondary)", paddingBottom: "24px", width: "48px", textAlign: "right" }}>
                        <span>{maxHourCount} msgs</span>
                        <span>{Math.round(maxHourCount * 0.75)}</span>
                        <span>{Math.round(maxHourCount * 0.5)}</span>
                        <span>{Math.round(maxHourCount * 0.25)}</span>
                        <span>0</span>
                      </div>
                      
                      {/* The hourly bars container */}
                      <div className="chart-body" style={{ height: "240px", gap: "4px", flex: 1, display: "flex", alignItems: "flex-end", borderBottom: "1px solid var(--border-color)", paddingBottom: "4px" }}>
                        {dashboard.active_hours.map((h, idx) => {
                          const percent = (h.count / maxHourCount) * 90;
                          return (
                            <div key={idx} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", height: "100%", justifyContent: "flex-end" }} title={`${h.hour}:00 - ${h.count} messages`}>
                              <div style={{ height: `${percent}%`, width: "70%", backgroundColor: "var(--primary-light)", border: "1px solid var(--primary)", borderRadius: "3px 3px 0 0", minHeight: h.count > 0 ? "2px" : "0" }} />
                              <span style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginTop: "4px" }}>{h.hour}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                    
                    {/* Legend & Explanation */}
                    <div style={{ marginTop: "0.5rem", borderTop: "1px solid var(--border-color)", paddingTop: "1rem" }}>
                      <div style={{ display: "flex", gap: "1rem", fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "0.75rem", alignItems: "center" }}>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: "0.25rem" }}>
                          <span style={{ width: "10px", height: "10px", backgroundColor: "var(--primary-light)", border: "1px solid var(--primary)", display: "inline-block", borderRadius: "2px" }}></span>
                          Hourly message volume
                        </span>
                        <span style={{ color: "var(--text-muted)" }}>• 24-hour horizontal distribution scale</span>
                      </div>
                      <p style={{ fontSize: "0.775rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                        <strong>Density Analysis:</strong> Identifies active windows throughout a 24-hour cycle. Ideal for highlighting peak coordination zones (e.g., lunch breaks or late evening syncs) and finding when users are most responsive.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "300px", color: "var(--text-muted)" }}>
                    No stats loaded.
                  </div>
                )}
              </div>
            </section>
          )}

          {/* TAB 5: MEMBERS LIST VIEW */}
          {activeTab === "members" && (
            <section className="card">
              <div className="chart-header">
                <h3>Community Directory</h3>
                <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                  {dashboard?.total_members ?? 0} unique participants
                </span>
              </div>
              <div className="senders-list" style={{ maxHeight: "none", overflow: "visible" }}>
                {dashboard && dashboard.top_senders.map((s, idx) => {
                  const percent = (s.count / maxSenderCount) * 100;
                  return (
                    <div key={idx} className="sender-row" style={{ paddingBottom: "1.25rem", borderBottom: "1px solid var(--border-color)" }}>
                      <div className="sender-avatar" style={{ width: "42px", height: "42px", fontSize: "1rem" }}>
                        {s.sender.slice(0, 2).toUpperCase()}
                      </div>
                      <div className="sender-info-box">
                        <div className="sender-header" style={{ marginBottom: "0.25rem" }}>
                          <span className="sender-name" style={{ fontSize: "0.95rem" }}>{s.sender}</span>
                          <span className="sender-count" style={{ fontSize: "0.875rem" }}>{s.count} messages</span>
                        </div>
                        <div className="sender-progress-bar" style={{ height: "8px" }}>
                          <div className="sender-progress-fill" style={{ width: `${percent}%` }} />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* TAB 6: DATA SOURCES & UPLOAD */}
          {activeTab === "sources" && (
            <section style={{ display: "flex", flexDirection: "column", gap: "2.5rem" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
                {/* Drag & Drop Upload Zone */}
                <div 
                  className="upload-container"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="upload-icon-container">
                    <UploadCloud size={32} />
                  </div>
                  <h3 className="upload-title">Drag & drop export files</h3>
                  <p className="upload-desc">Select exported WhatsApp .txt logs to sync</p>
                  <button className="primary-btn" disabled={uploadLoading}>
                    {uploadLoading ? <Loader className="spinner" /> : <UploadCloud size={16} />}
                    Choose File
                  </button>
                  <input 
                    type="file" 
                    ref={fileInputRef} 
                    className="file-input" 
                    accept=".txt" 
                    onChange={handleUpload}
                    disabled={uploadLoading}
                  />
                </div>

                {/* Indexing status vertical timeline */}
                <div className="card">
                  <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Indexing Pipeline Status</h3>
                  
                  {sources.some(s => s.status !== "ready") ? (
                    <div className="timeline-vertical">
                      {sources.filter(s => s.status !== "ready").map(s => {
                        const status = s.status;
                        const isFailed = status.startsWith("failed");
                        return (
                          <div key={s.id} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                            <div className="timeline-row complete">
                              <div className="timeline-node"><Check size={10} /></div>
                              <div className="timeline-info">
                                <span className="timeline-step-name">Uploaded</span>
                                <span className="timeline-step-desc">File "{s.name}" uploaded successfully.</span>
                              </div>
                            </div>
                            
                            <div className={`timeline-row ${["parsed", "storing", "stored", "indexing", "indexed", "ready"].includes(status) ? "complete" : status === "parsing" ? "active" : ""}`}>
                              <div className="timeline-node">{["parsed", "storing", "stored", "indexing", "indexed", "ready"].includes(status) ? <Check size={10} /> : null}</div>
                              <div className="timeline-info">
                                <span className="timeline-step-name">Parsed Messages</span>
                                <span className="timeline-step-desc">Chat logs split into message metadata.</span>
                              </div>
                            </div>

                            <div className={`timeline-row ${["stored", "indexing", "indexed", "ready"].includes(status) ? "complete" : status === "storing" ? "active" : ""}`}>
                              <div className="timeline-node">{["stored", "indexing", "indexed", "ready"].includes(status) ? <Check size={10} /> : null}</div>
                              <div className="timeline-info">
                                <span className="timeline-step-name">Stored Conversations</span>
                                <span className="timeline-step-desc">Messages grouped into SQLite conversation threads.</span>
                              </div>
                            </div>

                            <div className={`timeline-row ${["indexed", "ready"].includes(status) ? "complete" : status === "indexing" ? "active" : ""}`}>
                              <div className="timeline-node">{["indexed", "ready"].includes(status) ? <Check size={10} /> : null}</div>
                              <div className="timeline-info">
                                <span className="timeline-step-name">Indexed Embeddings</span>
                                <span className="timeline-step-desc">Generated sentence embeddings and indexed in ChromaDB.</span>
                              </div>
                            </div>

                            <div className={`timeline-row ${status === "ready" ? "complete" : isFailed ? "complete" : ""}`} style={{ opacity: status === "ready" ? 1 : 0.6 }}>
                              <div className="timeline-node">{status === "ready" ? <Check size={10} /> : isFailed ? <X size={10} /> : null}</div>
                              <div className="timeline-info">
                                <span className="timeline-step-name">{isFailed ? "Failed" : "AI Ready"}</span>
                                <span className="timeline-step-desc">{isFailed ? s.status : "Ready to process RAG queries."}</span>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyItems: "center", color: "var(--text-secondary)", gap: "0.5rem", padding: "3rem 1rem", textAlign: "center" }}>
                      <Check size={32} color="var(--success)" style={{ opacity: 0.8, marginBottom: "0.5rem" }} />
                      <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>All Systems Idle</span>
                      <span style={{ fontSize: "0.775rem" }}>Upload a new log file to trigger the pipeline indexing.</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Data Sources list */}
              <div>
                <h3 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1.25rem" }}>Registered Knowledge Bases</h3>
                
                <div className="sources-card-grid">
                  {sources.map(s => (
                    <div 
                      key={s.id} 
                      className={`card source-card ${selectedSource?.id === s.id ? "active" : ""}`}
                      style={{ borderLeft: selectedSource?.id === s.id ? "4px solid var(--primary)" : "" }}
                    >
                      <div className="source-card-header">
                        <div className="source-card-brand">
                          <Database size={16} color="var(--primary)" />
                          <span title={s.name} style={{ textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap", maxWidth: "160px" }}>{s.name}</span>
                        </div>
                        <span className={`badge badge-${s.status.startsWith("failed") ? "failed" : s.status.split(":")[0]}`}>
                          {s.status.startsWith("failed") ? "failed" : s.status}
                        </span>
                      </div>

                      <div style={{ fontSize: "1.35rem", fontWeight: 700, margin: "1rem 0 0.5rem 0", color: "var(--text-primary)" }}>
                        {s.message_count} <span style={{ fontSize: "0.8rem", fontWeight: 500, color: "var(--text-secondary)" }}>messages</span>
                      </div>

                      <div className="source-card-footer">
                        <span>{new Date(s.uploaded_at).toLocaleDateString()}</span>
                        <div style={{ display: "flex", gap: "0.25rem" }}>
                          <button 
                            className="secondary-btn" 
                            style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
                            onClick={() => s.status === "ready" && setSelectedSource(s)}
                          >
                            Select
                          </button>
                          <button className="delete-btn" onClick={() => handleDeleteSource(s.id)}>
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                  {sources.length === 0 && (
                    <div style={{ gridColumn: "1 / -1", textAlign: "center", color: "var(--text-secondary)", padding: "3rem 1rem", border: "1px solid var(--border-color)", borderRadius: "var(--radius-lg)" }}>
                      No data sources found. Upload your first WhatsApp export to begin.
                    </div>
                  )}
                </div>
              </div>
            </section>
          )}

          {/* TAB 7: SETTINGS VIEW */}
          {activeTab === "settings" && (
            <section className="card settings-section">
              <div className="chart-header" style={{ marginBottom: "2rem" }}>
                <h3>Platform Configuration Settings</h3>
                <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>Core API Abstraction Config</span>
              </div>
              
              <div className="settings-row">
                <div>
                  <div className="settings-label">Ollama Host URL</div>
                  <div className="settings-desc">Specify connection host endpoint for local Ollama APIs</div>
                </div>
                <input 
                  type="text" 
                  className="settings-input" 
                  value={ollamaUrl} 
                  onChange={(e) => setOllamaUrl(e.target.value)} 
                />
              </div>

              <div className="settings-row">
                <div>
                  <div className="settings-label">Active LLM Model</div>
                  <div className="settings-desc">Configure LLM model identifier pulled in Ollama</div>
                </div>
                <input 
                  type="text" 
                  className="settings-input" 
                  value={llmModel} 
                  onChange={(e) => setLlmModel(e.target.value)} 
                />
              </div>

              <div className="settings-row">
                <div>
                  <div className="settings-label">Reset Database Workspace</div>
                  <div className="settings-desc">Delete all uploaded sources, conversations, messages and vectors</div>
                </div>
                <div>
                  <button 
                    className="primary-btn" 
                    style={{ backgroundColor: "var(--danger)" }}
                    onClick={async () => {
                      if (!confirm("Are you sure you want to hard reset the database? This deletes all files and relational/vector tables.")) return;
                      // Deleting all sources one by one
                      for (const s of sources) {
                        try {
                          await api.deleteSource(s.id);
                        } catch (e) {
                          console.error(e);
                        }
                      }
                      setSelectedSource(null);
                      setChat([]);
                      setReport(null);
                      loadSources();
                    }}
                  >
                    Hard Reset Database
                  </button>
                </div>
              </div>
            </section>
          )}

          {/* TAB 8: CONVERSATION EXPLORER */}
          {activeTab === "explorer" && (
            <section style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
              {/* Highlight statistics metrics row */}
              <div className="metrics-grid">
                <div className="card metric-card">
                  <div className="metric-icon-box" style={{ backgroundColor: "rgba(37, 99, 235, 0.08)", color: "var(--primary)" }}>
                    <MessageSquare size={24} />
                  </div>
                  <div className="metric-details">
                    <span className="metric-label">Total Filtered</span>
                    <span className="metric-value">{explorerStats?.total_messages ?? 0}</span>
                    <span className="metric-growth" style={{ color: "var(--text-muted)" }}>messages matched</span>
                  </div>
                </div>

                <div className="card metric-card">
                  <div className="metric-icon-box" style={{ backgroundColor: "rgba(16, 163, 74, 0.08)", color: "var(--success)" }}>
                    <Users size={24} />
                  </div>
                  <div className="metric-details">
                    <span className="metric-label">Unique Senders</span>
                    <span className="metric-value">{explorerStats?.unique_members ?? 0}</span>
                    <span className="metric-growth" style={{ color: "var(--text-muted)" }}>active in range</span>
                  </div>
                </div>

                <div className="card metric-card">
                  <div className="metric-icon-box" style={{ backgroundColor: "rgba(139, 92, 246, 0.08)", color: "#8b5cf6" }}>
                    <Award size={24} />
                  </div>
                  <div className="metric-details">
                    <span className="metric-label">Top Contributor</span>
                    <span className="metric-value" style={{ fontSize: "1.1rem" }} title={explorerStats?.most_active_sender}>
                      {explorerStats?.most_active_sender ?? "N/A"}
                    </span>
                    <span className="metric-growth" style={{ color: "var(--text-muted)" }}>highest message share</span>
                  </div>
                </div>

                <div className="card metric-card">
                  <div className="metric-icon-box" style={{ backgroundColor: "rgba(245, 158, 11, 0.08)", color: "var(--warning)" }}>
                    <Clock size={24} />
                  </div>
                  <div className="metric-details">
                    <span className="metric-label">Peak Activity Hour</span>
                    <span className="metric-value" style={{ fontSize: "1.1rem" }}>
                      {explorerStats?.most_discussed_hour !== null && explorerStats?.most_discussed_hour !== undefined 
                        ? `${explorerStats.most_discussed_hour}:00` 
                        : "N/A"}
                    </span>
                    <span className="metric-growth" style={{ color: "var(--text-muted)" }}>
                      Avg: {explorerStats?.avg_messages_per_hour ?? 0}/hr
                    </span>
                  </div>
                </div>
              </div>

              {/* Grid content layout */}
              <div className="explorer-layout">
                {/* Left column - filters */}
                <div className="card filter-card" style={{ display: "flex", flexDirection: "column", gap: "1.25rem", height: "fit-content" }}>
                  <h3 style={{ fontSize: "1rem", fontWeight: 600, borderBottom: "1px solid var(--border-color)", paddingBottom: "0.75rem", marginBottom: "0.25rem" }}>Filters & Export</h3>
                  
                  <div className="filter-group">
                    <label>Time Period</label>
                    <select className="filter-control" value={expRange} onChange={(e) => setExpRange(e.target.value)}>
                      <option value="all">All Time</option>
                      <option value="1h">Last Hour</option>
                      <option value="6h">Last 6 Hours</option>
                      <option value="12h">Last 12 Hours</option>
                      <option value="24h">Last 24 Hours</option>
                      <option value="yesterday">Yesterday</option>
                      <option value="7d">Last 7 Days</option>
                      <option value="30d">Last 30 Days</option>
                      <option value="custom">Custom Range</option>
                    </select>
                  </div>

                  {expRange === "custom" && (
                    <>
                      <div className="filter-group">
                        <label>Start Date/Time</label>
                        <input type="datetime-local" className="filter-control" value={expStartDate} onChange={(e) => setExpStartDate(e.target.value)} />
                      </div>
                      <div className="filter-group">
                        <label>End Date/Time</label>
                        <input type="datetime-local" className="filter-control" value={expEndDate} onChange={(e) => setExpEndDate(e.target.value)} />
                      </div>
                    </>
                  )}

                  <div className="filter-group">
                    <label>Sender Username</label>
                    <input type="text" className="filter-control" placeholder="E.g. John Doe" value={expSender} onChange={(e) => setExpSender(e.target.value)} />
                  </div>

                  <div className="filter-group">
                    <label>Keyword / Text</label>
                    <input type="text" className="filter-control" placeholder="E.g. hackathon" value={expKeyword} onChange={(e) => setExpKeyword(e.target.value)} />
                  </div>

                  <div className="filter-group">
                    <label>Media content</label>
                    <select className="filter-control" value={expMedia} onChange={(e) => setExpMedia(e.target.value)}>
                      <option value="all">All Messages</option>
                      <option value="media_only">Media Only (&lt;Omitted&gt;)</option>
                      <option value="text_only">Exclude Media</option>
                    </select>
                  </div>

                  <div className="filter-group">
                    <label>Per Page Count</label>
                    <select className="filter-control" value={expLimit} onChange={(e) => setExpLimit(Number(e.target.value))}>
                      <option value={50}>50 messages</option>
                      <option value={100}>100 messages</option>
                      <option value={200}>200 messages</option>
                    </select>
                  </div>

                  <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                    <button className="primary-btn" style={{ flex: 1 }} onClick={() => loadExplorerMessages(true)}>
                      Apply Filters
                    </button>
                    <button className="secondary-btn" onClick={() => {
                      setExpRange("all");
                      setExpStartDate("");
                      setExpEndDate("");
                      setExpSender("");
                      setExpKeyword("");
                      setExpMedia("all");
                      setExpLimit(50);
                      setExpOffset(0);
                    }}>
                      Reset
                    </button>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", borderTop: "1px solid var(--border-color)", paddingTop: "1.25rem", marginTop: "0.5rem" }}>
                    <label style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.15rem" }}>Export Dataset</label>
                    <div style={{ display: "flex", gap: "0.5rem" }}>
                      <a 
                        className="secondary-btn" 
                        style={{ flex: 1, textDecoration: "none", display: "inline-flex", justifyContent: "center", alignItems: "center" }}
                        href={api.getExplorerExportUrl({
                          sourceId: selectedSource?.id || null,
                          relativeRange: expRange,
                          startDate: expRange === "custom" && expStartDate ? new Date(expStartDate).toISOString() : undefined,
                          endDate: expRange === "custom" && expEndDate ? new Date(expEndDate).toISOString() : undefined,
                          sender: expSender.trim() || undefined,
                          keyword: expKeyword.trim() || undefined,
                          hasMedia: expMedia === "media_only" ? true : expMedia === "text_only" ? false : null,
                          exportFormat: "txt"
                        })}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Export TXT
                      </a>
                      <a 
                        className="secondary-btn" 
                        style={{ flex: 1, textDecoration: "none", display: "inline-flex", justifyContent: "center", alignItems: "center" }}
                        href={api.getExplorerExportUrl({
                          sourceId: selectedSource?.id || null,
                          relativeRange: expRange,
                          startDate: expRange === "custom" && expStartDate ? new Date(expStartDate).toISOString() : undefined,
                          endDate: expRange === "custom" && expEndDate ? new Date(expEndDate).toISOString() : undefined,
                          sender: expSender.trim() || undefined,
                          keyword: expKeyword.trim() || undefined,
                          hasMedia: expMedia === "media_only" ? true : expMedia === "text_only" ? false : null,
                          exportFormat: "json"
                        })}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Export JSON
                      </a>
                    </div>
                  </div>
                </div>

                {/* Right column - conversation view */}
                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  {explorerLoading ? (
                    <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "380px", color: "var(--text-secondary)", width: "100%" }}>
                      <Loader className="spinner" style={{ animation: "spin 1s linear infinite" }} />
                      <span style={{ marginLeft: "0.5rem" }}>Filtering conversation logs...</span>
                    </div>
                  ) : explorerError ? (
                    <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "280px", color: "var(--danger)", padding: "2rem", width: "100%" }}>
                      <ShieldAlert size={36} />
                      <span style={{ marginTop: "1rem", fontWeight: 600 }}>Filtering Error</span>
                      <span style={{ fontSize: "0.85rem", marginTop: "0.25rem", color: "var(--text-secondary)" }}>{explorerError}</span>
                    </div>
                  ) : explorerMessages.length === 0 ? (
                    <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "380px", color: "var(--text-secondary)", padding: "2rem", width: "100%" }}>
                      <Database size={40} style={{ opacity: 0.3 }} />
                      <span style={{ marginTop: "1rem", fontWeight: 600 }}>No messages found</span>
                      <span style={{ fontSize: "0.85rem", marginTop: "0.25rem", textAlign: "center", maxWidth: "320px" }}>No messages matched your query or time period filters. Please try widening your settings.</span>
                    </div>
                  ) : (
                    <>
                      <div className="explorer-messages-container">
                        {(() => {
                          const elements = [];
                          for (let i = 0; i < explorerMessages.length; i++) {
                            const current = explorerMessages[i];
                            const prev = i > 0 ? explorerMessages[i - 1] : null;
                            
                            // Grouping criteria: same sender and timestamp within 5 minutes
                            const isGrouped = prev && 
                              current.sender === prev.sender && 
                              (new Date(current.timestamp).getTime() - new Date(prev.timestamp).getTime()) < 300000;

                            const timeStr = new Date(current.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                            
                            elements.push(
                              <div key={current.id} className="explorer-msg-group" style={{ marginTop: isGrouped ? "0.15rem" : "0.75rem" }}>
                                {!isGrouped && (
                                  <div className="explorer-msg-sender">
                                    {current.sender}
                                  </div>
                                )}
                                <div className="explorer-msg-bubble">
                                  <span className="explorer-msg-text">{current.content}</span>
                                  <span className="explorer-msg-time">{timeStr}</span>
                                </div>
                              </div>
                            );
                          }
                          return elements;
                        })()}
                      </div>

                      {/* Pagination buttons controls */}
                      <div className="explorer-pagination">
                        <button 
                          className="secondary-btn" 
                          style={{ padding: "0.5rem 1rem", fontSize: "0.85rem" }}
                          disabled={expOffset === 0} 
                          onClick={() => setExpOffset(prev => Math.max(0, prev - expLimit))}
                        >
                          Previous
                        </button>
                        <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                          Showing {expOffset + 1}–{Math.min(expOffset + expLimit, explorerCount)} of {explorerCount} messages
                        </span>
                        <button 
                          className="secondary-btn" 
                          style={{ padding: "0.5rem 1rem", fontSize: "0.85rem" }}
                          disabled={expOffset + expLimit >= explorerCount} 
                          onClick={() => setExpOffset(prev => prev + expLimit)}
                        >
                          Next
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </section>
          )}

        </div>
      </div>
    </div>
  );
}
