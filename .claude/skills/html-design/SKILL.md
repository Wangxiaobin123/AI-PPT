---
name: html-design
description: >
  Use this skill when creating HTML web pages, landing pages, or web components.
  Triggers on: "web page", "HTML", "React component", "landing page", "website",
  "static site", "responsive", "email template".
  Generates static HTML with inline CSS or standalone HTML files.
---

# HTML Design Skill

## Quick Start

This skill generates static HTML pages from Markdown or structured content. It
produces self-contained HTML files with inline CSS that render well in modern
browsers and can be used as landing pages, reports, or email-safe documents.

```bash
cd /home/user/AI-PPT && python -m src.skills.public.html_skill --help
```

## Output Types

### Static HTML Page
A single, self-contained `.html` file with embedded CSS. No external
dependencies. Opens directly in any browser.

### Responsive Page
A mobile-friendly HTML page using CSS media queries. Adapts layout for desktop,
tablet, and mobile viewports. Includes a viewport meta tag and flexible grid.

### Print-Ready HTML
HTML optimized for printing. Includes `@media print` styles that remove
navigation, adjust margins, and ensure clean page breaks.

### Email-Safe HTML
HTML with inline styles suitable for email clients. Uses table-based layout
for maximum compatibility across Outlook, Gmail, Apple Mail, and web clients.

## Input Format

Markdown is the preferred input. The HTML parser also accepts raw HTML input
for conversion or restyling.

### Markdown Example
```markdown
# Welcome to Our Product

## Features

- Fast and reliable
- Easy to use
- Beautiful design

## Pricing

| Plan    | Price   | Features       |
|---------|---------|----------------|
| Free    | $0/mo   | Basic          |
| Pro     | $19/mo  | All features   |
| Team    | $49/mo  | Collaboration  |
```

### HTML Passthrough
Provide raw HTML and the skill will parse, restructure, and restyle it:
```html
<h1>Existing Page</h1>
<p>This content will be restyled with the chosen template.</p>
```

## Design Guidelines

- Use semantic HTML5 elements (header, main, section, article, footer)
- Mobile-first responsive design with breakpoints at 768px and 1024px
- System font stack for fast loading: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- Color contrast ratio of at least 4.5:1 for body text (WCAG AA)
- Maximum content width of 800px for readability
- Minimum touch target size of 44x44px for interactive elements
- No external dependencies -- all CSS is inline or in a `<style>` block

## Style Overrides

Pass custom styles via JSON:
```json
{
  "color_scheme": {
    "primary": "1A73E8",
    "secondary": "34A853",
    "background": "FFFFFF",
    "text": "202124",
    "accent": "EA4335"
  },
  "fonts": {
    "title": "Georgia, serif",
    "body": "system-ui, sans-serif"
  },
  "options": {
    "output_type": "responsive",
    "include_print_styles": true,
    "max_width": "960px"
  }
}
```

## API Usage

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "format": "html",
    "content": "# Product Launch\n\n## Coming Soon\n\nOur revolutionary new product launches next month.\n\n- Faster performance\n- Better design\n- Lower price",
    "content_format": "markdown",
    "title": "Product Launch Page",
    "style": {
      "color_scheme": {"primary": "6200EA"},
      "options": {"output_type": "responsive"}
    }
  }'
```

## Template Catalog

The skill supports several built-in templates:

| Template     | Description                              | Best For                |
|-------------|------------------------------------------|-------------------------|
| `default`   | Clean, minimal design with sidebar nav   | Reports, documentation  |
| `landing`   | Hero section + features + CTA            | Product launch pages    |
| `report`    | Formal layout with table of contents     | Business reports        |
| `email`     | Table-based inline-styled layout         | Email campaigns         |
| `dashboard` | Card-based layout with data sections     | Data summaries          |

## QA

After generation, verify the output by checking:
- HTML validates (no unclosed tags, proper nesting)
- Page renders correctly at 320px, 768px, and 1280px viewport widths
- All text is readable (contrast ratio >= 4.5:1)
- Links are styled and functional
- Tables are responsive (horizontal scroll on small screens)
- Code blocks use monospace font with background
- Images have alt text
- Page loads without external resource errors
- Print preview shows clean layout with proper page breaks
