# Gym Manager UI Design System

A comprehensive guide to the visual design, component patterns, and coding standards for the Gym Manager application.

---

## Table of Contents

- [Color Palette](#color-palette)
- [Typography](#typography)
- [Icons](#icons)
- [Components](#components)
- [Badges](#badges)
- [Buttons](#buttons)
- [Cards](#cards)
- [Forms](#forms)
- [Utility Classes](#utility-classes)
- [Coding Standards](#coding-standards)

---

## Color Palette

### Bootstrap Theme Colors

The app uses Bootstrap 5.3+ with a dark theme (`data-bs-theme="dark"`).

| Color | Hex | Usage |
|-------|-----|-------|
| **Primary** | `#0d6efd` | Primary actions, links, category badges |
| **Success** | `#198754` | Success messages, completed status, target values |
| **Danger** | `#dc3545` | Errors, delete actions, primary muscle badges |
| **Warning** | `#ffc107` | Warnings, in-progress status |
| **Info** | `#0dcaf0` | Information, actual logged values |
| **Secondary** | `#6c757d` | Secondary actions, equipment badges, planned status |

### Brand Colors

#### Strava Orange
**Primary brand color for all Strava-related UI elements**

```css
/* Official Strava Orange */
#FC4C02

/* CSS Classes */
.strava-brand      /* Text color */
.bg-strava         /* Background color */
.btn-strava        /* Solid button */
.btn-outline-strava /* Outline button */
.alert-strava      /* Alert/notification */
```

**Usage:**
- ✅ Connect to Strava buttons
- ✅ Strava icon colors
- ✅ Connected status alerts
- ✅ Upload to Strava buttons
- ❌ Disconnect buttons (use `.btn-danger` for destructive actions)

### Exercise Metadata Colors

Standardized color system for exercise information display:

| Badge Class | Color | Hex | Usage |
|-------------|-------|-----|-------|
| `.badge-category` | Blue | `#0d6efd` | Exercise categories (Strength, Cardio, etc.) |
| `.badge-muscle-primary` | Red | `#dc3545` | Primary muscle groups |
| `.badge-muscle-secondary` | Orange | `#fd7e14` | Secondary muscle groups |
| `.badge-equipment` | Gray | `#6c757d` | Required equipment |
| `.badge-target` | Green | `#198754` | Target workout values (sets/reps/weight) |
| `.badge-actual` | Cyan | `#0dcaf0` | Actual logged values |

### Background & Text

| Element | Light Mode | Dark Mode (Active) |
|---------|-----------|-------------------|
| Body Background | N/A | `#212529` |
| Text | N/A | `#f8f9fa` |
| Card Background | N/A | `var(--bs-dark)` |
| Link Color | N/A | `#6ea8fe` |
| Link Hover | N/A | `#8bb9fe` |

---

## Typography

### Font Family
Default Bootstrap 5 system font stack (optimized for performance):
```css
-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif
```

### Responsive Typography

Mobile-first approach with responsive font sizes:

```css
/* Desktop (default) */
h1: 2.5rem
h2: 2rem
h3: 1.75rem

/* Mobile (max-width: 768px) */
h1: 1.75rem
h2: 1.5rem
h3: 1.25rem
```

### Font Weights

- **Bold (700)**: `.navbar-brand`, `.form-label`, `.exercise-item-name`
- **Medium (500)**: Form labels
- **Regular (400)**: Body text

---

## Icons

### Library: Bootstrap Icons

Currently using [Bootstrap Icons](https://icons.getbootstrap.com/) throughout the application.

**Common Icons:**

| Icon Class | Usage |
|-----------|-------|
| `bi-dumbbell` | Workouts, exercises |
| `bi-calendar` | Scheduled dates |
| `bi-bookmark-star` | Templates |
| `bi-strava` | Strava integration (use with `.strava-brand`) |
| `bi-play-fill` | Start/log workout |
| `bi-check-circle` | Complete, success |
| `bi-pencil` | Edit |
| `bi-trash` | Delete |
| `bi-arrow-left` | Back navigation |
| `bi-plus-circle` | Add/create |
| `bi-info-circle` | Information/details |
| `bi-link-45deg` | External links |

**Future Migration:** Plan exists to migrate to FontAwesome (already loaded but unused). See implementation plan Phase 3.

---

## Components

### Exercise Cards

Three standard variants for displaying exercise information:

#### 1. Compact List Item
**Use:** Browse pages, simple lists
**Shows:** Name, category badge, muscle badge, equipment badge, optional targets

```html
<div class="list-group-item">
    <div class="d-flex justify-content-between align-items-start">
        <div>
            <h5 class="mb-1">Exercise Name</h5>
            <div class="mt-2">
                <span class="badge badge-category">Category</span>
                <span class="badge badge-muscle-primary">Primary Muscle</span>
                <span class="badge badge-equipment">Equipment</span>
            </div>
        </div>
        <div class="btn-group">
            <button class="btn btn-sm btn-outline-info btn-touch">Info</button>
            <a class="btn btn-sm btn-outline-success btn-touch">Link</a>
        </div>
    </div>
</div>
```

#### 2. Detailed Card
**Use:** Detail pages, edit panels
**Shows:** Full metadata, description, images, instructions

```html
<div class="card exercise-card">
    <div class="card-header">
        <h5>Exercise Name</h5>
        <span class="badge badge-category">Category</span>
    </div>
    <div class="card-body">
        <p class="text-muted">Description</p>
        <div class="exercise-metadata">
            <span class="badge badge-muscle-primary">Primary</span>
            <span class="badge badge-muscle-secondary">Secondary</span>
            <span class="badge badge-equipment">Equipment</span>
        </div>
        <div class="exercise-targets mt-2">
            <span class="badge badge-target">Target: 3 × 10 @ 50kg</span>
        </div>
    </div>
</div>
```

#### 3. Log Entry
**Use:** Workout logging interface
**Shows:** Name, category, muscles, input fields for sets/reps/weight

```html
<div class="card exercise-log-card mb-3 shadow">
    <div class="card-header bg-primary text-white">
        <h5 class="mb-0">1. Exercise Name</h5>
        <small>Target: 3 × 10 @ 50kg</small>
    </div>
    <div class="card-body">
        <div class="exercise-log-meta mb-3">
            <span class="badge badge-category">Category</span>
            <span class="badge badge-muscle-primary">Muscle</span>
        </div>
        <!-- Input fields for logging -->
    </div>
</div>
```

### Workout Status Badges

```html
<span class="badge bg-planned">Planned</span>      <!-- Gray -->
<span class="badge bg-in-progress">In Progress</span>  <!-- Yellow -->
<span class="badge bg-completed">Completed</span>   <!-- Green -->
```

### Template Privacy Badges

```html
<span class="badge bg-success"><i class="bi bi-globe"></i> Public</span>
<span class="badge bg-secondary"><i class="bi bi-lock"></i> Private</span>
```

---

## Badges

### Semantic Badge Classes

**Always use semantic classes for exercise metadata:**

```html
<!-- Exercise Information -->
<span class="badge badge-category">Strength</span>
<span class="badge badge-muscle-primary">Chest, Triceps</span>
<span class="badge badge-muscle-secondary">Shoulders</span>
<span class="badge badge-equipment">Barbell, Bench</span>

<!-- Workout Values -->
<span class="badge badge-target">Target: 3 × 10 @ 50kg</span>
<span class="badge badge-actual">Actual: 3 × 12 @ 55kg</span>
```

### Badge Sizing

- Default: `padding: 0.5rem 0.75rem; font-size: 0.9rem`
- Small badges in cards: Use default, already appropriately sized

---

## Buttons

### Size Standards

| Size Class | Min Height | Usage |
|-----------|-----------|--------|
| `.btn-lg.btn-touch` | 50px+ | Primary page actions (create, save, submit, delete) |
| `.btn.btn-touch` | 48px | Secondary actions (edit, view, back, connect) |
| `.btn-sm.btn-touch` | 48px | Inline/compact actions (table rows, dense lists) |

**Important:** ALL interactive buttons MUST include `.btn-touch` for mobile accessibility (48px minimum touch target).

### Color Standards by Action Type

| Action Type | Class | Usage |
|------------|-------|--------|
| **Primary** | `.btn-primary` | Main actions, form submissions |
| **Success** | `.btn-success` | Affirmative actions (complete, confirm, external links) |
| **Strava** | `.btn-strava` | Strava connections, uploads |
| **Danger** | `.btn-danger` | Destructive actions (delete, disconnect) |
| **Info** | `.btn-info` | View details, information |
| **Navigation** | `.btn-outline-secondary` | Back, cancel, navigation |

### Button Examples

```html
<!-- Primary page action -->
<button type="submit" class="btn btn-primary btn-lg btn-touch">
    <i class="bi bi-check-circle"></i> Create Workout
</button>

<!-- Secondary action -->
<a href="..." class="btn btn-info btn-touch">
    <i class="bi bi-pencil"></i> Edit
</a>

<!-- Strava action -->
<a href="..." class="btn btn-strava btn-touch">
    <i class="bi bi-link-45deg strava-brand"></i> Connect to Strava
</a>

<!-- Navigation -->
<a href="..." class="btn btn-outline-secondary btn-touch">
    <i class="bi bi-arrow-left"></i> Back
</a>

<!-- Destructive action -->
<button class="btn btn-danger btn-lg btn-touch" onclick="return confirm('Are you sure?')">
    <i class="bi bi-trash"></i> Delete
</button>
```

### Touch Target Requirements

- **Minimum size:** 48×48px (enforced by `.btn-touch`)
- **Recommended spacing:** 8px between adjacent touch targets
- **Button groups:** Use `.btn-group` with proper spacing

---

## Cards

### Shadow Usage

```css
.shadow     /* Elevated cards (main content) */
.shadow-sm  /* Subtle depth (nested cards) */
```

### Card Structure

```html
<div class="card shadow">
    <div class="card-header">
        <h5 class="mb-0">Title</h5>
    </div>
    <div class="card-body">
        <!-- Content -->
    </div>
    <div class="card-footer bg-transparent">
        <!-- Actions -->
    </div>
</div>
```

### Card Styling

- **Background:** `var(--bs-dark)` (dark theme)
- **Border:** `var(--bs-gray-dark)`
- **Hover effect:** `background-color: rgba(255, 255, 255, 0.05)`

---

## Forms

### Input Sizing

```html
<!-- Large inputs for mobile (default on important forms) -->
<input class="form-control form-control-lg" type="text">

<!-- Standard inputs -->
<input class="form-control" type="text">
```

### Form Layout

```html
<div class="mb-3">
    <label for="input-id" class="form-label fw-bold">Label</label>
    <input type="text" class="form-control form-control-lg" id="input-id">
    <small class="text-muted">Helper text</small>
</div>
```

### Validation States

```html
<!-- Error state -->
<input class="form-control is-invalid" type="text">
<div class="invalid-feedback">Error message</div>

<!-- Success state -->
<input class="form-control is-valid" type="text">
<div class="valid-feedback">Success message</div>
```

---

## Utility Classes

### Custom Utilities

```css
/* Scrollable exercise lists */
.exercise-list-scroll {
    max-height: 400px;
    overflow-y: auto;
}

/* Thin progress bars */
.progress-thin {
    height: 5px;
}

/* Hidden by default (JavaScript controlled) */
.d-none-init {
    display: none;
}
```

### Exercise Component Classes

```css
/* List items */
.exercise-item-header
.exercise-item-name
.exercise-item-meta
.exercise-item-actions

/* Detailed cards */
.exercise-card
.exercise-metadata
.exercise-targets

/* Logging interface */
.exercise-log-card
.exercise-log-meta
.exercise-log-inputs
```

---

## Coding Standards

### CSS Organization

Files are organized by specificity:

1. **Bootstrap base** (loaded via CDN)
2. **FontAwesome** (loaded from `/static/fontawesome/`)
3. **Custom styles** (`/static/css/custom.css`):
   - Mobile-first responsive utilities
   - Touch-friendly controls
   - Dark theme optimizations
   - Component styles
   - Strava brand utilities
   - Exercise metadata badges
   - Design system documentation (in comments)

### Template Structure

```html
{% extends "base.html" %}

{% block title %}Page Title{% endblock %}

{% block content %}
<div class="container">
    <h1>Page Heading</h1>

    <!-- Content sections -->

    <!-- Navigation/actions at bottom -->
    <a href="..." class="btn btn-outline-secondary btn-touch">
        <i class="bi bi-arrow-left"></i> Back
    </a>
</div>

<!-- Include shared components -->
{% include 'includes/exercise_details_modal.html' %}
{% endblock %}
```

### Component Reusability

- **Shared components:** Store in `templates/includes/`
- **Modal dialogs:** Extract to includes if used in 2+ places
- **Badge patterns:** Use semantic classes, not inline colors
- **Button patterns:** Follow size/color standards consistently

### Inline Styles

**Avoid inline styles.** Use CSS classes instead.

**Exceptions:**
- JavaScript-controlled display properties (`style="display: none"`)
- Dynamic values (progress bar width, etc.)

### Accessibility Requirements

- ✅ All buttons have `.btn-touch` (48px touch targets)
- ✅ Form inputs have associated labels
- ✅ Color is not the only indicator (use icons + text)
- ✅ Focus states are visible
- ✅ Alt text on images
- ✅ ARIA labels where appropriate

---

## Migration Notes

### Completed Migrations

- **2024**: Extracted exercise details modal to shared component (eliminated ~760 lines duplicate code)
- **2024**: Established Strava brand color system (official orange #FC4C02)
- **2024**: Standardized exercise metadata badge colors
- **2024**: Removed inline styles, created utility classes
- **2024**: Enhanced workout logging with exercise metadata display
- **2024**: Database query optimization (added category/muscle data to workout exercises)

### Planned Migrations

- **Phase 3 (Future)**: Migrate from Bootstrap Icons to FontAwesome
  - FontAwesome already loaded (~500KB committed)
  - Need to replace 22+ templates
  - Create icon mapping document first
  - Remove Bootstrap Icons CDN after migration

---

## Component Examples

### Example: Exercise Browse List

```html
<div class="list-group mb-4">
    {% for exercise in exercises %}
        <div class="list-group-item">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h5 class="mb-1">{{ exercise.name }}</h5>
                    <p class="mb-1 text-muted small">{{ exercise.description[:100] }}</p>

                    <div class="mt-2">
                        <span class="badge badge-category">{{ exercise.category_name }}</span>
                        <span class="badge badge-muscle-primary">{{ exercise.primary_muscles }}</span>
                    </div>
                </div>
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-outline-info btn-touch view-exercise-details"
                            data-exercise-id="{{ exercise.id }}"
                            data-exercise-name="{{ exercise.name }}">
                        <i class="bi bi-info-circle"></i>
                    </button>
                    <a href="{{ exercise.name | exercem_url }}"
                       class="btn btn-sm btn-outline-success btn-touch"
                       target="_blank">
                        <i class="bi bi-link-45deg"></i>
                    </a>
                </div>
            </div>
        </div>
    {% endfor %}
</div>

{% include 'includes/exercise_details_modal.html' %}
```

### Example: Workout Card (Dashboard)

```html
<div class="card shadow mb-3">
    <div class="card-body">
        <h5 class="card-title">
            <i class="bi bi-dumbbell"></i> {{ workout.name }}
        </h5>
        <p class="text-muted small mb-2">
            <i class="bi bi-calendar"></i> {{ workout.scheduled_date }}
        </p>
        <span class="badge bg-{{ workout.status_color }} mb-2">
            {{ workout.status }}
        </span>
        <br>
        {% if workout.status != 'completed' %}
            <a href="{{ url_for('workouts.log', workout_id=workout.id) }}"
               class="btn btn-primary btn-touch">
                <i class="bi bi-play-fill"></i> Log
            </a>
        {% endif %}
        <a href="{{ url_for('workouts.detail', workout_id=workout.id) }}"
           class="btn btn-info btn-touch">
            <i class="bi bi-eye"></i> View
        </a>
    </div>
</div>
```

---

## Best Practices

### When Adding New Features

1. **Use existing components** before creating new ones
2. **Follow color standards** for all badges and buttons
3. **Include `.btn-touch`** on ALL interactive buttons
4. **Use semantic badge classes** for exercise metadata
5. **Test on mobile** (minimum 48px touch targets)
6. **Avoid inline styles** (use CSS classes)
7. **Check this design system** for established patterns

### When Creating Strava Features

1. Use `.btn-strava` for connection/upload buttons
2. Add `.strava-brand` class to Strava icons
3. Use `.alert-strava` for connected status messages
4. Keep destructive actions (disconnect) as `.btn-danger`
5. Test with official Strava orange: `#FC4C02`

### When Displaying Exercises

1. Show category with `.badge-category` (blue)
2. Show primary muscles with `.badge-muscle-primary` (red)
3. Show equipment with `.badge-equipment` (gray) if present
4. Use appropriate card variant (compact/detailed/log)
5. Include info button linked to exercise details modal

---

## Resources

- [Bootstrap 5.3 Documentation](https://getbootstrap.com/docs/5.3/)
- [Bootstrap Icons](https://icons.getbootstrap.com/)
- [Strava Brand Guidelines](https://www.strava.com/about/brand)
- [Custom CSS](/static/css/custom.css)
- [Button Audit Findings](/tmp/button-audit-findings.md)

---

## Questions?

When in doubt:
1. Check this design system documentation
2. Look at existing similar components
3. Follow Bootstrap conventions
4. Maintain consistency with established patterns

**Last Updated:** 2026-01-06
**Version:** 1.0
