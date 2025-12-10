PDF links: GoTo links (inter document) vs URI links

```
**PDF viewers often distinguish between two types of internal links:**

1. **URI Links (What you extracted):** Links that point to a URI (Uniform Resource Identifier), typically external URLs (`http://`, `mailto:`, `tel:`) or external file paths (`file://`, `mhtml:file://`). These are stored with an `/A` (Action) dictionary containing a `/URI` key. **Your current code captures these.**
    
2. **GoTo Links (What's missing):** Internal jump links that point to a **specific page and position** _within the same PDF document_. These use a `/Dest` (Destination) key instead of an `/A` (Action) key.
    

The "just to jump to a section, figure, etc" links you're missing are almost certainly **GoTo Links (Destinations)**.
```
