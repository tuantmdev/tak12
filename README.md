# TAK12 Courses — Affiliate Landing Page

A modern, responsive affiliate landing page promoting **TAK12**, Vietnam's comprehensive K-12 online learning platform. The page showcases featured courses, an interactive course-finder quiz, and the exclusive **DSMANHTUAN** discount code (10% off all TAK12 courses).

This page was designed in [Claude Design](https://claude.ai/design) (`TAK12 Affiliate.dc.html`) and implemented here as standalone vanilla HTML/CSS/JS.

## 🌟 Features

### Page Sections
- **Sticky navigation** with anchor links and a discount CTA
- **Coupon banner** with copy-to-clipboard code
- **Hero** with headline, value proposition, and primary CTAs
- **Stats bar** — social-proof metrics (students, satisfaction, courses, rating)
- **Featured courses** — 3 highlighted courses with tags, highlights, and pricing
- **Course-finder quiz** — 3 questions that recommend the best course for the student
- **Coupon CTA** — prominent discount code with copy button
- **About TAK12** — key selling points (AI personalization, time savings, progress tracking, affordability)
- **Testimonials** — parent reviews
- **FAQ** — collapsible accordion (6 questions)
- **Final CTA** and footer

### Interactive Elements
- Interactive course-finder quiz with a progress bar and dynamic recommendation
- Collapsible FAQ accordion
- Copy-to-clipboard promo code with toast confirmation (and `execCommand` fallback)
- Smooth-scrolling in-page navigation (native CSS `scroll-behavior`)
- Hover states and transitions throughout

### Marketing & Conversion
- Exclusive discount code **DSMANHTUAN** (10% off) surfaced in the banner, coupon sections, and footer
- Multiple CTAs linking to TAK12 with the affiliate `?ref=njg2odn` parameter
- PostHog event tracking on CTA clicks, quiz interactions, and promo-code copies

## 🚀 Live Demo

Visit the live site: [tak-12.com](https://tak-12.com/)

## 🛠️ Technologies Used

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: CSS Grid, Flexbox, custom properties, and responsive breakpoints
- **JavaScript**: Vanilla JS (no framework) for the quiz, FAQ, and copy/toast interactions

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

- **Breakpoints**: 900px and 640px with layout stacking (nav, hero, stats, course/testimonial grids, coupon card, footer)
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
├── script.js           # Quiz, FAQ accordion, copy-to-clipboard, PostHog events
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

## 📊 Analytics & Tracking

### PostHog Integration
- **User Behavior**: Page views and interactions
- **Privacy-Focused**: Identified users only
- **Custom Events**: `cta_click`, `quiz_started`, `quiz_completed`, and `promo_code_copied`

## 🎨 Design System

### Color Palette (Green & Gold)
- **Primary**: TAK12 green (`#1B8A2C`) — trust and growth
- **Accent**: Gold (`#FFD700`) — highlights and CTAs
- **Backgrounds**: White and soft green (`#f8faf8`) for a clean, airy feel
- **Typography**: Be Vietnam Pro; deep ink (`#1a202c`) for readability

### Interactive Elements
- Hover transforms and color transitions
- Toast feedback on promo-code copy
- Accessible tap targets and keyboard-friendly buttons

## 🤝 Contributing

This is a marketing landing page for TAK12. For:
- **Course Content Issues**: Contact TAK12 directly
- **Technical Issues**: Open a GitHub issue
- **Feature Requests**: Submit via GitHub issues

## 📄 License

This landing page is created for promotional purposes. All educational content and services are provided by TAK12.

---

**Built with ❤️ using Claude Code** | **Designed in Claude Design** | **Deployed via GitHub Pages** | **Analytics by PostHog**
