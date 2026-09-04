# 📝 Schreibrichtlinien

## Titelfindung

### Format
```
[Verb] [Noun] - [Context]
```

### Beispiele
- ✅ Build API Gateway für Desk-Assistent
- ✅ Learn Obsidian Automation
- ✅ Design Database Schema

### ❌ Falsch
- "Todo", "Note", "Stuff"
- Zu generisch oder vage

## Frontmatter-Struktur

```yaml
---
type: note | project | area | resource | moc
status: active | inactive | archived | completed
priority: 1 | 2 | 3
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [area/subtopic]
related: [[Note1]], [[Note2]]
---
```

## Struktur der Note

```markdown
# Titel

## 🎯 Zweck
Was ist das Ziel dieser Note?

## 📋 Inhaltsverzeichnis
(Nur bei längeren Notes)

## 💡 Kernideen
Die wichtigsten Punkte.

## 🔗 Verbindungen
[[Related Note 1]]
[[Related Note 2]]

## 📚 Quellen
- Source 1
- Source 2

## ⏰ Status
Wann wurde das zuletzt aktualisiert?
```

## Link-Konventionen

- `[[Topic]]` = Konzept
- `[[Project: Name]]` = Projekt
- `[[Person: Name]]` = Kontakt
- `#tag/subtag` = Kategorisierung

## Dateibenennungskonvention

```
[Typ] Aussagekräftiger Titel
```

Beispiele:
- `Project: API Gateway Redesign`
- `Area: Engineering Practices`
- `Resource: React Hooks Guide`
- `Note: Observer Pattern Implementation`

## Review-Häufigkeit

- **Daily**: Inbox-Verarbeitung
- **Weekly**: MOC-Review (Sonntag)
- **Monthly**: Archiv-Review
- **Quarterly**: System-Optimierung
