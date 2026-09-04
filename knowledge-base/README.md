# 🧠 Knowledge Management System

Professionelle digitale Wissensverwaltung basierend auf der **PARA-Methode** (Tiago Forte).

## 📊 System-Architektur

### PARA-Struktur
- **10-PROJECTS**: Zeitgebundene Ziele mit Deadlines
- **20-AREAS**: Langfristige Verantwortungsbereiche
- **30-RESOURCES**: Referenzmaterial & Sammlungen
- **40-ARCHIVE**: Abgeschlossene Projekte

### Metadaten
- **00-INBOX**: Triage-Punkt für neue Inhalte
- **_templates**: Note-Templates für Konsistenz
- **_metadata**: Konfiguration & Standards
- **_snippets**: CSS & UI-Erweiterungen
- **_scripts**: Automation & Workflows

## 🚀 Setup

1. Öffne `knowledge-base/` in Obsidian
2. Vault wird automatisch initialisiert
3. Tägliche Notizen in `00-INBOX` erstellen
4. Automatische Verarbeitung: Inbox → Areas/Projects

## 📐 Metadaten-Standard

```yaml
---
type: note | project | area | resource
status: active | inactive | archived
priority: high | medium | low
created: 2026-09-04
updated: 2026-09-04
tags: [topic/subtopic]
links: []
---
```

## 🔄 Workflow

```
CAPTURE (Inbox)
  ↓
CLARIFY (Type, Relevanz)
  ↓
ORGANIZE (Projects/Areas)
  ↓
REFLECT (Weekly Review)
  ↓
EXECUTE (Action)
```

## 📚 MOCs (Maps of Content)

- Index: Zentrale Navigation
- Projects: Aktuelle Projekte
- Areas: Verantwortungsbereiche
- Learning: Wissensentwicklung

## 🎯 Best Practices

✓ Aussagekräftige Titel (Format: Action/Ergebnis)  
✓ Frontmatter für alle Notes  
✓ Bidirektionale Links nutzen  
✓ Wöchentliche Reviews  
✓ Tagging-System konsequent  

## 📖 Dokumentation

- `_metadata/guidelines.md` - Schreibrichtlinien
- `_metadata/tagging-system.md` - Tag-Hierarchie
- `_metadata/workflows.md` - Automatisierungen
