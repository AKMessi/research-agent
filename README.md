# 🔬 Ultimate Research Agent

> **One agent. Any topic. Structured results. Zero cost.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-green)](https://ollama.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-grade research agent that searches the web, analyzes sources, and delivers structured reports on **any topic** - all running locally with zero API costs for inference.

![Demo](demo.gif)

## ✨ What Makes This Special

| Feature | Traditional LLMs | This Agent |
|---------|------------------|------------|
| **Data Freshness** | Training cutoff (months old) | Live web search |
| **Source Citations** | Often hallucinated | Real, clickable URLs |
| **Output Format** | Wall of text | Structured (CSV/Report/Table) |
| **Cost** | $10-20/month | **$0** (local LLM) |
| **Privacy** | Data sent to cloud | **100% local** |
| **Structured Output** | Manual prompting | Auto-detected format |

## 🎥 Demo

**Query:** `"how to learn machine learning"`

**Result:** Full roadmap with prerequisites, free resources, timeline, common mistakes, and 14 verified sources - in 90 seconds.

[Watch Demo Video](your-video-link-here)

## 🚀 Features

- **🔍 Multi-Source Research** - Google Search + Reddit + Deep content extraction
- **🧠 Smart Query Detection** - Auto-detects if you want products, travel guide, tutorial, etc.
- **📊 Format Adaptation** - Products → CSV table, Places → Travel guide, How-To → Step-by-step
- **📄 Structured Output** - CSV, Excel, Markdown reports, PDF
- **🔗 Source Citations** - Every claim backed by real, clickable URLs
- **🤖 Local LLM** - Runs on Ollama (llama3.2/mistral) - no cloud dependency
- **💰 Zero Cost** - No OpenAI/Anthropic API fees

## 📋 Supported Research Types

| Query Type | Example | Output Format |
|------------|---------|---------------|
| **Products** | "best wireless earbuds under $100" | CSV comparison table |
| **Travel** | "places to visit in Japan" | Markdown travel guide |
| **How-To** | "how to start a podcast" | Step-by-step tutorial |
| **People** | "top AI researchers 2024" | Profile cards |
| **Companies** | "AI startups in healthcare" | Company profiles |
| **Comparison** | "MacBook Air vs Pro" | Side-by-side table |
| **General** | "climate change effects" | Research report |

## 🛠️ Installation

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) installed locally
- API keys: Serper (Google Search)

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/ultimate-research-agent.git
cd ultimate-research-agent
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Ollama

```bash
# Pull a fast model (recommended: llama3.2)
ollama pull llama3.2

# Or use mistral
ollama pull mistral
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
SERPER_API_KEY=your_serper_key_here
FIRECRAWL_API_KEY=your_firecrawl_key_here  # Optional but recommended
```

**Get free API keys:**
- [Serper.dev](https://serper.dev) - 2,500 free searches/month
- [Firecrawl](https://firecrawl.dev) - 500 free credits

## 🎯 Usage

### Basic Research

```bash
python main.py research "best wireless earbuds for workout"
```

### With Context

```bash
python main.py research "best laptops" --context "for video editing, under $1500"
```

### Without Firecrawl (Faster, lighter)

```bash
python main.py research "current gold price" --no-firecrawl
```

### Output Examples

**Products:**
```csv
name,price,best_for,features
Sony WF-1000XM5,$280,Commute/Sport,Noise cancelling 30hr battery
AirPods Pro 2,$249,Apple ecosystem,Spatial audio MagSafe
```

**Travel Guide:**
```markdown
# Research: Places to visit in Japan

## Best Time to Visit
Spring (March-May) for cherry blossoms

## Top Attractions
1. Fushimi Inari Shrine
2. Kinkakuji Temple
...

## Budget
$100-200/day for mid-range travel
```

## 🏗️ Architecture

```
Query → Domain Detection → Multi-Source Search → Content Extraction → 
AI Synthesis → Format Selection → Structured Output
```

**Components:**
- `QueryAnalyzer` - Detects research domain (products/places/how-to)
- `UnifiedSynthesisEngine` - Formats output based on domain
- `SerperSearchTool` - Google Search API
- `FirecrawlClient` - Deep web scraping (top 5 sources)
- `Ollama Integration` - Local LLM for synthesis

## 📁 Project Structure

```
.
├── research_agent/
│   ├── core/
│   │   ├── ultimate_agent.py      # Main orchestrator
│   │   ├── query_analyzer.py      # Domain detection
│   │   ├── unified_synthesis.py   # AI synthesis engine
│   │   └── synthesis_prompts.py   # Format-specific prompts
│   ├── tools/
│   │   ├── serper_search.py       # Google Search
│   │   ├── firecrawl_client.py    # Premium scraping
│   │   └── reddit_scraper.py      # Reddit discussions
│   ├── formatters/                 # Output formatters
│   └── outputs/                    # Generated reports (gitignored)
├── main.py                         # CLI entry point
├── requirements.txt
├── .env.example
└── README.md
```

## ⚙️ Configuration

Edit `.env` file:

```env
# Required
SERPER_API_KEY=your_key_here

# Optional (enhances results)
FIRECRAWL_API_KEY=your_key_here

# Ollama (default: llama3.2)
OLLAMA_MODEL=llama3.2

# Output directory
OUTPUT_DIR=./research_agent/outputs
```

## 🧪 Testing Different Query Types

```bash
# Products - Comparison table
python main.py research "best mechanical keyboards under $100"

# Travel - Guide format
python main.py research "best places to visit in Thailand"

# How-To - Step-by-step
python main.py research "how to invest in index funds"

# People - Profiles
python main.py research "top machine learning experts"

# Companies - Analysis
python main.py research "AI startups in healthcare 2024"

# Comparison
python main.py research "MacBook Air M3 vs MacBook Pro M3"
```

## 🔒 Privacy & Security

- ✅ **100% Local LLM** - Your queries never leave your machine
- ✅ **No Data Logging** - No cloud AI service tracking your research
- ✅ **Source Transparency** - Every result cites verifiable URLs
- ✅ **Open Source** - Full code visibility, no black boxes

## 💡 Why I Built This

I research 10+ things daily:
- Products to buy
- Places to visit
- Tools to try
- Topics to learn

Tab hell was ruining my productivity. ChatGPT gave outdated answers. Perplexity was good but expensive. So I built the perfect research agent for myself.

**The sweet spot:** Fast enough (90s), accurate enough (live data), cheap enough ($0).

## 🤝 Contributing

Contributions welcome! Areas to improve:
- [ ] Add more output formats (PDF, HTML)
- [ ] Support for academic paper search
- [ ] Image extraction from sources
- [ ] Multi-language support
- [ ] Browser extension

## 📜 License

MIT License - feel free to use, modify, and distribute.

## 🙏 Acknowledgments

- [Ollama](https://ollama.com) for local LLM inference
- [Firecrawl](https://firecrawl.dev) for web scraping
- [Serper](https://serper.dev) for Google Search API
- Built with [Kimi Code](https://kimi.moonshot.cn)

---

**Star ⭐ this repo if you found it useful!**

**Questions?** Drop an issue or reach out on X: [@YOUR_HANDLE]
# research-agent
