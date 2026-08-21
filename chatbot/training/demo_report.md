# Engineering Symbol Training Pipeline

## Training Assets

* **150** Engineering Symbols
* **300** Symbol Aliases
* **25** Equipment Families
* **100** Engineering Labels

## Generated Outputs

* **Symbol Knowledge Base**: `symbol_knowledge_base.json` (Combined Master Database)
* **Symbol Index**: `symbol_index.json` (Taxonomy Categories)
* **Alias Index**: `alias_index.json` (Component Alternates Lookup)
* **Family Index**: `family_index.json` (Hierarchy Associations)
* **Label Index**: `label_index.json` (Civil layout dimension lookups)
* **Training Report**: `training_report.json` (Compilation metrics)

## Capabilities

1. **Alias Normalization**: Translates layout names and shorthand terminology to standard standard keys (e.g. `ICT` -> `power_transformer`).
2. **Symbol Recognition**: Identifies custom engineering components from drawing block annotations.
3. **Equipment Family Classification**: Resolves hierarchy groupings for nested component counts (such as checking `transformer_family`).
4. **Engineering Label Recognition**: Matches dimensional clearing design rules (`tw` -> `Thickness of Side Wall`).
5. **Inventory Standardization**: Builds consolidated inventory reports from raw component lists.

## Description

"The system uses a custom engineering symbol knowledge base, alias mappings, equipment taxonomy, and engineering label datasets to normalize engineering terminology and support CAD inventory recognition."



Deployed LLaMA 3.1 (8B) and Qwen 3.5 (9B) locally using Hugging Face for offline inference
Built secure terminal command execution layer (file ops, network tasks)
Reduced VRAM usage via 4-bit quantization (~6.3GB on RTX 4060)
Implemented persistent memory with ChromaDB for context retention
Designed task-oriented AI agent ("Aldric") using prompt engineering