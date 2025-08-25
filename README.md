## Table of Contents

- [System Architecture](#system-architecture)
- [Research Results](#research-results)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Evaluation](#evaluation)


## System Architecture

PDFuzzer consists of four main components working in a systematic pipeline:

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  API Specification  │───▶│   Grammar           │───▶│   Relationship      │───▶│   Test Case         │
│     Extraction      │    │   Generation        │    │   Inference         │    │   Generator         │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘    └─────────────────────┘
         │                           │                           │                           │
         ▼                           ▼                           ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│ • Manual Parser     │    │ • Per-Parameter     │    │ • RAG-based         │    │ • SMT Constraint    │
│ • Diff Analysis     │    │   CFG Generation    │    │   Candidate ID      │    │   Solving           │
│ • LLM Inference     │    │ • Type-aware        │    │ • Symbolic          │    │ • PDF Integration   │
│ • JSON Specs        │    │   Rules             │    │   Relationships     │    │ • Corpus Generation │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## Research Results

### Vulnerability Discovery
- **31 zero-day vulnerabilities** discovered across three popular PDF readers
- **18 vulnerabilities** already confirmed or fixed by vendors
- **$2,450** in bug bounties received
- Vulnerability types include:
  - Null pointer dereferences
  - Buffer overflows  
  - Use-after-free bugs
  - Arbitrary code execution potential

### Performance Improvements
- **Up to 48% higher code coverage** compared to existing tools
- **22% coverage improvement** from fine-grained parameter analysis vs. coarse-grained API analysis
- **14% coverage improvement** from semantic constraint modeling vs. simple co-occurrence relationships
- **39% coverage improvement** from comprehensive specification extraction vs. type-only approaches

### Tested Targets
- **Adobe Acrobat Reader DC**
- **Foxit PDF Reader** 
- **PDF-XChange Editor**

## Requirements

- Python 3.8+
- Windows OS (for PDF reader testing)
- OpenAI API key or Anthropic API key (for AI-powered analysis)
- Target PDF readers:
  - Adobe Acrobat Reader DC
  - Foxit PDF Reader
  - PDF-XChange Editor

### Python Dependencies

Install all required dependencies:
```bash
pip install -r requirements.txt
```


Key dependencies include:
- **AI/LLM APIs**: `openai`, `anthropic` - For LLM-driven specification inference
- **System Automation**: `pywinauto`, `psutil`, `pywin32` - Windows application monitoring
- **Web Scraping**: `requests`, `beautifulsoup4`, `lxml` - Documentation parsing
- **Constraint Solving**: `z3-solver` - SMT constraint satisfaction for test generation

## Installation

1. **Clone the repository**:
```bash
git clone https://github.com/pushvoidname/artifact_418.git
cd artifact_418
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure API keys**:
```bash
# For OpenAI
export OPENAI_API_KEY="your-openai-api-key"

# For Anthropic
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

4. **Install target PDF readers** (ensure they are installed in default locations):
   - Adobe Acrobat Reader DC
   - Foxit PDF Reader
   - PDF-XChange Editor

## Usage

### Phase 1: API Specification Extraction

#### 1. Extract Documented API Specifications
```bash
cd pre_fuzz
python document_parser/web_scraper.py -u <documentation-url> -o <output-directory>
```

#### 2. Infer Undocumented API Specifications  
```bash
python undoc_semantic_recovery.py \
    -d <documented-apis-path> \
    -u <undocumented-apis-path> \
    -o <output-path> \
    -m gpt-4
```

#### 3. Generate Context-Free Grammars
```bash
python grammar_generator_param.py \
    -i <api-descriptions-path> \
    -o <grammar-output-path> \
    -m gpt-4
```

#### 4. Infer API Relationships
```bash
cd relation_infer
python RAG_relation_infer_4o.py \
    -i <api-specs-path> \
    -o <relationships-output>
python Symbolic_relation_infer.py \
    -i <candidate-relations> \
    -o <symbolic-constraints>
```

### Phase 2: Test Generation and Fuzzing

#### Basic Test Generation (Dry Run)
```bash
cd fuzzing
python run.py \
    -p <grammar-data-path> \
    -t adobe \
    --dry
```

#### Relationship-Aware Fuzzing
```bash
python run.py \
    -p <grammar-data-path> \
    -t foxit \
    --relation \
    --symbolic
```

#### Full Fuzzing Campaign
```bash
# Generate 30,000 test cases with 2,048 API calls each
python run.py \
    -p data/object_grammar_param_all_adobe \
    -t adobe \
    --relation \
    --symbolic
```

#### Parameters:
- `-p, --base_directory`: Path to grammar data directory  
- `-t, --target`: Target PDF reader (adobe, foxit, xchange)
- `--dry`: Generate PDFs without execution (dry run)
- `--relation`: Enable weak relationship-aware API generation
- `--symbolic`: Use symbolic constraint solving for strong relationships
- `--run`: Execute existing test files without generating new ones

### Individual Test Monitoring
```bash
python monitor.py -t adobe -i <test-file-name>
```

## Project Structure

```
artifact_418/
├── pre_fuzz/                    # Pre-fuzzing phase components
│   ├── agentlib/               # AI agent communication handlers
│   ├── data/                   # Raw API data (documented & undocumented)
│   ├── document_parser/        # Documentation parsing tools
│   ├── relation_infer/         # API relationship inference
│   ├── results/                # Processed API descriptions
│   ├── prompts/                # AI prompt templates
│   ├── utils/                  # Utility functions
│   ├── grammar_generator_param.py  # Parameter grammar generation
│   └── undoc_semantic_recovery.py # Undocumented API analysis
├── fuzzing/                    # Fuzzing phase components
│   ├── config/                 # Configuration files
│   │   ├── blocklist.txt      # Blocked APIs
│   │   ├── limitlist.txt      # Limited APIs
│   │   ├── all_relation.json  # API relationships
│   │   └── all_symbolic.json  # Symbolic constraints
│   ├── data/                   # Generated grammar data
│   ├── param_grammar/          # Grammar-based generators
│   │   └── generator/         # Code generation modules
│   ├── test/                   # Generated test cases
│   ├── monitor.py             # Application monitoring
│   ├── mPDF.py               # PDF creation utilities
│   └── run.py                # Main fuzzing orchestrator
└── README.md                 # This file
```

## Configuration

### Fuzzing Configuration

#### Block List (`fuzzing/config/blocklist.txt`)
APIs that should be completely avoided during testing:
```
api.dangerous_function
app.system_call
```

#### Limit List (`fuzzing/config/limitlist.txt`)
APIs with usage restrictions:
```
app.file_operations
net.external_requests
```

#### Relationship Configuration (`fuzzing/config/all_relation.json`)
Defines API dependencies and relationships for coherent test generation.

#### Symbolic Constraints (`fuzzing/config/all_symbolic.json`)
Constraint definitions for symbolic execution engine.

### AI Model Configuration

The framework supports multiple AI models for semantic analysis:
- OpenAI: `gpt-4o`, `o3-mini`
- Anthropic: `claude-3-7-sonnet-20250219`

Configure via command line parameter `-m <model-name>`.

## Evaluation

### Experimental Setup
- **Duration**: 24-hour coverage experiments and 2-week vulnerability discovery campaigns
- **Targets**: Adobe Acrobat Reader, Foxit PDF Reader, PDF-XChange Editor
- **Baselines**: TypeOracle, Favocado, Cooper, Fuzz4All, naive LLM approaches
- **Metrics**: Code coverage, vulnerability discovery rate, specification accuracy

### Key Findings

#### Coverage Improvements
| Target | PDFuzzer vs Best Baseline |
|--------|--------------------------|
| Adobe Acrobat | +48% coverage |
| Foxit PDF Reader | +35% coverage |
| PDF-XChange Editor | +42% coverage |

#### Vulnerability Discovery
- **PDFuzzer**: 31 zero-day vulnerabilities
- **Best Baseline** (TypeOracle): 6 vulnerabilities
- **Improvement**: 5x more vulnerabilities discovered

#### Component Ablation Study
| Component | Coverage Improvement |
|-----------|---------------------|
| Fine-grained parameter analysis | +22% vs coarse-grained |
| Semantic constraint modeling | +14% vs co-occurrence only |
| Comprehensive spec extraction | +39% vs type-only |

#### LLM Accuracy Assessment
- **API Specification Extraction**: 95% accuracy
- **Grammar Generation**: 98% accuracy  
- **Relationship Inference**: 93% accuracy

### Responsible Disclosure
All 31 discovered vulnerabilities were responsibly disclosed to vendors:
- **18 vulnerabilities** confirmed/fixed by vendors
- **$2,450** total bug bounties received
- Response times varied from immediate fixes to acknowledgment pending patches

## Output

### Test Results
- **Crash Cases**: PDFs that cause application crashes
- **Hang Cases**: PDFs that cause application freezes
- **Error Cases**: PDFs that trigger error conditions
- **Normal Cases**: PDFs that execute successfully

### Logs and Reports
- `runlog.txt`: Execution summary for all test cases
- `*.log`: Detailed logging for each phase
- Crash artifacts: Saved in `save/crash/` directory
- Performance data: CPU usage and timing information

### Directory Structure After Execution
```
test/                    # Generated test PDFs
save/
├── crash/              # Crash-inducing PDFs
├── hang/               # Hang-inducing PDFs
└── error/              # Error-inducing PDFs
results/                # Analysis results
logs/                   # Execution logs
```


## Troubleshooting

### Common Issues

#### PDF Reader Not Found
Ensure target PDF readers are installed in default locations:
- Adobe: `C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe`
- Foxit: `C:\Program Files (x86)\Foxit Software\Foxit PDF Reader\FoxitPDFReader.exe`
- Xchange: `C:\Program Files\Tracker Software\PDF Editor\PDFXEdit.exe`

#### API Key Issues
```bash
# Verify API key is set
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY
```

For additional support, please open an issue on the project repository.
