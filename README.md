# TAK12 Courses — Affiliate Landing Page

A modern, responsive independent affiliate landing page about **TAK12**, Vietnam's K-12 online learning platform. The site helps families compare FREE and paid paths, explore relevant courses, and use an interactive course-finder quiz before visiting the provider.

This page was designed in [Claude Design](https://claude.ai/design) (`TAK12 Affiliate.dc.html`) and implemented here as standalone vanilla HTML/CSS/JS.

## 🌟 Features

### Page Sections
- **Sticky navigation** with anchor links and a FREE-vs-paid CTA
- **FREE-vs-paid guide** with links to the provider's current options
- **Hero** with headline, value proposition, and primary CTAs
- **Decision guide** — independent review and FREE-vs-paid routes
- **Featured courses** — 3 highlighted courses with tags, highlights, and pricing
- **Course-finder quiz** — 3 questions that recommend the best course for the student
- **Course CTA** — contextual route to the provider's current course options
- **About TAK12** — key selling points (AI personalization, time savings, progress tracking, affordability)
- **Independent review** — selection guidance for families
- **FAQ** — collapsible accordion (6 questions)
- **Final CTA** and footer

### Interactive Elements
- Interactive course-finder quiz with a progress bar and dynamic recommendation
- Collapsible FAQ accordion
- Contextual affiliate CTA tracking with destination-aligned intent
- Smooth-scrolling in-page navigation (native CSS `scroll-behavior`)
- Hover states and transitions throughout

### Marketing & Conversion
- Multiple CTAs linking to TAK12 with the affiliate `?ref=njg2odn` parameter and `rel="sponsored noopener"`
- PostHog event tracking on affiliate CTA clicks and quiz interactions

## 🚀 Live Demo

Visit the live site: [tak-12.com](https://tak-12.com/)

## 🛠️ Technologies Used

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: CSS Grid, Flexbox, custom properties, and responsive breakpoints
- **JavaScript**: Vanilla JS (no framework) for the quiz, FAQ accordion, and analytics events

### SEO & Analytics
- **SEO Optimized**:
  - Comprehensive meta tags and Open Graph implementation
  - JSON-LD structured data (`EducationalOrganization` with course catalog)
  - FAQ schema matching the visible FAQ for rich snippets
  - Twitter Card integration
- **Analytics**: PostHog integration for user behavior tracking and insights
- **Performance**: Preconnect hints and a CDN for assets

### Assets & CDN
- **Image CDN**: jsDelivr via GitHub for global image delivery
- **Fonts**: Google Fonts (Be Vietnam Pro) with preconnect
- **Social Media Preview**: Custom feature images for Open Graph and Twitter Cards

## 📱 Responsive Design

- **Breakpoints**: 900px and 640px with layout stacking (nav, hero, course grids, decision-guide cards, footer)
- **Touch-Friendly**: Large tap targets and mobile-optimized interactions
- **Cross-Browser**: Compatible with modern browsers including Safari, Chrome, and Firefox

## 🎯 SEO & Marketing Features

### Structured Data
- `EducationalOrganization` schema for TAK12 with an offer catalog
- Course offerings with pricing information
- `FAQPage` schema for rich search results

### Social Media Integration
- Open Graph tags for Facebook and LinkedIn sharing
- Twitter Card support with large image previews
- Custom feature images served via CDN

### Affiliate Marketing
- Consistent `?ref=njg2odn` parameter across all TAK12 links
- Trackable CTA buttons
- Analytics integration for conversion tracking

## 🔧 Development

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/tuantmdev/tak12.git
cd tak12
```

2. Serve locally (any static server works):
```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

### File Structure
```
tak12/
├── index.html          # Affiliate landing page
├── styles.css          # Green/gold theme + responsive styles
├── script.js           # Quiz, FAQ accordion, affiliate CTA tracking, PostHog events
├── images/             # Feature images for social media
│   ├── feature_desktop.jpg
│   └── feature_mobile.png
├── pricing/            # Course pricing reference screenshots
├── CNAME               # Custom domain (tak-12.com)
├── README.md           # This file
└── CLAUDE.md           # Development instructions
```

### Deployment

This site is deployed using **GitHub Pages** with automatic deployment:
- Any push to `main` triggers automatic deployment
- Live at https://tuantmdev.github.io/tak12/
- Custom domain (tak-12.com) via the `CNAME` file

### Sitemap freshness contract

Every canonical page in `sitemap.xml` has a matching entry in
`sitemap-content.json`. A canonical URL selects its page deterministically:
the site root maps to `index.html`, and `/<slug>/` maps to
`<slug>/index.html`; the contract never stores a source path. When a page's
indexable HTML changes, update that entry's SHA-256 fingerprint **and** set
both contract and sitemap `lastmod` to the reviewed content-change date. Do
not bump unchanged pages.

Verify the contract before opening a content PR:

```bash
python3 -m unittest tests.test_sitemap -v
```

The test resolves the branch point with `git merge-base origin/main HEAD` and
compares against `sitemap-content.json` at that exact commit. Fetch
`origin/main` before validating a change; missing or unreadable Git history
fails closed. The initial contract bootstrap is allowed only when the resolved
baseline commit exists but has no manifest. Once a baseline exists, a
fingerprint and its `lastmod` must change together.

## 📊 Analytics & Tracking

### PostHog Integration
- **User Behavior**: Page views and interactions
- **Privacy-Focused**: Identified users only
- **Custom Events**: `affiliate_cta_click`, `quiz_started`, and `quiz_completed`

## 🎨 Design System

### Color Palette (Green & Gold)
- **Primary**: TAK12 green (`#1B8A2C`) — trust and growth
- **Accent**: Gold (`#FFD700`) — highlights and CTAs
- **Backgrounds**: White and soft green (`#f8faf8`) for a clean, airy feel
- **Typography**: Be Vietnam Pro; deep ink (`#1a202c`) for readability

### Interactive Elements
- Hover transforms and color transitions
- CTA interaction feedback
- Accessible tap targets and keyboard-friendly buttons

## 🤝 Contributing

This is a marketing landing page for TAK12. For:
- **Course Content Issues**: Contact TAK12 directly
- **Technical Issues**: Open a GitHub issue
- **Feature Requests**: Submit via GitHub issues

## 📄 License

This independent affiliate landing page provides selection guidance; all educational content and services are provided by TAK12.

---

**Built with ❤️ using Claude Code** | **Designed in Claude Design** | **Deployed via GitHub Pages** | **Analytics by PostHog**
