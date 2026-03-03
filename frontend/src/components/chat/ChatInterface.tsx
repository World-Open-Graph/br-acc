import { useCallback, useEffect, useRef, useState } from "react";
import { MessageCircle, Send, Sparkles, X, Plus, Trash2, History, ChevronLeft } from "lucide-react";
import { addJourneyEntry } from "@/lib/journey";
import {
  sendChatMessage,
  listConversations,
  createConversation,
  getConversation,
  deleteConversation,
  type ChatEntityCard,
  type ChatResponse,
  type ConversationSummary,
} from "@/api/client";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  entities?: ChatEntityCard[];
  suggestions?: string[];
  evidence_chain?: { tool: string; source: string; result_count: number }[];
  cost_usd?: number;
  loading?: boolean;
}

const ENTITY_TYPE_COLORS: Record<string, string> = {
  company: "#3b82f6",
  person: "#8b5cf6",
  contract: "#f59e0b",
  sanction: "#ef4444",
  publicoffice: "#10b981",
  embargo: "#f97316",
  convenio: "#06b6d4",
  election: "#ec4899",
  finance: "#84cc16",
};

const ENTITY_TYPE_LABELS: Record<string, string> = {
  company: "Empresa",
  person: "Pessoa",
  contract: "Contrato",
  sanction: "Sanção",
  publicoffice: "Cargo Público",
  embargo: "Embargo",
  convenio: "Convênio",
  election: "Eleição",
  finance: "Financeiro",
};

const ACTIVE_CONV_KEY = "egos_active_conv";

export function ChatInterface({ embedded = false }: { embedded?: boolean }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isOpen, setIsOpen] = useState(embedded);
  const [isLoading, setIsLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConvId, setActiveConvId] = useState<string>(() => {
    try { return localStorage.getItem(ACTIVE_CONV_KEY) ?? ""; } catch { return ""; }
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const loadWelcomeMessage = useCallback(() => {
    fetch("/api/v1/meta/stats")
      .then((r) => r.json())
      .then((s) => {
        const nodes = Math.round(s.total_nodes / 1000);
        const rels = Math.round(s.total_relationships / 1000);
        const sources = s.data_sources || 108;
        setMessages([{
          id: "welcome",
          role: "assistant",
          text: `Olá! Sou o agente investigativo do **EGOS Inteligência**.\n\n🔍 **${nodes} mil entidades** e **${rels} mil conexões** em dados públicos brasileiros.\n📊 **24 ferramentas** integradas em **${sources} fontes** (Portal da Transparência, DataJud, BNMP, Interpol, PNCP, OAB, e mais).\n\n**Você não precisa de CNPJ ou nome completo!** Escolha uma sugestão abaixo ou digite:\n- 🏙️ Uma **cidade** (ex: "Uberlândia", "Manaus")\n- 👤 Um **nome** (parcial ok: "Silva", "Bolsonaro")\n- 🏢 Uma **empresa** (nome fantasia: "Odebrecht")\n- 📋 Um **tema** ("licitações SP", "trabalho escravo")\n\n⚡ Modelo: GPT-4o-mini · Custo por consulta: ~$0.001`,
          suggestions: [
            "Políticos de São Paulo",
            "Empresas sancionadas que ainda recebem contratos",
            "Emendas parlamentares Minas Gerais 2024",
            "Deputados que mais gastaram com cartão corporativo",
            "Lista suja trabalho escravo",
            "Licitações suspeitas Rio de Janeiro",
            "Mandados de prisão pendentes",
            "Recuperações judiciais recentes TJSP",
          ],
        }]);
      })
      .catch(() => {
        setMessages([{
          id: "welcome",
          role: "assistant",
          text: "Olá! Sou o agente investigativo do **EGOS Inteligência**.\n\n**Você não precisa de CNPJ!** Digite uma cidade, nome, empresa ou tema para começar.\n\n⚡ Modelo: GPT-4o-mini",
          suggestions: [
            "Políticos de São Paulo",
            "Empresas sancionadas com contratos",
            "Emendas parlamentares 2024",
            "Deputados que mais gastaram",
            "Lista suja trabalho escravo",
            "Licitações suspeitas",
            "Mandados de prisão pendentes",
            "Recuperações judiciais TJSP",
          ],
        }]);
      });
  }, []);

  // Load conversation from server when activeConvId changes
  useEffect(() => {
    if (!isOpen) return;
    if (activeConvId) {
      getConversation(activeConvId)
        .then((conv) => {
          if (conv.messages && conv.messages.length > 0) {
            setMessages(conv.messages.map((m, i) => ({
              id: `${m.role}-${i}`,
              role: m.role as "user" | "assistant",
              text: m.content,
            })));
          } else {
            loadWelcomeMessage();
          }
        })
        .catch(() => loadWelcomeMessage());
    } else {
      loadWelcomeMessage();
    }
  }, [isOpen, activeConvId, loadWelcomeMessage]);

  // Load conversation list when history panel opens
  useEffect(() => {
    if (showHistory) {
      listConversations()
        .then((res) => setConversations(res.conversations ?? []))
        .catch(() => setConversations([]));
    }
  }, [showHistory]);

  const handleNewConversation = useCallback(async () => {
    try {
      const conv = await createConversation();
      setActiveConvId(conv.id);
      localStorage.setItem(ACTIVE_CONV_KEY, conv.id);
      setMessages([]);
      setShowHistory(false);
      loadWelcomeMessage();
      // Refresh list
      listConversations().then((res) => setConversations(res.conversations ?? [])).catch(() => {});
    } catch {
      // Fallback: just clear messages
      setActiveConvId("");
      localStorage.removeItem(ACTIVE_CONV_KEY);
      setMessages([]);
      loadWelcomeMessage();
    }
  }, [loadWelcomeMessage]);

  const handleSwitchConversation = useCallback((convId: string) => {
    setActiveConvId(convId);
    localStorage.setItem(ACTIVE_CONV_KEY, convId);
    setShowHistory(false);
  }, []);

  const handleDeleteConversation = useCallback(async (convId: string) => {
    await deleteConversation(convId).catch(() => {});
    setConversations((prev) => prev.filter((c) => c.id !== convId));
    if (convId === activeConvId) {
      setActiveConvId("");
      localStorage.removeItem(ACTIVE_CONV_KEY);
      loadWelcomeMessage();
    }
  }, [activeConvId, loadWelcomeMessage]);

  const handleSend = useCallback(async (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg || isLoading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      text: msg,
    };

    const loadingMsg: ChatMessage = {
      id: `loading-${Date.now()}`,
      role: "assistant",
      text: "",
      loading: true,
    };

    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setInput("");
    setIsLoading(true);
      addJourneyEntry({ type: "chat", title: msg.slice(0, 80), query: msg, url: window.location.pathname, description: "Chat EGOS" });

    try {
      // Auto-create conversation on first message if none active
      let convId = activeConvId;
      if (!convId) {
        try {
          const conv = await createConversation(msg.slice(0, 60));
          convId = conv.id;
          setActiveConvId(convId);
          localStorage.setItem(ACTIVE_CONV_KEY, convId);
        } catch { /* continue without persistence */ }
      }
      const response: ChatResponse = await sendChatMessage(msg, convId || undefined);
      setMessages((prev) =>
        prev.filter((m) => !m.loading).concat({
          id: `assistant-${Date.now()}`,
          role: "assistant",
          text: response.reply,
          entities: response.entities,
          suggestions: response.suggestions,
          evidence_chain: response.evidence_chain,
          cost_usd: response.cost_usd,
        }),
      );
    } catch {
      setMessages((prev) =>
        prev.filter((m) => !m.loading).concat({
          id: `error-${Date.now()}`,
          role: "assistant",
          text: "Desculpe, houve um erro. Tente novamente.",
          suggestions: ["Tentar novamente"],
        }),
      );
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading]);

  const handleEntityClick = useCallback((entity: ChatEntityCard) => {
    addJourneyEntry({
      type: "entity",
      title: entity.name,
      description: entity.type,
      entityId: entity.id,
      entityType: entity.type,
      url: `/app/analysis/${entity.id}`,
    });
    window.open(`/app/analysis/${entity.id}`, "_blank", "noopener,noreferrer");
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  const renderMarkdown = (text: string) => {
    let html = text
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color:#00e5c3;text-decoration:underline">$1</a>');
    // Auto-link bare URLs (skip already linked)
    html = html.replace(/(^|[^"'])(https?:\/\/[^\s<]+)/g, '$1<a href="$2" target="_blank" rel="noopener noreferrer" style="color:#00e5c3;text-decoration:underline">$2</a>');
    return html.replace(/\n/g, "<br/>");
  };

  // Floating button mode
  if (!embedded && !isOpen) {
    return (
      <button
        onClick={() => { setIsOpen(true); setTimeout(() => inputRef.current?.focus(), 100); }}
        style={{
          position: "fixed", bottom: 80, right: 16, zIndex: 100,
          width: 56, height: 56, borderRadius: "50%",
          background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
          border: "none", cursor: "pointer",
          display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: "0 4px 20px rgba(59,130,246,0.4)",
        }}
      >
        <MessageCircle size={24} color="white" />
      </button>
    );
  }

  const containerStyle: React.CSSProperties = embedded
    ? {
        width: "100%", margin: "0 auto",
        display: "flex", flexDirection: "column",
        height: "min(78vh, 680px)", minHeight: 480,
        background: "#0c1210",
        borderRadius: 14, border: "1px solid rgba(255,255,255,0.08)",
        overflow: "hidden",
        boxShadow: "0 8px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04)",
      }
    : {
        position: "fixed", bottom: 80, right: 16, zIndex: 100,
        width: "min(420px, calc(100vw - 32px))", height: "min(78vh, 680px)",
        display: "flex", flexDirection: "column",
        background: "#0c1210",
        borderRadius: 14, border: "1px solid rgba(255,255,255,0.08)",
        boxShadow: "0 8px 40px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.04)",
        overflow: "hidden",
      };

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "14px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)",
        background: "#111a16",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8,
            background: "linear-gradient(135deg, #00e5c3, #3b82f6)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Sparkles size={15} color="white" />
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontWeight: 600, fontSize: 13, color: "#e8ede9", lineHeight: 1.2 }}>
              EGOS Inteligência
            </span>
            <span style={{ fontSize: 10, color: "#5a6b60", fontFamily: "var(--font-mono, monospace)", letterSpacing: "0.05em" }}>
              Agente de pesquisa pública
            </span>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{
            width: 6, height: 6, borderRadius: "50%",
            background: "#00e5c3",
            boxShadow: "0 0 8px rgba(0,229,195,0.5)",
          }} />
          <button
            onClick={handleNewConversation}
            title="Nova conversa"
            style={{ background: "none", border: "none", cursor: "pointer", padding: 4 }}
          >
            <Plus size={16} color="#5a6b60" />
          </button>
          <button
            onClick={() => setShowHistory((v) => !v)}
            title="Histórico de conversas"
            style={{ background: "none", border: "none", cursor: "pointer", padding: 4 }}
          >
            <History size={16} color={showHistory ? "#00e5c3" : "#5a6b60"} />
          </button>
          {!embedded && (
            <button
              onClick={() => setIsOpen(false)}
              style={{ background: "none", border: "none", cursor: "pointer", padding: 4 }}
            >
              <X size={18} color="#5a6b60" />
            </button>
          )}
        </div>
      </div>

      {/* Conversation History Panel */}
      {showHistory && (
        <div style={{
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          background: "#0e1512",
          maxHeight: 240, overflowY: "auto",
          scrollbarWidth: "thin", scrollbarColor: "rgba(255,255,255,0.1) transparent",
        }}>
          <div style={{ padding: "10px 14px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: "#94a39a", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              Conversas anteriores
            </span>
            <button
              onClick={() => setShowHistory(false)}
              style={{ background: "none", border: "none", cursor: "pointer", padding: 2 }}
            >
              <ChevronLeft size={14} color="#5a6b60" style={{ transform: "rotate(-90deg)" }} />
            </button>
          </div>
          {conversations.length === 0 ? (
            <div style={{ padding: "8px 14px 14px", fontSize: 12, color: "#5a6b60" }}>
              Nenhuma conversa salva ainda.
            </div>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "8px 14px", cursor: "pointer",
                  background: conv.id === activeConvId ? "rgba(0,229,195,0.08)" : "transparent",
                  borderLeft: conv.id === activeConvId ? "2px solid #00e5c3" : "2px solid transparent",
                  transition: "all 100ms ease-out",
                }}
                onClick={() => handleSwitchConversation(conv.id)}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: 12, color: "#e8ede9", fontWeight: 500,
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}>
                    {conv.title}
                  </div>
                  <div style={{ fontSize: 10, color: "#5a6b60", marginTop: 2 }}>
                    {conv.message_count} msgs · {new Date(conv.updated_at * 1000).toLocaleDateString("pt-BR")}
                  </div>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteConversation(conv.id); }}
                  style={{ background: "none", border: "none", cursor: "pointer", padding: 4, flexShrink: 0 }}
                >
                  <Trash2 size={13} color="#5a6b60" />
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {/* Messages */}
      <div ref={messagesContainerRef} style={{
        flex: 1, overflowY: "auto", padding: "16px 18px",
        display: "flex", flexDirection: "column", gap: 14,
        scrollbarWidth: "thin", scrollbarColor: "rgba(255,255,255,0.1) transparent",
      }}>
        {messages.map((msg) => (
          <div key={msg.id} style={{
            alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
            maxWidth: "85%",
          }}>
            {msg.loading ? (
              <div style={{
                padding: "10px 14px", borderRadius: 12,
                background: "#111a16",
                color: "#94a39a",
                fontSize: 13,
              }}>
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: "50%",
                    background: "#00e5c3",
                    animation: "pulse 1.5s infinite",
                  }} />
                  Investigando dados públicos...
                </span>
              </div>
            ) : (
              <>
                <div
                  style={{
                    padding: "12px 16px", borderRadius: 12, fontSize: 13, lineHeight: 1.6,
                    background: msg.role === "user"
                      ? "linear-gradient(135deg, rgba(0,229,195,0.2), rgba(59,130,246,0.15))"
                      : "#111a16",
                    color: msg.role === "user" ? "#e8ede9" : "#e8ede9",
                    border: msg.role === "user"
                      ? "1px solid rgba(0,229,195,0.15)"
                      : "1px solid rgba(255,255,255,0.04)",
                  }}
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }}
                />

                {/* Entity cards */}
                {msg.entities && msg.entities.length > 0 && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
                    {msg.entities.map((entity) => (
                      <button
                        key={entity.id}
                        onClick={() => handleEntityClick(entity)}
                        style={{
                          display: "flex", alignItems: "center", gap: 8,
                          padding: "8px 12px", borderRadius: 8,
                          background: "#0c1210",
                          border: `1px solid ${ENTITY_TYPE_COLORS[entity.type] ?? "rgba(255,255,255,0.08)"}40`,
                          cursor: "pointer", textAlign: "left", width: "100%",
                          transition: "border-color 150ms ease-out",
                        }}
                      >
                        <span style={{
                          fontSize: 10, fontWeight: 700, textTransform: "uppercase",
                          color: ENTITY_TYPE_COLORS[entity.type] ?? "#5a6b60",
                          minWidth: 60, fontFamily: "var(--font-mono, monospace)",
                          letterSpacing: "0.05em",
                        }}>
                          {ENTITY_TYPE_LABELS[entity.type] ?? entity.type}
                        </span>
                        <span style={{
                          fontSize: 12, color: "#e8ede9",
                          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                        }}>
                          {entity.name}
                        </span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Suggestion chips */}
                {msg.suggestions && msg.suggestions.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                    {msg.suggestions.map((s) => (
                      <button
                        key={s}
                        onClick={() => handleSend(s)}
                        style={{
                          padding: "5px 12px", borderRadius: 12, fontSize: 11,
                          background: "rgba(0,229,195,0.06)",
                          border: "1px solid rgba(0,229,195,0.15)",
                          color: "#94a39a",
                          cursor: "pointer", whiteSpace: "nowrap",
                          transition: "all 150ms ease-out",
                          fontFamily: "var(--font-sans, sans-serif)",
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(0,229,195,0.12)"; e.currentTarget.style.color = "#e8ede9"; }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(0,229,195,0.06)"; e.currentTarget.style.color = "#94a39a"; }}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "14px 18px", borderTop: "1px solid rgba(255,255,255,0.06)",
        background: "#111a16",
      }}>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Cidade, deputado, CNPJ ou pergunta..."
          disabled={isLoading}
          style={{
            flex: 1, padding: "11px 16px", borderRadius: 10, fontSize: 14,
            background: "#0c1210",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#e8ede9",
            outline: "none",
            fontFamily: "var(--font-sans, sans-serif)",
            transition: "border-color 150ms ease-out",
          }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,229,195,0.3)"; }}
          onBlur={(e) => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)"; }}
        />
        <button
          onClick={() => handleSend()}
          disabled={isLoading || !input.trim()}
          style={{
            width: 42, height: 42, borderRadius: 10, flexShrink: 0,
            background: input.trim() ? "linear-gradient(135deg, #00e5c3, #3b82f6)" : "#162018",
            border: "none", cursor: input.trim() ? "pointer" : "default",
            display: "flex", alignItems: "center", justifyContent: "center",
            opacity: input.trim() ? 1 : 0.4,
            transition: "all 150ms ease-out",
          }}
        >
          <Send size={18} color="white" />
        </button>
      </div>
    </div>
  );
}
