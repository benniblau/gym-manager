# Icon Migration Guide: Bootstrap Icons → FontAwesome

## Overview

This document maps Bootstrap Icons (bi-*) to their FontAwesome equivalents for the icon migration project. FontAwesome is already loaded in the application, so we're eliminating the redundant Bootstrap Icons library.

## Icon Syntax

**Bootstrap Icons**:
```html
<i class="bi bi-icon-name"></i>
```

**FontAwesome**:
```html
<!-- Solid (default) -->
<i class="fa-solid fa-icon-name"></i>

<!-- Regular (outline style) -->
<i class="fa-regular fa-icon-name"></i>

<!-- Brands (logos) -->
<i class="fa-brands fa-icon-name"></i>
```

## Complete Icon Mapping

### Navigation & Core UI

| Bootstrap Icon | FontAwesome Equivalent | Usage |
|----------------|------------------------|-------|
| `bi-house` | `fa-solid fa-house` | Home/Dashboard |
| `bi-gear` | `fa-solid fa-gear` | Settings |
| `bi-box-arrow-right` | `fa-solid fa-right-from-bracket` | Logout |
| `bi-person-circle` | `fa-solid fa-circle-user` | User profile |
| `bi-arrow-left` | `fa-solid fa-arrow-left` | Back navigation |
| `bi-x` | `fa-solid fa-xmark` | Close/Clear |
| `bi-x-circle` | `fa-solid fa-circle-xmark` | Disconnect/Cancel |

### Workouts & Exercise

| Bootstrap Icon | FontAwesome Equivalent | Usage |
|----------------|------------------------|-------|
| `bi-calendar` | `fa-solid fa-calendar` | Schedule/Date |
| `bi-clock` | `fa-solid fa-clock` | Time |
| `bi-play-fill` | `fa-solid fa-play` | Start/Log workout |
| `bi-check-circle` | `fa-solid fa-circle-check` | Complete/Success |
| `bi-check-lg` | `fa-solid fa-check` | Confirm/Update |
| `bi-plus-circle` | `fa-solid fa-circle-plus` | Add/Create |
| `bi-pencil` | `fa-solid fa-pencil` | Edit |
| `bi-trash` | `fa-solid fa-trash` | Delete |
| `bi-eye` | `fa-solid fa-eye` | View |
| `bi-info-circle` | `fa-solid fa-circle-info` | Information |
| `bi-list-check` | `fa-solid fa-list-check` | Exercise list |
| `bi-list-ul` | `fa-solid fa-list-ul` | List |
| `bi-activity` | `fa-solid fa-heart-pulse` | Muscles/Activity |
| `bi-dash-lg` | `fa-solid fa-minus` | Decrease/Minus |
| `bi-plus-lg` | `fa-solid fa-plus` | Increase/Plus |
| `bi-arrow-up` | `fa-solid fa-arrow-up` | Move up |
| `bi-arrow-down` | `fa-solid fa-arrow-down` | Move down |

### Templates & Bookmarks

| Bootstrap Icon | FontAwesome Equivalent | Usage |
|----------------|------------------------|-------|
| `bi-bookmark-star` | `fa-solid fa-bookmark` | Template |
| `bi-bookmark` | `fa-solid fa-bookmark` | Template (simple) |
| `bi-bookmarks` | `fa-solid fa-book-bookmark` | Multiple templates |
| `bi-globe` | `fa-solid fa-globe` | Public |
| `bi-lock` | `fa-solid fa-lock` | Private |
| `bi-fire` | `fa-solid fa-fire` | Popular/Most used |
| `bi-sort-alpha-down` | `fa-solid fa-arrow-down-a-z` | Alphabetical sort |
| `bi-people` | `fa-solid fa-users` | Usage count |

### Forms & Input

| Bootstrap Icon | FontAwesome Equivalent | Usage |
|----------------|------------------------|-------|
| `bi-envelope` | `fa-solid fa-envelope` | Email |
| `bi-key` | `fa-solid fa-key` | Password |
| `bi-key-fill` | `fa-solid fa-key` | Password (filled) |
| `bi-search` | `fa-solid fa-magnifying-glass` | Search |
| `bi-tools` | `fa-solid fa-wrench` | Equipment |
| `bi-tag` | `fa-solid fa-tag` | Category |

### Notes & Content

| Bootstrap Icon | FontAwesome Equivalent | Usage |
|----------------|------------------------|-------|
| `bi-sticky` | `fa-solid fa-note-sticky` | Notes |
| `bi-card-heading` | `fa-solid fa-heading` | Heading/Title |

### Links & External

| Bootstrap Icon | FontAwesome Equivalent | Usage |
|----------------|------------------------|-------|
| `bi-link-45deg` | `fa-solid fa-link` | External link |
| `bi-upload` | `fa-solid fa-upload` | Upload |
| `bi-chevron-right` | `fa-solid fa-chevron-right` | Next/Forward |

### Alerts & Status

| Bootstrap Icon | FontAwesome Equivalent | Usage |
|----------------|------------------------|-------|
| `bi-exclamation-triangle` | `fa-solid fa-triangle-exclamation` | Warning |
| `bi-check-circle` | `fa-solid fa-circle-check` | Success |
| `bi-info-circle` | `fa-solid fa-circle-info` | Information |
| `bi-x-circle` | `fa-solid fa-circle-xmark` | Error/Cancel |

### Brands

| Bootstrap Icon | FontAwesome Equivalent | Usage |
|----------------|------------------------|-------|
| `bi-strava` | `fa-brands fa-strava` | Strava logo |

### Special Cases

| Bootstrap Icon | FontAwesome Equivalent | Notes |
|----------------|------------------------|-------|
| `bi-cloud-check` | `fa-solid fa-cloud-arrow-up` | Auto-save indicator |
| `bi-shield-lock` | `fa-solid fa-shield-halved` | Privacy/Security |

## Migration Steps

### 1. Update Template
Replace Bootstrap Icon classes with FontAwesome equivalents:

**Before**:
```html
<i class="bi bi-calendar"></i>
```

**After**:
```html
<i class="fa-solid fa-calendar"></i>
```

### 2. Preserve Additional Classes
Keep utility classes (colors, sizing, etc.):

**Before**:
```html
<i class="bi bi-strava strava-brand"></i>
```

**After**:
```html
<i class="fa-brands fa-strava strava-brand"></i>
```

### 3. Update Combined Selectors
Be careful with complex class combinations:

**Before**:
```html
<i class="bi bi-check-circle text-success"></i>
```

**After**:
```html
<i class="fa-solid fa-circle-check text-success"></i>
```

## Templates by Priority

### Priority 1 - Core Templates (8 files)
- `base.html` - Navigation icons
- `main/dashboard.html` - Dashboard widgets
- `auth/login.html` - Form icons
- `auth/register.html` - Form icons
- `auth/settings.html` - Settings icons

### Priority 2 - Workout Templates (6 files)
- `workouts/list.html`
- `workouts/detail.html`
- `workouts/log.html`
- `workouts/create.html`
- `workouts/edit.html`

### Priority 3 - Template System (5 files)
- `templates/list.html`
- `templates/detail.html`
- `templates/edit.html`
- `templates/browse_public.html`
- `templates/create.html`

### Priority 4 - Exercise Pages (3 files)
- `exercises/browse.html`
- `exercises/detail.html`
- `includes/exercise_details_modal.html`

## Testing Checklist

After migration:
- [ ] All icons render correctly (no broken/missing icons)
- [ ] Icon sizes match previous design
- [ ] Icon colors respect utility classes
- [ ] Brand icons (Strava) display correctly
- [ ] Mobile view icons are visible
- [ ] No console errors about missing fonts

## Removal Steps

After all templates are migrated:

1. **Remove Bootstrap Icons CDN** from `base.html`:
   ```html
   <!-- REMOVE THIS -->
   <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
   ```

2. **Verify FontAwesome is loaded** in `base.html`:
   ```html
   <!-- KEEP THIS -->
   <link rel="stylesheet" href="{{ url_for('static', filename='fontawesome/css/fontawesome.css') }}">
   <link rel="stylesheet" href="{{ url_for('static', filename='fontawesome/css/solid.css') }}">
   <link rel="stylesheet" href="{{ url_for('static', filename='fontawesome/css/brands.css') }}">
   ```

3. **Test all pages** to ensure icons render correctly

## Performance Impact

- **Before**: ~500KB Bootstrap Icons (unused) + FontAwesome (used)
- **After**: FontAwesome only
- **Savings**: ~500KB eliminated, faster page loads

## Notes

- FontAwesome uses three-part class structure: `fa-[style] fa-[icon-name]`
- Styles: `solid` (default), `regular` (outlined), `brands` (logos)
- Some icon names differ significantly (e.g., `bi-box-arrow-right` → `fa-right-from-bracket`)
- Always test after migration to ensure visual consistency
