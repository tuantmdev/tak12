// TAK12 Landing Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Smooth scrolling for navigation links
    const navLinks = document.querySelectorAll('a[href^="#"]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                const offsetTop = targetElement.offsetTop - 80;
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Promo code copy functionality
    const promoCodes = document.querySelectorAll('.promo-code, .promo-code-large');
    promoCodes.forEach(code => {
        code.addEventListener('click', function() {
            // Copy to clipboard
            navigator.clipboard.writeText('DSMANHTUAN').then(() => {
                // Show feedback
                const originalText = this.textContent;
                this.textContent = 'Copied!';
                this.style.background = '#6B8E4D';
                
                setTimeout(() => {
                    this.textContent = originalText;
                    this.style.background = '';
                }, 1500);
            }).catch(() => {
                // Fallback for older browsers
                alert('Promo code: DSMANHTUAN');
            });
        });
        
        // Add cursor pointer
        code.style.cursor = 'pointer';
        code.title = 'Click to copy promo code';
    });

    // Animate progress bars when they come into view
    const progressBars = document.querySelectorAll('.progress-fill');
    const animateProgressBars = () => {
        progressBars.forEach(bar => {
            const rect = bar.getBoundingClientRect();
            if (rect.top < window.innerHeight && rect.bottom > 0) {
                const width = bar.style.width;
                bar.style.width = '0%';
                setTimeout(() => {
                    bar.style.width = width;
                }, 500);
            }
        });
    };

    // Intersection Observer for animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observe elements for fade-in animation
    const animatedElements = document.querySelectorAll('.benefit-card, .course-card, .testimonial-card, .video-wrapper, .video-description, .faq-item');
    animatedElements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        
        // Add staggered delay for FAQ items
        if (el.classList.contains('faq-item')) {
            const faqIndex = Array.from(document.querySelectorAll('.faq-item')).indexOf(el);
            el.style.transitionDelay = `${faqIndex * 0.1}s`;
        }
        
        observer.observe(el);
    });

    // Trigger progress bar animation on scroll
    window.addEventListener('scroll', animateProgressBars);
    animateProgressBars(); // Initial check

    // Add click tracking for analytics
    const trackClick = (element, action) => {
        console.log(`Tracking: ${action} clicked`);
        
        // Send event to PostHog
        if (window.posthog) {
            const properties = {
                button_text: element.textContent.trim(),
                button_class: element.className,
                page_url: window.location.href,
                action: action
            };
            
            // Add course-specific data if available
            const href = element.getAttribute('href');
            if (href && href.includes('tak12.com/license/ex/')) {
                const courseId = href.match(/ex\/(\d+\/\d+)/)?.[1];
                if (courseId) {
                    properties.course_id = courseId;
                }
            }
            
            posthog.capture('cta_clicked', properties);
        }
    };

    // Track CTA button clicks
    const ctaButtons = document.querySelectorAll('.primary-button, .cta-button, .course-cta-button, .select-course');
    ctaButtons.forEach(button => {
        button.addEventListener('click', () => {
            trackClick(button, 'CTA Button');
        });
    });

    // Add promo code highlight effect on scroll
    let promoHighlighted = false;
    const promoBox = document.querySelector('.promo-box');
    
    window.addEventListener('scroll', () => {
        if (!promoHighlighted && window.scrollY > 200) {
            promoBox.style.animation = 'pulse 1s ease-in-out';
            promoHighlighted = true;
            
            setTimeout(() => {
                promoBox.style.animation = '';
            }, 1000);
        }
    });

    // Mobile menu toggle (for future implementation)
    const createMobileMenu = () => {
        if (window.innerWidth <= 768) {
            const nav = document.querySelector('.nav-links');
            if (nav && !document.querySelector('.mobile-menu-toggle')) {
                const toggleButton = document.createElement('button');
                toggleButton.className = 'mobile-menu-toggle';
                toggleButton.innerHTML = '☰';
                toggleButton.style.cssText = `
                    background: none;
                    border: none;
                    font-size: 1.5rem;
                    color: var(--sage-primary);
                    cursor: pointer;
                `;
                
                document.querySelector('.nav-container').appendChild(toggleButton);
                
                toggleButton.addEventListener('click', () => {
                    nav.style.display = nav.style.display === 'flex' ? 'none' : 'flex';
                });
            }
        }
    };

    // Initialize mobile menu
    createMobileMenu();
    window.addEventListener('resize', createMobileMenu);

    // Add discount calculator
    const addDiscountCalculator = () => {
        const originalPrices = document.querySelectorAll('.original-price');
        const discountedPrices = document.querySelectorAll('.discounted-price');
        
        // Apply 10% discount calculation
        originalPrices.forEach((original, index) => {
            const priceText = original.textContent.replace(/[^\d]/g, '');
            const originalPrice = parseInt(priceText);
            const discountedPrice = Math.round(originalPrice * 0.9);
            
            if (discountedPrices[index]) {
                const currency = original.textContent.includes('VND') ? ' VND' : '';
                discountedPrices[index].textContent = discountedPrice.toLocaleString() + currency;
            }
        });
    };

    // Initialize discount calculator
    addDiscountCalculator();
});

// Course Catalog Modal Functions
function toggleCourseCatalog() {
    const modal = document.getElementById('courseCatalogModal');
    if (modal.classList.contains('active')) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    } else {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function showCategory(categoryId) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedContent = document.getElementById(categoryId);
    if (selectedContent) {
        selectedContent.classList.add('active');
    }
    
    // Add active class to clicked button
    const clickedButton = event.target;
    if (clickedButton) {
        clickedButton.classList.add('active');
    }
}

// Close modal when clicking outside
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('courseCatalogModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                toggleCourseCatalog();
            }
        });
    }
    
    // Close modal with Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const modal = document.getElementById('courseCatalogModal');
            if (modal && modal.classList.contains('active')) {
                toggleCourseCatalog();
            }
        }
    });
});

// Add CSS animation keyframes dynamically
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    .promo-code:hover,
    .promo-code-large:hover {
        transform: scale(1.05);
        transition: transform 0.2s ease;
    }
    
    .mobile-menu-toggle {
        display: none;
    }
    
    @media (max-width: 768px) {
        .mobile-menu-toggle {
            display: block !important;
        }
        
        .nav-links {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            flex-direction: column;
            padding: 1rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: none;
        }
        
        .nav-links.active {
            display: flex;
        }
    }
`;
document.head.appendChild(style);

// FAQ Toggle Functionality
function toggleFAQ(button) {
    const faqItem = button.parentElement;
    const faqAnswer = faqItem.querySelector('.faq-answer');
    const isActive = faqItem.classList.contains('active');
    
    // Close all other FAQ items
    document.querySelectorAll('.faq-item').forEach(item => {
        if (item !== faqItem) {
            item.classList.remove('active');
        }
    });
    
    // Toggle current FAQ item
    if (isActive) {
        faqItem.classList.remove('active');
    } else {
        faqItem.classList.add('active');
        
        // Smooth scroll to the FAQ item if it's not fully visible
        setTimeout(() => {
            const rect = faqItem.getBoundingClientRect();
            const windowHeight = window.innerHeight;
            
            if (rect.bottom > windowHeight) {
                faqItem.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'center' 
                });
            }
        }, 300);
    }
}

// Keyboard accessibility for FAQ
document.addEventListener('DOMContentLoaded', function() {
    const faqQuestions = document.querySelectorAll('.faq-question');
    
    faqQuestions.forEach(question => {
        question.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleFAQ(this);
            }
        });
    });
});