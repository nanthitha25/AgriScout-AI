"use client";

import React, { useState, useEffect } from "react";
import { 
  Plus, 
  Trash2, 
  Search, 
  RefreshCw, 
  Download, 
  TrendingUp, 
  Globe, 
  PieChart as PieIcon, 
  MessageSquare, 
  X, 
  ChevronUp, 
  ChevronDown, 
  Info,
  ExternalLink,
  Tag
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from "recharts";

// TypeScript interfaces
interface Startup {
  id: number;
  startup_name: string;
  startup_website: string;
  country: string;
  category: string;
  brief_description: string;
  funding_amount: string;
  funding_stage: string;
  news_type: string;
  source_url: string;
  news_summary: string;
  date_tracked: string;
}

interface Analytics {
  category_distribution: Array<{ name: string; value: number }>;
  news_type_distribution: Array<{ name: string; value: number }>;
  funding_by_country: Array<{ country: string; amount: number }>;
  funding_by_month: Array<{ month: string; amount: number }>;
  total_startups: number;
}

interface SimilarityResponse {
  target: string;
  similar_companies: Array<{
    startup_name: string;
    startup_website: string;
    brief_description: string;
    similarity: number;
  }>;
}

const API_BASE = "http://localhost:8001"; // Connect to our running FastAPI backend

const COLORS = ["#10b981", "#06b6d4", "#f59e0b", "#a855f7", "#ec4899", "#3b82f6", "#64748b"];

export default function Home() {
  // Main Data States
  const [startups, setStartups] = useState<Startup[]>([]);
  const [filteredStartups, setFilteredStartups] = useState<Startup[]>([]);
  const [analytics, setAnalytics] = useState<Analytics>({
    category_distribution: [],
    news_type_distribution: [],
    funding_by_country: [],
    funding_by_month: [],
    total_startups: 0
  });

  // UI Control States
  const [searchQuery, setSearchQuery] = useState("");
  const [newsTypeFilter, setNewsTypeFilter] = useState("All");
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [sortBy, setSortBy] = useState("newest");
  
  // Pipeline status state
  const [trackerStatus, setTrackerStatus] = useState({
    is_running: false,
    last_run_status: "Checking...",
    last_run_time: "Never"
  });

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    startup_name: "",
    startup_website: "",
    country: "",
    category: "Other",
    brief_description: "",
    funding_amount: "",
    funding_stage: "",
    news_type: "Other",
    source_url: "",
    news_summary: ""
  });

  // Similarity Drawer State
  const [similarityData, setSimilarityData] = useState<SimilarityResponse | null>(null);
  const [isSimilarityLoading, setIsSimilarityLoading] = useState(false);

  // Chat Assistant State
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<Array<{ sender: "user" | "ai"; text: string }>>([
    { sender: "ai", text: "Hello! I am AgriScout AI Q&A Assistant. You can ask me questions about your startup database (e.g. 'Show vertical farming companies' or 'What is the total funding in Finland?')." }
  ]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  // Loading indicator for fetching database
  const [isLoadingList, setIsLoadingList] = useState(true);

  // Fetch all initial data
  useEffect(() => {
    fetchStartupsData();
    fetchAnalytics();
    fetchTrackerStatus();
    
    // Poll tracker status every 5 seconds
    const interval = setInterval(fetchTrackerStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Sync filtration
  useEffect(() => {
    filterAndSort();
  }, [startups, searchQuery, newsTypeFilter, categoryFilter, sortBy]);

  const fetchStartupsData = async () => {
    setIsLoadingList(true);
    try {
      const res = await fetch(`${API_BASE}/api/startups`);
      if (res.ok) {
        const data = await res.json();
        setStartups(data);
      }
    } catch (e) {
      console.error("Error fetching startups:", e);
    } finally {
      setIsLoadingList(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/analytics`);
      if (res.ok) {
        const data = await res.json();
        setAnalytics(data);
      }
    } catch (e) {
      console.error("Error fetching analytics:", e);
    }
  };

  const fetchTrackerStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/tracker/status`);
      if (res.ok) {
        const data = await res.json();
        setTrackerStatus(data);
      }
    } catch (e) {
      console.error("Error fetching status:", e);
    }
  };

  // Filter and sort core logic
  const filterAndSort = () => {
    let list = [...startups];

    // Search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      list = list.filter(item => 
        item.startup_name.toLowerCase().includes(query) ||
        item.brief_description.toLowerCase().includes(query) ||
        item.news_summary.toLowerCase().includes(query) ||
        item.country.toLowerCase().includes(query)
      );
    }

    // News type filter
    if (newsTypeFilter !== "All") {
      list = list.filter(item => item.news_type.toLowerCase() === newsTypeFilter.toLowerCase());
    }

    // Category filter
    if (categoryFilter !== "All") {
      list = list.filter(item => item.category.toLowerCase() === categoryFilter.toLowerCase());
    }

    // Sort by criteria
    if (sortBy === "newest") {
      list.sort((a, b) => b.id - a.id);
    } else if (sortBy === "oldest") {
      list.sort((a, b) => a.id - b.id);
    } else if (sortBy === "alphabetical") {
      list.sort((a, b) => a.startup_name.localeCompare(b.startup_name));
    }

    setFilteredStartups(list);
  };

  const triggerScraper = async () => {
    if (trackerStatus.is_running) return;
    try {
      const res = await fetch(`${API_BASE}/api/tracker/run`, { method: "POST" });
      if (res.ok) {
        fetchTrackerStatus();
        alert("AgriScout AI discovery pipeline initiated successfully in the background.");
      } else {
        alert("Could not start tracking. Please check server logs.");
      }
    } catch (e) {
      alert("Backend connection failed.");
    }
  };

  const handleDelete = async (rowId: number) => {
    if (!confirm("Are you sure you want to remove this startup profile from intelligence records?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/startups/${rowId}`, { method: "DELETE" });
      if (res.ok) {
        fetchStartupsData();
        fetchAnalytics();
      }
    } catch (e) {
      alert("Delete call failed.");
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/api/startups`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        setIsModalOpen(false);
        setFormData({
          startup_name: "",
          startup_website: "",
          country: "",
          category: "Other",
          brief_description: "",
          funding_amount: "",
          funding_stage: "",
          news_type: "Other",
          source_url: "",
          news_summary: ""
        });
        fetchStartupsData();
        fetchAnalytics();
      }
    } catch (e) {
      alert("Failed to save startup.");
    }
  };

  const fetchSimilar = async (rowId: number) => {
    setIsSimilarityLoading(true);
    setSimilarityData(null);
    try {
      const res = await fetch(`${API_BASE}/api/startups/${rowId}/similar`);
      if (res.ok) {
        const data = await res.json();
        setSimilarityData(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsSimilarityLoading(false);
    }
  };

  const handleSendChatMessage = async () => {
    if (!chatInput.trim() || isChatLoading) return;
    const query = chatInput.trim();
    setChatInput("");
    setChatMessages(prev => [...prev, { sender: "user", text: query }]);
    setIsChatLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });
      if (res.ok) {
        const data = await res.json();
        setChatMessages(prev => [...prev, { sender: "ai", text: data.reply }]);
      }
    } catch (e) {
      setChatMessages(prev => [...prev, { sender: "ai", text: "Connection error. Failed to consult AI Assistant." }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  // Calculations for dashboard indicators
  const countRecentThisWeek = () => {
    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
    return startups.filter(s => {
      if (!s.date_tracked) return false;
      return new Date(s.date_tracked) >= oneWeekAgo;
    }).length;
  };

  return (
    <main className="min-h-screen bg-[#090d16] text-[#f3f4f6] relative font-sans overflow-x-hidden">
      {/* Visual background gradient blobs */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none overflow-hidden z-0">
        <div className="absolute top-[-10%] right-[10%] w-[500px] h-[500px] rounded-full bg-emerald-500/10 blur-[130px]"></div>
        <div className="absolute bottom-[-10%] left-[10%] w-[600px] h-[600px] rounded-full bg-cyan-500/10 blur-[130px]"></div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8 relative z-10 flex flex-col gap-8">
        
        {/* Navigation & Header */}
        <header className="bg-slate-900/60 backdrop-blur-md border border-slate-800 p-6 rounded-2xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-xl">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="bg-gradient-to-r from-emerald-500 to-cyan-500 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider text-white">Platform v2.0</span>
              {trackerStatus.is_running ? (
                <span className="flex items-center gap-1.5 text-xs text-amber-400 bg-amber-400/10 px-2.5 py-0.5 rounded-full border border-amber-400/20">
                  <span className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse"></span> Scraper Running
                </span>
              ) : (
                <span className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-400/10 px-2.5 py-0.5 rounded-full border border-emerald-400/20">
                  <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></span> Idle Scheduler
                </span>
              )}
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-100 to-emerald-400 bg-clip-text text-transparent">
              AgriScout AI
            </h1>
            <p className="text-sm text-slate-400 mt-1">Automated AgTech Startup Discovery & Market Intelligence System</p>
          </div>
          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            <button 
              onClick={triggerScraper}
              disabled={trackerStatus.is_running}
              className="flex-1 md:flex-none bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800 disabled:opacity-50 text-white font-semibold py-2.5 px-4 rounded-xl shadow-lg shadow-emerald-500/10 transition duration-200 flex items-center justify-center gap-2 text-sm"
            >
              <RefreshCw className={`w-4 h-4 ${trackerStatus.is_running ? "animate-spin" : ""}`} />
              Scan Industry News
            </button>
            
            <a 
              href={`${API_BASE}/api/report/weekly`}
              className="flex-1 md:flex-none bg-slate-800 hover:bg-slate-700 text-white font-semibold py-2.5 px-4 rounded-xl border border-slate-700 transition duration-200 flex items-center justify-center gap-2 text-sm text-center"
            >
              <Download className="w-4 h-4" />
              Intelligence PDF
            </a>
            
            <button 
              onClick={() => setIsModalOpen(true)}
              className="flex-1 md:flex-none bg-cyan-600 hover:bg-cyan-500 text-white font-semibold py-2.5 px-4 rounded-xl shadow-lg shadow-cyan-500/10 transition duration-200 flex items-center justify-center gap-2 text-sm"
            >
              <Plus className="w-4 h-4" />
              Add Startup
            </button>
          </div>
        </header>

        {/* Stats Section */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6" aria-label="System Stats">
          <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 p-6 rounded-2xl flex items-center gap-4 shadow-lg">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center text-2xl text-emerald-400">🌱</div>
            <div>
              <span className="block text-2xl font-bold text-white">{startups.length}</span>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Startups Logged</span>
            </div>
          </div>
          
          <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 p-6 rounded-2xl flex items-center gap-4 shadow-lg">
            <div className="w-12 h-12 rounded-xl bg-cyan-500/10 flex items-center justify-center text-2xl text-cyan-400">⏱️</div>
            <div>
              <span className="block text-sm font-semibold text-white truncate max-w-[200px]" title={trackerStatus.last_run_time}>
                {trackerStatus.last_run_time !== "Never" ? trackerStatus.last_run_time : "Never Started"}
              </span>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Last Pipeline Execution</span>
            </div>
          </div>
          
          <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 p-6 rounded-2xl flex items-center gap-4 shadow-lg">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center text-2xl text-purple-400">🔥</div>
            <div>
              <span className="block text-2xl font-bold text-white">{countRecentThisWeek()}</span>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Discovered This Week</span>
            </div>
          </div>
        </section>

        {/* Charts & Analytics Panel */}
        <section className="bg-slate-900/40 backdrop-blur-md border border-slate-800 p-6 rounded-2xl shadow-xl flex flex-col gap-6" aria-label="Market Intelligence Charts">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-4">
            <TrendingUp className="text-emerald-400 w-5 h-5" />
            <h2 className="text-lg font-bold text-white">Market Intelligence & Funding Analytics</h2>
          </div>
          
          {startups.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm">
              Analytics visualizations will render automatically once startups are discovered.
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Chart 1: Monthly funding */}
              <div className="bg-slate-950/40 border border-slate-800/60 p-4 rounded-xl min-h-[300px] flex flex-col">
                <h3 className="text-sm font-bold text-slate-300 mb-4">Funding Raised by Month ($ Millions)</h3>
                <div className="flex-1 w-full h-[220px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={analytics.funding_by_month}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="month" stroke="#94a3b8" fontSize={10} />
                      <YAxis stroke="#94a3b8" fontSize={10} />
                      <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155" }} />
                      <Bar dataKey="amount" fill="#10b981" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Chart 2: Category Distribution */}
              <div className="bg-slate-950/40 border border-slate-800/60 p-4 rounded-xl min-h-[300px] flex flex-col">
                <h3 className="text-sm font-bold text-slate-300 mb-4">Startups by AgTech Sector</h3>
                <div className="flex-1 w-full h-[220px] flex items-center justify-center">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={analytics.category_distribution}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {analytics.category_distribution.map((entry, idx) => (
                          <Cell key={`cell-${idx}`} fill={COLORS[idx % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155" }} />
                      <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: 9 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Chart 3: Top Country Funding */}
              <div className="bg-slate-950/40 border border-slate-800/60 p-4 rounded-xl min-h-[300px] flex flex-col">
                <h3 className="text-sm font-bold text-slate-300 mb-4">Funding by Country ($ Millions)</h3>
                <div className="flex-1 w-full h-[220px]">
                  {analytics.funding_by_country.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-slate-600 text-xs">No country funding records.</div>
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={analytics.funding_by_country} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis type="number" stroke="#94a3b8" fontSize={10} />
                        <YAxis dataKey="country" type="category" stroke="#94a3b8" fontSize={9} width={70} />
                        <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155" }} />
                        <Bar dataKey="amount" fill="#06b6d4" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>
            </div>
          )}
        </section>

        {/* Search & Filters row */}
        <section className="bg-slate-900/40 backdrop-blur-md border border-slate-800 p-4 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-4 shadow-lg">
          <div className="relative w-full md:max-w-md flex items-center">
            <Search className="absolute left-3.5 text-slate-400 w-4 h-4 pointer-events-none" />
            <input 
              type="text" 
              placeholder="Search startup name, keywords, description, or country..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-950/60 border border-slate-800 focus:border-emerald-500 rounded-xl outline-none text-sm text-[#f3f4f6] placeholder-slate-500 transition duration-150"
            />
          </div>
          
          <div className="flex flex-wrap items-center gap-4 w-full md:w-auto">
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">News:</span>
              <select 
                value={newsTypeFilter}
                onChange={(e) => setNewsTypeFilter(e.target.value)}
                className="w-full sm:w-auto bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-xs outline-none text-slate-300 focus:border-emerald-500"
              >
                <option value="All">All Events</option>
                <option value="Funding">Funding</option>
                <option value="Product Launch">Product Launch</option>
                <option value="Acquisition">Acquisition</option>
                <option value="Partnership">Partnership</option>
                <option value="Other">Other</option>
              </select>
            </div>
            
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Sector:</span>
              <select 
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="w-full sm:w-auto bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-xs outline-none text-slate-300 focus:border-emerald-500"
              >
                <option value="All">All Categories</option>
                <option value="Hydroponics">Hydroponics</option>
                <option value="Vertical Farming">Vertical Farming</option>
                <option value="Drone Technology">Drone Technology</option>
                <option value="Farm Robotics">Farm Robotics</option>
                <option value="FoodTech">FoodTech</option>
                <option value="ClimateTech">ClimateTech</option>
                <option value="Other">Other</option>
              </select>
            </div>
            
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Sort:</span>
              <select 
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full sm:w-auto bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-xs outline-none text-slate-300 focus:border-emerald-500"
              >
                <option value="newest">Newest Log</option>
                <option value="oldest">Oldest Log</option>
                <option value="alphabetical">Name A-Z</option>
              </select>
            </div>
          </div>
        </section>

        {/* Startups List / Grid */}
        <section className="min-h-[300px]">
          {isLoadingList ? (
            <div className="py-20 flex flex-col items-center justify-center gap-3">
              <div className="w-10 h-10 border-4 border-slate-800 rounded-full border-t-emerald-500 animate-spin"></div>
              <p className="text-slate-500 text-sm">Consulting data intelligence logs...</p>
            </div>
          ) : filteredStartups.length === 0 ? (
            <div className="bg-slate-900/20 border border-dashed border-slate-800 p-12 text-center rounded-2xl flex flex-col items-center gap-3">
              <span className="text-4xl">🚜</span>
              <h3 className="text-lg font-bold text-slate-300">No AgTech Startups Discovered</h3>
              <p className="text-sm text-slate-500 max-w-sm">Try running the Scraper to crawl recent news feeds or adjust search filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredStartups.map((startup) => {
                // Formatting links
                let websiteLink = startup.startup_website;
                if (websiteLink !== "Not Mentioned" && !/^https?:\/\//i.test(websiteLink)) {
                  websiteLink = `http://${websiteLink}`;
                }
                
                return (
                  <article key={startup.id} className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-2xl flex flex-col h-full shadow-lg hover:border-emerald-500/40 hover:-translate-y-1 transition duration-200 relative overflow-hidden group">
                    <div className="absolute top-0 left-0 w-full h-[3px] bg-gradient-to-r from-emerald-500 to-cyan-500"></div>
                    
                    {/* Card Header */}
                    <div className="p-5 flex justify-between items-start border-b border-slate-800/40">
                      <div>
                        <h3 className="text-base font-bold text-white mb-0.5 group-hover:text-emerald-400 transition-colors">
                          {startup.startup_name}
                        </h3>
                        <div className="flex flex-wrap items-center gap-2 mt-1">
                          <span className="text-[10px] font-bold text-cyan-400 bg-cyan-400/10 px-2 py-0.5 rounded border border-cyan-400/20">
                            {startup.category}
                          </span>
                          {startup.startup_website !== "Not Mentioned" ? (
                            <a href={websiteLink} target="_blank" rel="noopener noreferrer" className="text-[10px] text-slate-400 hover:text-white flex items-center gap-0.5">
                              <Globe className="w-2.5 h-2.5" /> Domain <ExternalLink className="w-2 h-2" />
                            </a>
                          ) : (
                            <span className="text-[10px] text-slate-500">No URL</span>
                          )}
                        </div>
                      </div>
                      <button 
                        onClick={() => handleDelete(startup.id)}
                        className="text-slate-500 hover:text-red-500 p-1.5 hover:bg-red-500/15 rounded-lg transition duration-150"
                        title="Delete record"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Description Body */}
                    <div className="p-5 flex-1 flex flex-col gap-4">
                      <p className="text-xs text-slate-300 leading-relaxed font-light">
                        {startup.brief_description}
                      </p>

                      <div className="bg-slate-950/40 border border-slate-800/50 p-3.5 rounded-xl">
                        <span className="text-[9px] font-bold text-emerald-400 uppercase tracking-widest block mb-1">AI Intel Summary</span>
                        <p className="text-[11px] text-slate-400 leading-normal">{startup.news_summary}</p>
                      </div>
                    </div>

                    {/* Metadata Footer */}
                    <div className="p-5 bg-slate-950/20 border-t border-slate-800/40 flex justify-between items-center gap-3">
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[9px] text-slate-500 uppercase tracking-wider">Country / Funding</span>
                        <span className="text-xs font-semibold text-slate-300">
                          📍 {startup.country} | 💵 {startup.funding_amount}
                        </span>
                      </div>
                      <button 
                        onClick={() => fetchSimilar(startup.id)}
                        className="text-[10px] bg-slate-800 hover:bg-slate-700 hover:text-emerald-400 font-semibold px-2.5 py-1.5 rounded-lg border border-slate-700 transition"
                      >
                        Find Similar
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </div>

      {/* Floating AI Chat Assistant Panel */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
        {isChatOpen ? (
          <div className="w-[360px] h-[450px] bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden mb-3 animate-slideUp">
            <header className="bg-slate-950/60 p-4 border-b border-slate-800 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <MessageSquare className="text-emerald-400 w-4 h-4" />
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">AgriScout AI Chat</h3>
              </div>
              <button onClick={() => setIsChatOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </header>
            
            <div className="flex-1 p-4 overflow-y-auto flex flex-col gap-3 text-xs">
              {chatMessages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] rounded-xl p-3 leading-relaxed whitespace-pre-line ${
                    msg.sender === "user" 
                      ? "bg-emerald-600 text-white rounded-br-none" 
                      : "bg-slate-800 text-slate-300 rounded-bl-none border border-slate-700"
                  }`}>
                    {msg.text}
                  </div>
                </div>
              ))}
              {isChatLoading && (
                <div className="flex justify-start">
                  <div className="bg-slate-800 border border-slate-700 rounded-xl p-3 rounded-bl-none flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"></span>
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce delay-75"></span>
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce delay-150"></span>
                  </div>
                </div>
              )}
            </div>

            <div className="p-3 border-t border-slate-800 bg-slate-950/60 flex items-center gap-2">
              <input 
                type="text" 
                placeholder="Ask about AgTech startups..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSendChatMessage();
                }}
                className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs outline-none text-slate-200 focus:border-emerald-500"
              />
              <button 
                onClick={handleSendChatMessage}
                disabled={isChatLoading}
                className="bg-emerald-600 hover:bg-emerald-500 font-semibold p-2 rounded-lg text-white transition disabled:opacity-50"
              >
                Send
              </button>
            </div>
          </div>
        ) : null}
        
        <button 
          onClick={() => setIsChatOpen(!isChatOpen)}
          className="bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white font-bold p-3.5 rounded-full shadow-2xl transition duration-200 hover:-translate-y-0.5"
          title="Open AI Chat Assistant"
        >
          {isChatOpen ? <ChevronDown className="w-5 h-5" /> : <MessageSquare className="w-5 h-5" />}
        </button>
      </div>

      {/* Manual Add Modal Overlay */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-[#05070c]/70 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 shadow-2xl animate-slideUp">
            <div className="flex justify-between items-center border-b border-slate-800 pb-4 mb-6">
              <h3 className="text-lg font-bold text-white">Record Startup Discovery Manually</h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleManualSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1 md:col-span-2">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Startup Name *</label>
                <input 
                  type="text" required placeholder="e.g. Solar Foods"
                  value={formData.startup_name}
                  onChange={(e) => setFormData({...formData, startup_name: e.target.value})}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none text-slate-200 focus:border-cyan-500"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Official Website</label>
                <input 
                  type="text" placeholder="e.g. solarfoods.com"
                  value={formData.startup_website}
                  onChange={(e) => setFormData({...formData, startup_website: e.target.value})}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none text-slate-200 focus:border-cyan-500"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Country</label>
                <input 
                  type="text" placeholder="e.g. Finland"
                  value={formData.country}
                  onChange={(e) => setFormData({...formData, country: e.target.value})}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none text-slate-200 focus:border-cyan-500"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Category</label>
                <select 
                  value={formData.category}
                  onChange={(e) => setFormData({...formData, category: e.target.value})}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none text-slate-300 focus:border-cyan-500"
                >
                  <option value="Hydroponics">Hydroponics</option>
                  <option value="Vertical Farming">Vertical Farming</option>
                  <option value="Drone Technology">Drone Technology</option>
                  <option value="Farm Robotics">Farm Robotics</option>
                  <option value="FoodTech">FoodTech</option>
                  <option value="ClimateTech">ClimateTech</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">News Event Type</label>
                <select 
                  value={formData.news_type}
                  onChange={(e) => setFormData({...formData, news_type: e.target.value})}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none text-slate-300 focus:border-cyan-500"
                >
                  <option value="Funding">Funding</option>
                  <option value="Product Launch">Product Launch</option>
                  <option value="Acquisition">Acquisition</option>
                  <option value="Partnership">Partnership</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Funding Stage</label>
                <input 
                  type="text" placeholder="e.g. Seed, Series A, N/A"
                  value={formData.funding_stage}
                  onChange={(e) => setFormData({...formData, funding_stage: e.target.value})}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none text-slate-200 focus:border-cyan-500"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Funding Amount</label>
                <input 
                  type="text" placeholder="e.g. $10M, N/A"
                  value={formData.funding_amount}
                  onChange={(e) => setFormData({...formData, funding_amount: e.target.value})}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none text-slate-200 focus:border-cyan-500"
                />
              </div>

              <div className="flex flex-col gap-1 md:col-span-2">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Source URL</label>
                <input 
                  type="text" placeholder="e.g. https://techcrunch.com/article-url"
                  value={formData.source_url}
                  onChange={(e) => setFormData({...formData, source_url: e.target.value})}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none text-slate-200 focus:border-cyan-500"
                />
              </div>

              <div className="flex flex-col gap-1 md:col-span-2">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Brief Description *</label>
                <textarea 
                  required rows={2} placeholder="Explain the core product and technology..."
                  value={formData.brief_description}
                  onChange={(e) => setFormData({...formData, brief_description: e.target.value})}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none text-slate-200 focus:border-cyan-500"
                />
              </div>

              <div className="flex flex-col gap-1 md:col-span-2">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">News Summary *</label>
                <textarea 
                  required rows={2} placeholder="Explain why the company is in the news..."
                  value={formData.news_summary}
                  onChange={(e) => setFormData({...formData, news_summary: e.target.value})}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-sm outline-none text-slate-200 focus:border-cyan-500"
                />
              </div>

              <div className="flex justify-end gap-3 md:col-span-2 border-t border-slate-800 pt-4 mt-2">
                <button type="button" onClick={() => setIsModalOpen(false)} className="bg-slate-800 hover:bg-slate-700 font-semibold px-4 py-2 rounded-xl text-sm transition">
                  Cancel
                </button>
                <button type="submit" className="bg-cyan-600 hover:bg-cyan-500 font-semibold px-4 py-2 rounded-xl text-sm transition text-white shadow-lg shadow-cyan-500/10">
                  Save Discovery
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Similar Companies Drawer/Overlay Modal */}
      {similarityData && (
        <div className="fixed inset-0 z-50 bg-[#05070c]/70 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl animate-slideUp">
            <div className="flex justify-between items-center border-b border-slate-800 pb-4 mb-4">
              <div className="flex items-center gap-2">
                <Info className="text-emerald-400 w-4 h-4" />
                <h3 className="text-base font-bold text-white">AI Similarity Insights</h3>
              </div>
              <button onClick={() => setSimilarityData(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-400 mb-4">
              Below are the top recommendations matching <b>{similarityData.target}</b>, calculated locally based on description semantic vector embeddings.
            </p>

            <div className="flex flex-col gap-3">
              {similarityData.similar_companies.length === 0 ? (
                <p className="text-xs text-slate-500 py-4 text-center">No other startups found in database to compare.</p>
              ) : (
                similarityData.similar_companies.map((sim, idx) => (
                  <div key={idx} className="bg-slate-950/50 border border-slate-800 p-4 rounded-xl flex flex-col gap-2">
                    <div className="flex justify-between items-start">
                      <h4 className="text-sm font-bold text-white">{sim.startup_name}</h4>
                      <span className="text-[10px] font-bold text-emerald-400 bg-emerald-400/10 border border-emerald-400/25 px-2 py-0.5 rounded-full">
                        {Math.round(sim.similarity * 100)}% Match
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">{sim.brief_description}</p>
                    {sim.startup_website !== "Not Mentioned" && (
                      <a 
                        href={sim.startup_website.startsWith("http") ? sim.startup_website : `http://${sim.startup_website}`} 
                        target="_blank" rel="noopener noreferrer"
                        className="text-[10px] text-cyan-400 hover:underline flex items-center gap-1 self-start"
                      >
                        🌐 Domain <ExternalLink className="w-2 h-2" />
                      </a>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="flex justify-end mt-6">
              <button onClick={() => setSimilarityData(null)} className="bg-slate-800 hover:bg-slate-700 font-semibold px-4 py-2 rounded-xl text-sm transition">
                Close Insights
              </button>
            </div>
          </div>
        </div>
      )}

      {isSimilarityLoading && (
        <div className="fixed inset-0 z-50 bg-[#05070c]/50 backdrop-blur-sm flex items-center justify-center">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl flex flex-col items-center gap-3 shadow-2xl">
            <div className="w-8 h-8 border-4 border-slate-800 rounded-full border-t-emerald-500 animate-spin"></div>
            <p className="text-slate-400 text-xs font-semibold">Comparing vector descriptions...</p>
          </div>
        </div>
      )}
    </main>
  );
}
