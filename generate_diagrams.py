import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

# Set global styles
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.family'] = 'sans-serif'

output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "report_assets"))
os.makedirs(output_dir, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# 1. HIGH-LEVEL ARCHITECTURE DIAGRAM
# ─────────────────────────────────────────────────────────────────────────────
def create_architecture_diagram():
    fig, ax = plt.subplots(figsize=(14, 10), dpi=300)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Background canvas
    fig.patch.set_facecolor('#F8FAFC')
    ax.set_facecolor('#F8FAFC')

    # Title Banner
    ax.text(7, 9.6, "THE VIVA-VERSE: HIGH-LEVEL SYSTEM ARCHITECTURE", 
            ha='center', va='center', fontsize=16, fontweight='bold', color='#0F172A')
    ax.text(7, 9.25, "Four-Tier Decoupled Architecture with Space-Bound Retrieval & BYOK LLM Orchestration", 
            ha='center', va='center', fontsize=10, style='italic', color='#475569')

    # Tier 1: Presentation Layer
    rect1 = patches.FancyBboxPatch((0.5, 7.3), 13, 1.6, boxstyle="round,pad=0.2,rounding_size=0.15",
                                  facecolor='#EFF6FF', edgecolor='#3B82F6', linewidth=1.5)
    ax.add_patch(rect1)
    ax.text(0.8, 8.6, "TIER 1: PRESENTATION & CLIENT LAYER (React 18 + Vite)", fontsize=11, fontweight='bold', color='#1E40AF')

    # Sub-boxes in Tier 1
    boxes_t1 = [
        ("Setup Studio\n(JD/CV Ingestion)", 1.0, 7.5, 2.6, 0.9, '#DBEAFE', '#2563EB'),
        ("Live Defense Arena\n(Multi-Turn Chat UI)", 4.0, 7.5, 2.6, 0.9, '#DBEAFE', '#2563EB'),
        ("Hybrid Search Hub\n(Experience Explorer)", 7.0, 7.5, 2.6, 0.9, '#DBEAFE', '#2563EB'),
        ("Analytics Dashboard\n(Knapsack Study Plan)", 10.0, 7.5, 2.8, 0.9, '#DBEAFE', '#2563EB')
    ]
    for label, x, y, w, h, bg, border in boxes_t1:
        b = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1,rounding_size=0.1", facecolor=bg, edgecolor=border, linewidth=1.2)
        ax.add_patch(b)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center', fontsize=8.5, fontweight='bold', color='#1E293B')

    # Arrow Down T1 -> T2
    ax.annotate("", xy=(7, 6.7), xytext=(7, 7.2),
                arrowprops=dict(arrowstyle="->", lw=2, color='#3B82F6', mutation_scale=15))
    ax.text(7.2, 6.95, "REST APIs (JSON / Streaming HTTP)", fontsize=8.5, fontweight='bold', color='#1D4ED8')

    # Tier 2: API Gateway & Application Layer
    rect2 = patches.FancyBboxPatch((0.5, 4.8), 13, 1.8, boxstyle="round,pad=0.2,rounding_size=0.15",
                                  facecolor='#F0FDF4', edgecolor='#10B981', linewidth=1.5)
    ax.add_patch(rect2)
    ax.text(0.8, 6.3, "TIER 2: API ROUTING & APPLICATION CONTROLLER (FastAPI + Async Python 3.10+)", fontsize=11, fontweight='bold', color='#065F46')

    boxes_t2 = [
        ("Auth & Session API\nJWT & State Store", 1.0, 5.0, 2.6, 1.0, '#DCFCE7', '#059669'),
        ("Search Router\nFTS5 + Vector Coordinator", 4.0, 5.0, 2.6, 1.0, '#DCFCE7', '#059669'),
        ("Viva Simulation Hub\nMulti-Agent State Machine", 7.0, 5.0, 2.6, 1.0, '#DCFCE7', '#059669'),
        ("Subscription Engine\nReal-time Alerting Hook", 10.0, 5.0, 2.8, 1.0, '#DCFCE7', '#059669')
    ]
    for label, x, y, w, h, bg, border in boxes_t2:
        b = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1,rounding_size=0.1", facecolor=bg, edgecolor=border, linewidth=1.2)
        ax.add_patch(b)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center', fontsize=8.5, fontweight='bold', color='#064E3B')

    # Arrow Down T2 -> T3
    ax.annotate("", xy=(4.5, 4.2), xytext=(4.5, 4.7),
                arrowprops=dict(arrowstyle="->", lw=2, color='#10B981', mutation_scale=15))
    ax.annotate("", xy=(9.5, 4.2), xytext=(9.5, 4.7),
                arrowprops=dict(arrowstyle="->", lw=2, color='#10B981', mutation_scale=15))

    # Tier 3: Algorithmic Engines & Space-Bound Storage Layer
    rect3 = patches.FancyBboxPatch((0.5, 2.0), 13, 2.1, boxstyle="round,pad=0.2,rounding_size=0.15",
                                  facecolor='#FAF5FF', edgecolor='#8B5CF6', linewidth=1.5)
    ax.add_patch(rect3)
    ax.text(0.8, 3.8, "TIER 3: ALGORITHMIC ENGINES & DATA STORAGE (Space-Bound < 500MB Footprint)", fontsize=11, fontweight='bold', color='#5B21B6')

    boxes_t3 = [
        ("Lexical Engine\nSQLite FTS5 (BM25)", 1.0, 2.2, 2.2, 1.3, '#EDE9FE', '#7C3AED'),
        ("Semantic Engine\nFAISS FlatIP Index", 3.4, 2.2, 2.2, 1.3, '#EDE9FE', '#7C3AED'),
        ("RRF Fusion\nReciprocal Rank Combiner", 5.8, 2.2, 2.2, 1.3, '#EDE9FE', '#7C3AED'),
        ("DP Chunking\nLeetCode 410 Split Array", 8.2, 2.2, 2.2, 1.3, '#EDE9FE', '#7C3AED'),
        ("K-Means & Knapsack\nTimeline & Remediation", 10.6, 2.2, 2.4, 1.3, '#EDE9FE', '#7C3AED')
    ]
    for label, x, y, w, h, bg, border in boxes_t3:
        b = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1,rounding_size=0.1", facecolor=bg, edgecolor=border, linewidth=1.2)
        ax.add_patch(b)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center', fontsize=8, fontweight='bold', color='#3B0764')

    # Arrow Down T3 -> T4
    ax.annotate("", xy=(7, 1.3), xytext=(7, 1.9),
                arrowprops=dict(arrowstyle="->", lw=2, color='#8B5CF6', mutation_scale=15))
    ax.text(7.2, 1.6, "Zero-Storage BYOK API Calls (Encrypted Transit)", fontsize=8.5, fontweight='bold', color='#6D28D9')

    # Tier 4: External BYOK LLM Inference Tier
    rect4 = patches.FancyBboxPatch((0.5, 0.2), 13, 1.0, boxstyle="round,pad=0.2,rounding_size=0.15",
                                  facecolor='#FFFBEB', edgecolor='#F59E0B', linewidth=1.5)
    ax.add_patch(rect4)
    ax.text(0.8, 0.9, "TIER 4: ZERO-COST BYOK MODEL INFERENCE PROVIDERS", fontsize=10.5, fontweight='bold', color='#92400E')

    boxes_t4 = [
        ("Google GenAI / Gemini 3.7 Flash", 1.0, 0.35, 3.5, 0.48, '#FEF3C7', '#D97706'),
        ("OpenRouter / Gemma-4-31B-IT", 4.8, 0.35, 3.5, 0.48, '#FEF3C7', '#D97706'),
        ("NVIDIA NIM / Hugging Face Router", 8.6, 0.35, 4.4, 0.48, '#FEF3C7', '#D97706')
    ]
    for label, x, y, w, h, bg, border in boxes_t4:
        b = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.08", facecolor=bg, edgecolor=border, linewidth=1.1)
        ax.add_patch(b)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center', fontsize=8, fontweight='bold', color='#78350F')

    plt.tight_layout()
    path = os.path.join(output_dir, "architecture_diagram.png")
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated: {path}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA FLOW DIAGRAM (DFD LEVEL 1 & SEQUENCE PIPELINE)
# ─────────────────────────────────────────────────────────────────────────────
def create_data_flow_diagram():
    fig, ax = plt.subplots(figsize=(14, 9), dpi=300)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis('off')

    fig.patch.set_facecolor('#F8FAFC')
    ax.set_facecolor('#F8FAFC')

    ax.text(7, 8.6, "THE VIVA-VERSE: END-TO-END DATA FLOW DIAGRAM (DFD LEVEL 1)", 
            ha='center', va='center', fontsize=15, fontweight='bold', color='#0F172A')
    ax.text(7, 8.25, "Complete Candidate Ingestion, Semantic Clustering, Dynamic Questioning & Remediation Pipeline", 
            ha='center', va='center', fontsize=9.5, style='italic', color='#475569')

    # Step 1: Input Entity
    p1 = patches.FancyBboxPatch((0.4, 4.5), 2.2, 2.5, boxstyle="round,pad=0.15,rounding_size=0.15",
                               facecolor='#E2E8F0', edgecolor='#475569', linewidth=1.5)
    ax.add_patch(p1)
    ax.text(1.5, 6.6, "CANDIDATE / USER", ha='center', fontsize=9.5, fontweight='bold', color='#1E293B')
    ax.text(1.5, 5.7, "• Resume (PDF)\n• Target JD (Text)\n• BYOK API Key\n• Interview Mode", 
            ha='center', va='center', fontsize=8, color='#334155')

    # Arrow 1 -> Step 2
    ax.annotate("", xy=(3.0, 5.75), xytext=(2.7, 5.75),
                arrowprops=dict(arrowstyle="->", lw=1.8, color='#2563EB', mutation_scale=12))
    ax.text(2.85, 6.0, "Upload", ha='center', fontsize=7.5, fontweight='bold', color='#2563EB')

    # Step 2: Document Ingestion & DP Chunking
    p2 = patches.FancyBboxPatch((3.1, 4.5), 2.5, 2.5, boxstyle="round,pad=0.15,rounding_size=0.15",
                               facecolor='#DBEAFE', edgecolor='#2563EB', linewidth=1.5)
    ax.add_patch(p2)
    ax.text(4.35, 6.6, "1. INGESTION & PARSE", ha='center', fontsize=9, fontweight='bold', color='#1E40AF')
    ax.text(4.35, 5.5, "• PyMuPDF Extractor\n• Paragraph Slicing\n• DP Chunking (LC 410)\n• SBERT Vectorization", 
            ha='center', va='center', fontsize=7.8, color='#1E3A8A')

    # Arrow 2 -> Step 3
    ax.annotate("", xy=(6.0, 5.75), xytext=(5.7, 5.75),
                arrowprops=dict(arrowstyle="->", lw=1.8, color='#2563EB', mutation_scale=12))
    ax.text(5.85, 6.0, "Vectors", ha='center', fontsize=7.5, fontweight='bold', color='#2563EB')

    # Step 3: K-Means Clustering & Topic Alignment
    p3 = patches.FancyBboxPatch((6.1, 4.5), 2.5, 2.5, boxstyle="round,pad=0.15,rounding_size=0.15",
                               facecolor='#FEF3C7', edgecolor='#D97706', linewidth=1.5)
    ax.add_patch(p3)
    ax.text(7.35, 6.6, "2. CLUSTERING ENGINE", ha='center', fontsize=9, fontweight='bold', color='#92400E')
    ax.text(7.35, 5.5, "• K-Means (k=5..7)\n• Anti-Hyperfixation\n• Richness Scoring\n• Batch Gemini Prompt", 
            ha='center', va='center', fontsize=7.8, color='#78350F')

    # Arrow 3 -> Step 4
    ax.annotate("", xy=(9.0, 5.75), xytext=(8.7, 5.75),
                arrowprops=dict(arrowstyle="->", lw=1.8, color='#D97706', mutation_scale=12))
    ax.text(8.85, 6.0, "Contexts", ha='center', fontsize=7.5, fontweight='bold', color='#D97706')

    # Step 4: Autonomous Simulation Hub (LLM Engine)
    p4 = patches.FancyBboxPatch((9.1, 4.5), 2.5, 2.5, boxstyle="round,pad=0.15,rounding_size=0.15",
                               facecolor='#DCFCE7', edgecolor='#059669', linewidth=1.5)
    ax.add_patch(p4)
    ax.text(10.35, 6.6, "3. VIVA DEFENSE ARENA", ha='center', fontsize=9, fontweight='bold', color='#065F46')
    ax.text(10.35, 5.5, "• Multi-Turn Agent\n• Real-Time Scoring\n• RAG Rubric Validation\n• Brutal Honest Critique", 
            ha='center', va='center', fontsize=7.8, color='#064E3B')

    # Arrow 4 -> Step 5
    ax.annotate("", xy=(12.0, 5.75), xytext=(11.7, 5.75),
                arrowprops=dict(arrowstyle="->", lw=1.8, color='#059669', mutation_scale=12))
    ax.text(11.85, 6.0, "Scores", ha='center', fontsize=7.5, fontweight='bold', color='#059669')

    # Step 5: Knapsack Remediation Engine
    p5 = patches.FancyBboxPatch((12.1, 4.5), 1.6, 2.5, boxstyle="round,pad=0.15,rounding_size=0.15",
                               facecolor='#EDE9FE', edgecolor='#7C3AED', linewidth=1.5)
    ax.add_patch(p5)
    ax.text(12.9, 6.6, "4. 0/1 KNAPSACK", ha='center', fontsize=8.5, fontweight='bold', color='#5B21B6')
    ax.text(12.9, 5.5, "• SW-TF JD Weights\n• Hour Budgeting\n• Optimal Study\n• Daily Roadmap", 
            ha='center', va='center', fontsize=7.5, color='#3B0764')

    # Lower Data Stores & Retrieval Path
    # SQLite Database Box
    d1 = patches.FancyBboxPatch((1.5, 1.0), 4.5, 2.2, boxstyle="round,pad=0.15,rounding_size=0.15",
                               facecolor='#F1F5F9', edgecolor='#64748B', linewidth=1.3)
    ax.add_patch(d1)
    ax.text(3.75, 2.8, "LOCAL SQLITE FTS5 DATABASE (Lexical Index)", ha='center', fontsize=9, fontweight='bold', color='#334155')
    ax.text(3.75, 1.9, "• BM25 Indexing on Experiences\n• Full-Text Search on Company, Role, Topics\n• Serialized JSON Metadata Storage", 
            ha='center', va='center', fontsize=7.8, color='#475569')

    # FAISS In-Memory Vector Store Box
    d2 = patches.FancyBboxPatch((7.5, 1.0), 5.0, 2.2, boxstyle="round,pad=0.15,rounding_size=0.15",
                               facecolor='#F1F5F9', edgecolor='#64748B', linewidth=1.3)
    ax.add_patch(d2)
    ax.text(10.0, 2.8, "FAISS IN-MEMORY VECTOR STORE (Semantic Index)", ha='center', fontsize=9, fontweight='bold', color='#334155')
    ax.text(10.0, 1.9, "• 384-d / 768-d Normalized Embeddings\n• Inner Product (Cosine Similarity) Search\n• Sub-5ms Query Response & Disk Binary Cache", 
            ha='center', va='center', fontsize=7.8, color='#475569')

    # Connecting Feedback Lines
    ax.annotate("", xy=(3.75, 3.3), xytext=(4.35, 4.4),
                arrowprops=dict(arrowstyle="<->", lw=1.5, color='#64748B', linestyle='--'))
    ax.annotate("", xy=(10.0, 3.3), xytext=(10.35, 4.4),
                arrowprops=dict(arrowstyle="<->", lw=1.5, color='#64748B', linestyle='--'))
    ax.annotate("", xy=(1.5, 4.4), xytext=(12.9, 4.4),
                arrowprops=dict(arrowstyle="->", lw=1.5, color='#7C3AED', connectionstyle="arc3,rad=0.35"))
    ax.text(7.0, 3.6, "Optimized Actionable Report & Multi-Day Roadmap Returned to Candidate", 
            ha='center', fontsize=8, fontweight='bold', color='#6D28D9')

    plt.tight_layout()
    path = os.path.join(output_dir, "data_flow_diagram.png")
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated: {path}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. HYBRID SEARCH RRF DUAL-PATH ARCHITECTURE DIAGRAM
# ─────────────────────────────────────────────────────────────────────────────
def create_hybrid_search_diagram():
    fig, ax = plt.subplots(figsize=(13, 7), dpi=300)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7)
    ax.axis('off')

    fig.patch.set_facecolor('#F8FAFC')
    ax.set_facecolor('#F8FAFC')

    ax.text(6.5, 6.5, "HYBRID SEARCH ENGINE: RECIPROCAL RANK FUSION (RRF) ARCHITECTURE", 
            ha='center', va='center', fontsize=14, fontweight='bold', color='#0F172A')

    # Query Input
    q = patches.FancyBboxPatch((0.5, 2.7), 2.2, 1.6, boxstyle="round,pad=0.1,rounding_size=0.1",
                              facecolor='#E0F2FE', edgecolor='#0284C7', linewidth=1.5)
    ax.add_patch(q)
    ax.text(1.6, 3.6, "USER QUERY", ha='center', fontsize=10, fontweight='bold', color='#0369A1')
    ax.text(1.6, 3.1, "e.g., 'K8s cluster'\n'raft consensus'", ha='center', fontsize=8, color='#0C4A6E')

    # Split Arrows
    ax.annotate("", xy=(3.5, 4.8), xytext=(2.8, 3.8),
                arrowprops=dict(arrowstyle="->", lw=2, color='#2563EB', mutation_scale=12))
    ax.annotate("", xy=(3.5, 2.2), xytext=(2.8, 3.2),
                arrowprops=dict(arrowstyle="->", lw=2, color='#7C3AED', mutation_scale=12))

    # Path 1: BM25 Lexical Search
    p1 = patches.FancyBboxPatch((3.6, 4.0), 3.4, 1.8, boxstyle="round,pad=0.1,rounding_size=0.1",
                               facecolor='#DBEAFE', edgecolor='#2563EB', linewidth=1.5)
    ax.add_patch(p1)
    ax.text(5.3, 5.4, "LEXICAL PATH: SQLite FTS5", ha='center', fontsize=9.5, fontweight='bold', color='#1E40AF')
    ax.text(5.3, 4.6, "• Stopword Filtering\n• Exact Match & Prefix Search\n• BM25 Okapi Scoring\n• Top-100 Ranked IDs", 
            ha='center', fontsize=7.8, color='#1E3A8A')

    # Path 2: FAISS Semantic Vector Search
    p2 = patches.FancyBboxPatch((3.6, 1.2), 3.4, 1.8, boxstyle="round,pad=0.1,rounding_size=0.1",
                               facecolor='#EDE9FE', edgecolor='#7C3AED', linewidth=1.5)
    ax.add_patch(p2)
    ax.text(5.3, 2.6, "SEMANTIC PATH: FAISS Dense Vector", ha='center', fontsize=9.5, fontweight='bold', color='#5B21B6')
    ax.text(5.3, 1.8, "• SBERT Embedding (all-MiniLM-L6-v2)\n• L2 Normalization\n• Inner Product Cosine Sim\n• Top-100 Ranked IDs", 
            ha='center', fontsize=7.8, color='#3B0764')

    # Fusion Arrows
    ax.annotate("", xy=(7.8, 3.8), xytext=(7.1, 4.8),
                arrowprops=dict(arrowstyle="->", lw=2, color='#2563EB', mutation_scale=12))
    ax.annotate("", xy=(7.8, 3.2), xytext=(7.1, 2.2),
                arrowprops=dict(arrowstyle="->", lw=2, color='#7C3AED', mutation_scale=12))

    # RRF Fusion Engine
    f = patches.FancyBboxPatch((7.9, 2.2), 2.8, 2.6, boxstyle="round,pad=0.1,rounding_size=0.15",
                              facecolor='#FEF3C7', edgecolor='#D97706', linewidth=1.5)
    ax.add_patch(f)
    ax.text(9.3, 4.4, "RRF FUSION ENGINE", ha='center', fontsize=10, fontweight='bold', color='#92400E')
    ax.text(9.3, 3.6, r"$RRF(d) = \sum_{r \in R} \frac{w_r}{k + rank_r(d)}$", ha='center', fontsize=9, color='#78350F')
    ax.text(9.3, 2.7, "• Constant k = 60\n• Weight Vector = 3.0\n• Weight BM25 = 1.0\n• Scale Invariant Merge", 
            ha='center', fontsize=7.5, color='#78350F')

    # Arrow to Output
    ax.annotate("", xy=(11.2, 3.5), xytext=(10.8, 3.5),
                arrowprops=dict(arrowstyle="->", lw=2, color='#059669', mutation_scale=12))

    # Output Box
    o = patches.FancyBboxPatch((11.3, 2.4), 1.5, 2.2, boxstyle="round,pad=0.1,rounding_size=0.1",
                              facecolor='#DCFCE7', edgecolor='#059669', linewidth=1.5)
    ax.add_patch(o)
    ax.text(12.05, 4.2, "UNIFIED\nRESULTS", ha='center', fontsize=9.5, fontweight='bold', color='#065F46')
    ax.text(12.05, 3.1, "• 0 Semantic\nBlindness\n• +45% MRR\n• Paginated\nJSON", 
            ha='center', fontsize=7.5, color='#064E3B')

    plt.tight_layout()
    path = os.path.join(output_dir, "hybrid_search_flow.png")
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated: {path}")

create_architecture_diagram()
create_data_flow_diagram()
create_hybrid_search_diagram()
