/**
 * Client-side JavaScript for Course Outline to iCalendar Converter
 * 
 * This file contains JavaScript functions for enhancing the user experience
 * in the web interface. It handles form interactions, validation, and
 * dynamic content updates.
 */

// A page whose content is hidden until a script succeeds is a page one typo
// can blank. The reveal animation only arms itself once initMotion() adds
// `motion-ready`, and the first uncaught error takes it straight back off.
window.addEventListener('error', function () {
    document.documentElement.classList.remove('motion-ready');
});

/** Run one initialiser; a failure in it must not take the others with it. */
function boot(name, fn) {
    try {
        fn();
    } catch (err) {
        console.error('Plato: ' + name + ' failed', err);
        document.documentElement.classList.remove('motion-ready');
    }
}

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize form enhancements
    boot('initMotion', initMotion);
    boot('initFormValidation', initFormValidation);
    boot('initDynamicForms', initDynamicForms);
    boot('initEditableFields', initEditableFields);
    boot('initManualSectionAdders', initManualSectionAdders);
    boot('initAssessmentAddRemove', initAssessmentAddRemove);
    boot('initHeaderShadow', initHeaderShadow);
    boot('initDownloadConfirm', initDownloadConfirm);
    boot('drawIcons', drawIcons);
    
    // The Generate button only has work to do when a field is still open in
    // its inline editor: save that edit first, then submit. Otherwise the
    // native submit runs and the confirmation handler picks it up.
    const generateBtn = document.getElementById('generate-calendar-btn');
    const reviewForm = document.getElementById('review-form');
    if (generateBtn && reviewForm) {
        generateBtn.addEventListener('click', function (e) {
            const editingField = document.querySelector('.editable-field.editing');
            if (!editingField) return;

            const input = editingField.querySelector('.inline-edit-input');
            if (!input) {
                // Mid-save, with no input to read: leave editing mode and go on.
                editingField.classList.remove('editing');
                return;
            }

            const fieldType = editingField.getAttribute('data-field-type');
            const assessmentIndex = editingField.getAttribute('data-assessment-index');
            const newValue = input.value.trim();
            const clearable = fieldType === 'assessment_due_date' || fieldType === 'term_start' || fieldType === 'term_end';

            if (!newValue && !clearable) {
                // Nothing typed: drop the edit and let the submit through.
                editingField.innerHTML = editingField.getAttribute('data-original-content') || '';
                editingField.classList.remove('editing');
                return;
            }

            e.preventDefault();
            const originalContent = editingField.getAttribute('data-original-content') || editingField.textContent;
            saveField(editingField, fieldType, newValue, assessmentIndex, originalContent);
            setTimeout(function () {
                if (document.querySelector('.editable-field.editing')) {
                    showReviewNotice('Still saving your edit; click Generate calendar again in a moment.');
                    return;
                }
                submitReview(reviewForm);
            }, 500);
        });
    }
});

/**
 * Submit the review form in a way that still fires the submit event, so the
 * download confirmation can read the response. form.submit() would skip it.
 */
function submitReview(form) {
    if (typeof form.requestSubmit === 'function') form.requestSubmit();
    else form.submit();
}

/**
 * Initialize form validation
 * Provides client-side validation feedback
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (e.defaultPrevented) return;   // an earlier handler already stopped this submit
            // Basic validation - browser will handle required fields
            // Add custom validation here if needed
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('error');
                } else {
                    field.classList.remove('error');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                showReviewNotice('Please fill in all required fields.');
            }
        });
    });
}

/**
 * Initialize dynamic form elements
 * Handles show/hide logic for conditional form fields
 */
function initDynamicForms() {
    // Handle checkbox-triggered show/hide
    const checkboxes = document.querySelectorAll('input[type="checkbox"][data-toggle]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const targetId = this.getAttribute('data-toggle');
            const target = document.getElementById(targetId);
            if (target) {
                target.style.display = this.checked ? 'block' : 'none';
            }
        });
    });
}

/**
 * Format date for display
 * Converts ISO date string to readable format
 * 
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date string
 */
function formatDate(dateString) {
    if (!dateString) return 'Not specified';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

/**
 * Format time for display
 * Converts time string to readable format
 * 
 * @param {string} timeString - Time string (HH:MM)
 * @returns {string} Formatted time string
 */
function formatTime(timeString) {
    if (!timeString) return 'Not specified';
    const [hours, minutes] = timeString.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    return `${displayHour}:${minutes} ${ampm}`;
}

/**
 * Show loading indicator
 * Displays a loading message while processing
 * 
 * @param {string} message - Loading message to display
 */
function showLoading(message) {
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'loading-indicator';
    loadingDiv.className = 'loading';
    loadingDiv.innerHTML = `
        <div class="loading-spinner"></div>
        <p>${message || 'Processing...'}</p>
    `;
    document.body.appendChild(loadingDiv);
}

/**
 * Hide loading indicator
 * Removes the loading message
 */
function hideLoading() {
    const loadingDiv = document.getElementById('loading-indicator');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

/**
 * Validate PDF file
 * Checks if uploaded file is a valid PDF
 * 
 * @param {File} file - File object to validate
 * @returns {boolean} True if file is valid PDF
 */
function validatePDFFile(file) {
    if (!file) return false;
    
    // Check file extension
    const extension = file.name.split('.').pop().toLowerCase();
    if (extension !== 'pdf') {
        showReviewNotice('Only PDF files can be read.');
        return false;
    }
    
    // Check file size: Vercel's function accepts 4.5 MB request bodies, so 4 MB of PDF
    const maxSize = 4 * 1024 * 1024;
    if (file.size > maxSize) {
        showReviewNotice('That file is ' + (file.size / 1024 / 1024).toFixed(1) + ' MB; the free hosting accepts up to 4 MB.');
        return false;
    }
    
    return true;
}

/**
 * Parse days of week string
 * Converts day abbreviations to array of day numbers
 * 
 * @param {string} daysStr - Day string (e.g., "MWF" or "Mon/Wed/Fri")
 * @returns {Array<number>} Array of day numbers (0=Monday, 6=Sunday)
 */
function parseDaysOfWeek(daysStr) {
    if (!daysStr) return [];
    
    const dayMap = {
        'M': 0, 'Mon': 0, 'Monday': 0,
        'T': 1, 'Tue': 1, 'Tuesday': 1,
        'W': 2, 'Wed': 2, 'Wednesday': 2,
        'Th': 3, 'Thu': 3, 'Thursday': 3,
        'F': 4, 'Fri': 4, 'Friday': 4,
        'S': 5, 'Sat': 5, 'Saturday': 5,
        'Su': 6, 'Sun': 6, 'Sunday': 6,
    };
    
    const days = [];
    const upper = daysStr.toUpperCase();
    
    // Simple parsing - can be enhanced
    for (let i = 0; i < upper.length; i++) {
        const char = upper[i];
        if (char === 'M' && (i === 0 || upper[i-1] !== 'T')) {
            days.push(0);
        } else if (char === 'T') {
            if (i + 1 < upper.length && upper[i+1] === 'H') {
                days.push(3); // Thursday
                i++;
            } else {
                days.push(1); // Tuesday
            }
        } else if (char === 'W') {
            days.push(2);
        } else if (char === 'F') {
            days.push(4);
        }
    }
    
    return [...new Set(days)].sort();
}

/**
 * Initialize editable fields functionality
 * Makes missing or reviewable fields clickable for inline editing
 */
function initEditableFields() {
    // First, find all editable fields and add direct click listeners
    const editableFields = document.querySelectorAll('.editable-field');
    if (editableFields.length === 0) {
        return;
    }
    
    editableFields.forEach((field, index) => {
        field._isEditable = true;

        // Enter or Space opens the editor, so a keyboard visitor can proof
        // every field without a pointer (the spans carry role="button").
        field.addEventListener('keydown', function (e) {
            if (e.key !== 'Enter' && e.key !== ' ' && e.key !== 'Spacebar') return;
            if (e.target.closest('.inline-edit-form')) return;
            e.preventDefault();
            if (!this.classList.contains('editing')) startEditing(this);
        });
        
        // Use onclick as primary handler (most reliable)
        field.onclick = function(e) {
            // Don't handle clicks on buttons or inside the edit form
            const target = e.target;
            if (target.closest('.inline-edit-form') || 
                target.closest('.btn-save') || 
                target.closest('.btn-cancel') ||
                target.closest('button') ||
                target.closest('input')) {
                return true; // Allow the click to proceed
            }
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            
            if (!this.classList.contains('editing')) {
                startEditing(this);
            }
            return false;
        };
        
        // Also add event listener as backup
        field.addEventListener('click', function(e) {
            // Don't handle clicks on buttons or inside the edit form
            const target = e.target;
            if (target.closest('.inline-edit-form') || 
                target.closest('.btn-save') || 
                target.closest('.btn-cancel') ||
                target.closest('button') ||
                target.closest('input')) {
                return true; // Allow the click to proceed
            }
            e.preventDefault();
            e.stopPropagation();
            if (!this.classList.contains('editing')) {
                startEditing(this);
            }
            return false;
        }, true); // Capture phase
        
        // Prevent form submission when clicking
        field.addEventListener('mousedown', function(e) {
            e.stopPropagation();
        }, true);
    });
}

/**
 * Start editing a field
 * Replaces the field display with an input form
 * 
 * @param {HTMLElement} fieldElement - The field element to edit
 */
function startEditing(fieldElement) {
    if (!fieldElement) {
        console.error('startEditing: fieldElement is null or undefined');
        return;
    }
    
    // Don't start editing if already in edit mode
    if (fieldElement.classList.contains('editing')) {
        return;
    }
    
    const fieldType = fieldElement.getAttribute('data-field-type');
    let currentValue = fieldElement.getAttribute('data-current-value') || '';
    
    // For assessment_title, extract text from <strong> tag if data attribute is empty
    if (fieldType === 'assessment_title' && !currentValue) {
        const strongTag = fieldElement.querySelector('strong');
        if (strongTag) {
            currentValue = strongTag.textContent.trim();
        }
    }
    
    const assessmentIndex = fieldElement.getAttribute('data-assessment-index');
    // Determine input type based on field type
    let inputType = 'text';
    let placeholder = '';
    let inputValue = currentValue;
    
    if (fieldType === 'term_start' || fieldType === 'term_end') {
        inputType = 'date';
        // For date fields, just use the date part
        if (currentValue && currentValue.includes('T')) {
            inputValue = currentValue.split('T')[0];
        } else if (currentValue && currentValue.includes(' ')) {
            inputValue = currentValue.split(' ')[0];
        } else {
            inputValue = currentValue;
        }
        placeholder = 'YYYY-MM-DD';
    } else if (fieldType === 'assessment_due_date') {
        inputType = 'datetime-local';
        // Convert YYYY-MM-DD to datetime-local format if needed
        if (currentValue && !currentValue.includes('T') && !currentValue.includes(' ')) {
            inputValue = currentValue + 'T00:00';
        } else if (currentValue && currentValue.includes(' ')) {
            inputValue = currentValue.replace(' ', 'T');
        }
        placeholder = 'YYYY-MM-DD HH:MM';
    } else if (fieldType === 'assessment_weight') {
        inputType = 'number';
        inputValue = currentValue;
        placeholder = 'Enter weight (%)';
    } else if (fieldType === 'assessment_lead_time') {
        inputType = 'number';
        inputValue = currentValue;
        placeholder = 'Enter lead time (days)';
        min = 0;  // Lead time must be non-negative
    } else if (fieldType === 'lead_time_mapping') {
        inputType = 'number';
        inputValue = currentValue;
        placeholder = 'Enter lead time (days)';
        min = 0;  // Lead time must be non-negative
    } else if (fieldType === 'assessment_title') {
        inputType = 'text';
        inputValue = currentValue;
        placeholder = 'Enter assessment title';
    } else {
        placeholder = 'Enter value';
    }
    
    // Create input form - make sure it doesn't submit parent form
    const editForm = document.createElement('form');
    editForm.className = 'inline-edit-form';
    editForm.style.display = 'inline-block';
    editForm.style.position = 'relative';
    editForm.style.zIndex = '1000';
    editForm.onsubmit = function(e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        return false;
    };
    // Build min/max/step attributes for number inputs
    let numberAttrs = '';
    if (inputType === 'number') {
        if (fieldType === 'assessment_weight') {
            numberAttrs = 'min="0" max="100" step="0.1"';
        } else if (fieldType === 'assessment_lead_time' || fieldType === 'lead_time_mapping') {
            numberAttrs = 'min="0" step="1"';
        } else {
            numberAttrs = 'min="0"';
        }
    }
    
    editForm.innerHTML = `
        <div class="inline-edit-container">
            <input type="${inputType}" 
                   class="inline-edit-input" 
                   value="${escapeHtml(inputValue)}" 
                   placeholder="${placeholder}"
                   ${numberAttrs}
                   autofocus>
            <div class="inline-edit-buttons">
                <button type="submit" class="btn-save save-btn" style="pointer-events: auto; z-index: 1001;">Save</button>
                <button type="button" class="btn-cancel cancel-btn" style="pointer-events: auto; z-index: 1001;">Cancel</button>
            </div>
        </div>
    `;
    
    // Store original content
    const originalContent = fieldElement.innerHTML;
    const originalDisplay = fieldElement.style.display;
    
    // Store original content as attribute for later retrieval
    fieldElement.setAttribute('data-original-content', originalContent);
    
    // Replace field with form
    fieldElement.innerHTML = '';
    fieldElement.appendChild(editForm);
    fieldElement.classList.add('editing');
    const input = editForm.querySelector('.inline-edit-input');
    const saveBtn = editForm.querySelector('.btn-save');
    const cancelBtn = editForm.querySelector('.btn-cancel');
    if (input) {
        // Use setTimeout to ensure focus works after DOM update
        setTimeout(() => {
            input.focus();
            input.select();
        }, 10);
    }
    
    // Handle form submission - prevent bubbling to parent form
    editForm.addEventListener('submit', function(e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        const newValue = input.value.trim();
        saveField(fieldElement, fieldType, newValue, assessmentIndex, originalContent);
        return false;
    }, true); // Use capture phase
    
    // Handle save button click directly (in case form submit doesn't work)
    // saveBtn is already declared above, so just use it
    if (saveBtn) {
        // Use both capture and bubble phases to ensure we catch the event
        saveBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            const newValue = input.value.trim();
            saveField(fieldElement, fieldType, newValue, assessmentIndex, originalContent);
            return false;
        }, true); // Capture phase
        
        saveBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            const newValue = input.value.trim();
            saveField(fieldElement, fieldType, newValue, assessmentIndex, originalContent);
            return false;
        }, false); // Bubble phase
        
        // Also use onclick as a fallback
        saveBtn.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            const newValue = input.value.trim();
            saveField(fieldElement, fieldType, newValue, assessmentIndex, originalContent);
            return false;
        };
    }
    
    // Handle cancel
    // cancelBtn is already declared above, so just use it
    if (cancelBtn) {
        // Use both capture and bubble phases to ensure we catch the event
        cancelBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            fieldElement.innerHTML = originalContent;
            fieldElement.classList.remove('editing');
            return false;
        }, true); // Capture phase
        
        cancelBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            fieldElement.innerHTML = originalContent;
            fieldElement.classList.remove('editing');
            return false;
        }, false); // Bubble phase
        
        // Also use onclick as a fallback
        cancelBtn.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            fieldElement.innerHTML = originalContent;
            fieldElement.classList.remove('editing');
            return false;
        };
    }
    
    // Handle escape key
    if (input) {
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                e.preventDefault();
                fieldElement.innerHTML = originalContent;
                fieldElement.classList.remove('editing');
            } else if (e.key === 'Enter') {
                // Auto-save on Enter key
                e.preventDefault();
                const newValue = input.value.trim();
                if (newValue || fieldType === 'assessment_due_date' || fieldType === 'term_start' || fieldType === 'term_end') {
                    // Allow empty dates to be saved (clears the field)
                    saveField(fieldElement, fieldType, newValue, assessmentIndex, originalContent);
                }
            }
        });
        
        // Auto-save on blur (when user clicks outside) - especially important for date inputs
        input.addEventListener('blur', function(e) {
            // Use setTimeout to allow click events on save/cancel buttons to fire first
            setTimeout(() => {
                // Check if we're still in editing mode (buttons might have already saved/cancelled)
                if (fieldElement.classList.contains('editing')) {
                    const newValue = input.value.trim();
                    // For date fields, allow saving even if empty (to clear the date)
                    if (newValue || fieldType === 'assessment_due_date' || fieldType === 'term_start' || fieldType === 'term_end') {
                        saveField(fieldElement, fieldType, newValue, assessmentIndex, originalContent);
                    } else {
                        // If no value and not a date field, cancel the edit
                        fieldElement.innerHTML = originalContent;
                        fieldElement.classList.remove('editing');
                    }
                }
            }, 200); // Small delay to let button clicks process first
        });
    }
}

/**
 * Save field value to server
 * 
 * @param {HTMLElement} fieldElement - The field element
 * @param {string} fieldType - Type of field being edited
 * @param {string} newValue - New value to save
 * @param {string} assessmentIndex - Assessment index if editing assessment
 * @param {string} originalContent - Original HTML content to restore on error
 */
function saveField(fieldElement, fieldType, newValue, assessmentIndex, originalContent) {
    // Show loading state
    fieldElement.innerHTML = '<span class="saving">Saving...</span>';
    
    // Prepare request data
    const requestData = {
        field_type: fieldType,
        value: newValue || null
    };
    
    if (assessmentIndex !== null) {
        requestData.assessment_index = parseInt(assessmentIndex);
    }
    
    // For lead time mapping, include the weight range
    if (fieldType === 'lead_time_mapping') {
        const weightRange = fieldElement.getAttribute('data-weight-range');
        if (weightRange) {
            requestData.weight_range = weightRange;
        }
    }
    
    // Send update request
    fetch('/api/update-field', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update display with new value and leave editing mode (the Download button
            // refuses to submit while any field still carries the "editing" class)
            updateFieldDisplay(fieldElement, fieldType, newValue);
            fieldElement.classList.remove('editing');
            applyCompleteness(data.completeness);
            applyRowState(fieldElement, data.row);
            announceSave(data.completeness);
            // Show success message briefly
            fieldElement.classList.add('saved');
            setTimeout(() => {
                fieldElement.classList.remove('saved');
            }, 2000);
        } else {
            // Show error and restore original
            showReviewNotice('Could not save: ' + (data.error || 'unknown error'));
            fieldElement.innerHTML = originalContent;
            fieldElement.classList.remove('editing');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showReviewNotice('Could not save the field (network error). Please try again.');
        fieldElement.innerHTML = originalContent;
        fieldElement.classList.remove('editing');
    });
}

/**
 * Say "saved" out loud. The failure path has role="status" on the notice box,
 * but a success was silent — and the whole task is fixing flagged fields, so a
 * screen-reader user got no confirmation and no updated count.
 */
function announceSave(completeness) {
    const el = document.getElementById('save-status');
    if (!el) return;
    const tail = completeness && completeness.summary_undated ? ' ' + completeness.summary_undated : '';
    el.textContent = 'Saved.' + tail;
}

/**
 * Inline notice on the review page (replaces native alert(), which freezes the tab)
 */
function showReviewNotice(message, kind) {
    let box = document.getElementById('review-notice');
    if (!box) {
        box = document.createElement('div');
        box.id = 'review-notice';
        box.className = 'alert alert-warning review-notice';
        box.setAttribute('role', 'status');
        const form = document.getElementById('review-form');
        (form ? form.parentNode : document.body).insertBefore(box, form || null);
    }
    box.className = 'alert alert-' + (kind || 'warning') + ' review-notice';
    box.textContent = message;
    box.style.display = 'block';
    clearTimeout(box._hide);
    box._hide = setTimeout(() => { box.style.display = 'none'; }, 6000);
}

/**
 * Update field display after successful save
 * 
 * @param {HTMLElement} fieldElement - The field element
 * @param {string} fieldType - Type of field
 * @param {string} newValue - New value
 */
function updateFieldDisplay(fieldElement, fieldType, newValue) {
    let displayValue = newValue || 'Not found';
    
    // Format display based on field type
    if (fieldType === 'term_start' || fieldType === 'term_end') {
        if (newValue) {
            // Extract date part (YYYY-MM-DD) - already just a date
            displayValue = newValue.split('T')[0].split(' ')[0];
        } else {
            displayValue = 'Not found';
        }
    } else if (fieldType === 'assessment_due_date') {
        if (newValue) {
            // Same shape as the server renders: "Mar 20, 2026" plus the time unless it is 23:59
            displayValue = formatDueDate(newValue);
        } else {
            displayValue = 'Add date';
        }
    } else if (fieldType === 'assessment_weight') {
        if (newValue) {
            displayValue = newValue + '%';
        } else {
            displayValue = 'Add weight';
        }
    } else if (fieldType === 'assessment_lead_time') {
        if (newValue) {
            displayValue = newValue + ' days';
        } else {
            displayValue = 'Not set';
        }
    } else if (fieldType === 'lead_time_mapping') {
        if (newValue) {
            displayValue = newValue + ' days before due';
        } else {
            displayValue = 'Not set';
        }
    } else if (fieldType === 'assessment_title') {
        displayValue = newValue || 'Untitled';
    } else if (fieldType === 'course_code' || fieldType === 'course_name') {
        displayValue = newValue || 'Not found';
    }
    
    // Update the field
    const isMissing = !newValue || newValue === '' || displayValue === 'Not found' || displayValue === 'Not set';
    
    // For assessment_title, preserve the <strong> tag structure; date and weight keep their icon
    if (fieldType === 'assessment_title') {
        fieldElement.innerHTML = `<strong>${escapeHtml(displayValue)}</strong>`;
    } else {
        fieldElement.textContent = displayValue;
    }
    
    fieldElement.setAttribute('data-current-value', newValue || '');
    
    if (isMissing) {
        fieldElement.classList.add('missing-field');
    } else {
        fieldElement.classList.remove('missing-field');
    }
    
    // Update completeness metrics without full page reload
    // The field display has been updated, so we're done
    // User can continue editing other fields
}

function escapeHtml(text) {
    return String(text).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}

/**
 * "2026-04-20 09:00" / "2026-04-20T09:00" -> "Apr 20, 2026 9:00 AM"; 23:59 shows the date only.
 */
function formatDueDate(value) {
    const m = String(value).match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/);
    if (!m) return value;
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    let out = `${months[parseInt(m[2], 10) - 1]} ${m[3]}, ${m[1]}`;
    if (m[4] !== undefined && !(m[4] === '23' && m[5] === '59')) {
        const h = parseInt(m[4], 10);
        out += ` ${((h + 11) % 12) + 1}:${m[5]} ${h < 12 ? 'AM' : 'PM'}`;
    }
    return out;
}

/**
 * Re-render the four summary tiles from the numbers the server just computed (D19).
 */
function applyCompleteness(c) {
    if (!c) return;
    const say = (name, text) => {
        const el = document.querySelector(`[data-summary="${name}"]`);
        if (el && typeof text === 'string') el.textContent = text;
    };
    say('assessments', c.summary_assessments);
    say('slots', c.summary_slots);
    say('undated', c.summary_undated);
    const undated = document.querySelector('[data-summary="undated"]');
    if (undated) undated.classList.toggle('is-flagged', c.assessments_undated > 0);
    const total = document.querySelector('[data-tile="total"]');
    if (total) {
        total.textContent = `${String(c.total_weight).replace(/\.0$/, '')}%`;
        total.className = `c-weight mono completeness-${c.total_class}`;
    }
}

/**
 * Badge and note of the edited row: "Needs a date" and "no calendar event until you add a date"
 * go away once a date exists, and come back when it is cleared (D19).
 */
function applyRowState(fieldElement, row) {
    if (!row) return;
    const item = fieldElement.closest('.assessment-item');
    if (!item) return;
    const flagCell = item.querySelector('.c-flag');
    let badge = item.querySelector('.badge-needs-date');
    const missing = !row.has_date && !row.is_bonus;
    if (missing && !badge && flagCell) {
        badge = document.createElement('span');
        badge.className = 'badge badge-warning badge-needs-date';
        badge.textContent = 'Needs a date';
        flagCell.insertBefore(badge, flagCell.firstChild);
    } else if (!missing && badge) {
        badge.remove();
    }
    const flagged = (row.needs_review || missing || !row.weight) && !row.is_bonus;
    item.classList.toggle('needs-review', flagged);

    const index = item.getAttribute('data-assessment-index');
    let noteRow = item.nextElementSibling;
    if (!noteRow || !noteRow.classList.contains('assessment-note')) noteRow = null;
    if (missing) {
        if (!noteRow) {
            noteRow = document.createElement('tr');
            noteRow.className = 'assessment-note';
            noteRow.setAttribute('data-note-for', index);
            noteRow.innerHTML = '<td class="c-ordinal" aria-hidden="true"></td>' +
                                '<td colspan="4"><p class="date-reason"></p></td>';
            item.parentNode.insertBefore(noteRow, item.nextSibling);
        }
        noteRow.classList.toggle('needs-review', flagged);
        noteRow.querySelector('.date-reason').textContent =
            (row.date_note || 'No due date') + ' — no calendar event until you add a date.';
    } else if (noteRow && /no calendar event until you add a date\.$/.test(noteRow.textContent.trim())) {
        // Only retract the missing-date note. The same row also carries the
        // "recurring" and "rule" explanations, which survive an edit.
        noteRow.remove();
    }
}

/**
 * Initialize manual section adders (for lecture and lab sections)
 * Handles the "Add Section Manually" buttons
 */
function initManualSectionAdders() {
    // Handle "Add Lab Section Manually" button
    const addLabBtn = document.getElementById('add-lab-section');
    if (addLabBtn) {
        addLabBtn.addEventListener('click', function() {
            showManualSectionForm('lab');
        });
    }
    
    // Handle "Add Lecture Section Manually" button
    const addLectureBtn = document.getElementById('add-lecture-section');
    if (addLectureBtn) {
        addLectureBtn.addEventListener('click', function() {
            showManualSectionForm('lecture');
        });
    }
}

/**
 * Show form modal for adding a manual section
 * 
 * @param {string} sectionType - 'lab' or 'lecture'
 */
function showManualSectionForm(sectionType) {
    // Create modal overlay using existing modal class
    const modal = document.createElement('div');
    modal.className = 'modal';
    
    // Create modal content using existing modal-content class
    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content';
    
    const sectionName = sectionType === 'lab' ? 'Lab' : 'Lecture';
    
    modalContent.innerHTML = `
        <button type="button" class="close-modal" aria-label="Close">&times;</button>
        <h3 id="manual-section-title">
            Add ${sectionName} Section Manually
        </h3>
        <form id="manual-section-form">
            <div class="form-group">
                <label for="section-days">Days of Week:</label>
                <div class="days-checkbox-group">
                    <label class="checkbox-label">
                        <input type="checkbox" name="day" value="0"> Mon
                    </label>
                    <label class="checkbox-label">
                        <input type="checkbox" name="day" value="1"> Tue
                    </label>
                    <label class="checkbox-label">
                        <input type="checkbox" name="day" value="2"> Wed
                    </label>
                    <label class="checkbox-label">
                        <input type="checkbox" name="day" value="3"> Thu
                    </label>
                    <label class="checkbox-label">
                        <input type="checkbox" name="day" value="4"> Fri
                    </label>
                    <label class="checkbox-label">
                        <input type="checkbox" name="day" value="5"> Sat
                    </label>
                    <label class="checkbox-label">
                        <input type="checkbox" name="day" value="6"> Sun
                    </label>
                </div>
                <small>Select one or more days when this ${sectionName.toLowerCase()} meets</small>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label for="section-start-time">Start Time:</label>
                    <input type="time" id="section-start-time" name="start_time" required class="form-control">
                </div>
                <div class="form-group">
                    <label for="section-end-time">End Time:</label>
                    <input type="time" id="section-end-time" name="end_time" required class="form-control">
                </div>
            </div>
            
            <div class="form-group">
                <label for="section-location">Location (optional):</label>
                <input type="text" id="section-location" name="location" placeholder="e.g., UC 202" class="form-control">
            </div>
            
            <div class="form-actions">
                <button type="button" class="btn btn-secondary btn-cancel-modal">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Section</button>
            </div>
        </form>
    `;
    
    modal.appendChild(modalContent);
    document.body.appendChild(modal);
    
    // Initialize Lucide icons in modal
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
    
    // Handle form submission
    const form = modalContent.querySelector('#manual-section-form');
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get selected days
        const dayCheckboxes = form.querySelectorAll('input[name="day"]:checked');
        if (dayCheckboxes.length === 0) {
            showReviewNotice('Please select at least one day of the week.');
            return;
        }
        
        const days = Array.from(dayCheckboxes).map(cb => parseInt(cb.value)).sort();
        const startTime = form.querySelector('#section-start-time').value;
        const endTime = form.querySelector('#section-end-time').value;
        const location = form.querySelector('#section-location').value || null;
        
        if (!startTime || !endTime) {
            showReviewNotice('Please enter both start and end times.');
            return;
        }
        
        // Add the section to the page
        addManualSection(sectionType, days, startTime, endTime, location);

        // Close modal
        closeManualSectionModal();
    });
    
    // Handle close button
    const closeBtn = modalContent.querySelector('.close-modal');
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            closeManualSectionModal();
        });
    }
    
    // Handle cancel button
    const cancelBtn = modalContent.querySelector('.btn-cancel-modal');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            closeManualSectionModal();
        });
    }

    // Close on overlay click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeManualSectionModal();
        }
    });

    // Escape closes, Tab stays inside, focus returns to the opener — the same
    // contract the Add-assessment dialog already honours.
    modalContent.setAttribute('role', 'dialog');
    modalContent.setAttribute('aria-modal', 'true');
    modalContent.setAttribute('aria-labelledby', 'manual-section-title');
    const opener = document.activeElement;
    const focusables = modalContent.querySelectorAll('input, select, textarea, button, [href]');
    if (focusables.length) focusables[0].focus();

    function onKeydown(e) {
        if (e.key === 'Escape') {
            e.preventDefault();
            closeManualSectionModal();
            return;
        }
        if (e.key !== 'Tab' || focusables.length === 0) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
        }
    }
    document.addEventListener('keydown', onKeydown);

    function closeManualSectionModal() {
        document.removeEventListener('keydown', onKeydown);
        if (modal.parentNode) document.body.removeChild(modal);
        if (opener && typeof opener.focus === 'function') opener.focus();
    }
}

/**
 * Add a manually created section to the page
 * 
 * @param {string} sectionType - 'lab' or 'lecture'
 * @param {Array<number>} days - Array of day numbers (0=Mon, 6=Sun)
 * @param {string} startTime - Start time (HH:MM format)
 * @param {string} endTime - End time (HH:MM format)
 * @param {string|null} location - Location (optional)
 */
function addManualSection(sectionType, days, startTime, endTime, location) {
    const sectionName = sectionType === 'lab' ? 'Lab' : 'Lecture';
    const sectionId = sectionType === 'lab' ? 'lab_section' : 'lecture_section';
    
    const slotRow = document.querySelector(`[data-slot="${sectionType}"]`);
    let sectionContainer = slotRow ? slotRow.querySelector('.c-section') : null;
    if (!sectionContainer) {
        const addButton = document.getElementById(`add-${sectionType}-section`);
        if (addButton) sectionContainer = addButton.parentNode;
    }
    
    if (!sectionContainer) {
        console.error(`Could not find ${sectionName} section container`);
        return;
    }
    
    // Day names for display
    const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const dayDisplay = days.map(d => dayNames[d]).join('/');
    
    // Format time for display (convert 24h to 12h)
    const formatTime = (timeStr) => {
        const [hours, minutes] = timeStr.split(':');
        const hour = parseInt(hours);
        const ampm = hour >= 12 ? 'PM' : 'AM';
        const displayHour = hour % 12 || 12;
        return `${displayHour}:${minutes} ${ampm}`;
    };
    
    // Create the select dropdown if it doesn't exist
    let selectElement = document.getElementById(sectionId);
    if (!selectElement) {
        // Remove the "no data" message and button
        const noDataMsg = sectionContainer.querySelector('.no-data');
        const addButton = sectionContainer.querySelector(`#add-${sectionType}-section`);
        const hiddenInput = sectionContainer.querySelector('input[type="hidden"][name="' + sectionId + '"]');
        
        if (noDataMsg) {
            noDataMsg.remove();
        }
        if (addButton) {
            addButton.remove();
        }
        if (hiddenInput) {
            hiddenInput.remove();
        }
        
        // Build the select inside the slot row's "Your section" cell
        const label = document.createElement('label');
        label.className = 'sr-only';
        label.setAttribute('for', sectionId);
        label.textContent = `Select your ${sectionName.toLowerCase()} section`;

        const select = document.createElement('select');
        select.name = sectionId;
        select.id = sectionId;
        select.className = 'control';
        if (sectionType === 'lecture') select.required = true;
        const placeholder = document.createElement('option');
        placeholder.value = sectionType === 'lab' ? 'none' : '';
        placeholder.textContent = sectionType === 'lab' ? 'No lab section' : 'Select a section';
        select.appendChild(placeholder);

        sectionContainer.insertBefore(label, sectionContainer.firstChild);
        sectionContainer.insertBefore(select, label.nextSibling);
        selectElement = select;

        const addMoreButton = document.createElement('button');
        addMoreButton.type = 'button';
        addMoreButton.className = 'btn btn-quiet btn-sm';
        addMoreButton.id = `add-${sectionType}-section`;
        addMoreButton.textContent = 'Add Section';
        addMoreButton.addEventListener('click', function() {
            showManualSectionForm(sectionType);
        });
        sectionContainer.appendChild(addMoreButton);

    }
    
    // Store manual sections in a hidden input for form submission
    let manualSectionsInput = document.getElementById(`manual_${sectionType}_sections`);
    if (!manualSectionsInput) {
        manualSectionsInput = document.createElement('input');
        manualSectionsInput.type = 'hidden';
        manualSectionsInput.id = `manual_${sectionType}_sections`;
        manualSectionsInput.name = `manual_${sectionType}_sections`;
        sectionContainer.appendChild(manualSectionsInput);
    }
    
    // Get existing manual sections
    const manualSections = [];
    const allOptions = selectElement.querySelectorAll('option[data-manual="true"]');
    allOptions.forEach(opt => {
        manualSections.push({
            days: JSON.parse(opt.getAttribute('data-days')),
            start_time: opt.getAttribute('data-start-time'),
            end_time: opt.getAttribute('data-end-time'),
            location: opt.getAttribute('data-location')
        });
    });
    
    // Add the new section
    manualSections.push({
        days: days,
        start_time: startTime,
        end_time: endTime,
        location: location || ''
    });
    
    // Update hidden input
    manualSectionsInput.value = JSON.stringify(manualSections);
    
    // Add option to select - use index as value for proper matching
    const option = document.createElement('option');
    const manualIndex = manualSections.length - 1; // Index in the manual sections array
    option.value = `manual_${manualIndex}`;
    option.textContent = `${dayDisplay} ${formatTime(startTime)}-${formatTime(endTime)}${location ? ` (${location})` : ''}`;
    option.setAttribute('data-days', JSON.stringify(days));
    option.setAttribute('data-start-time', startTime);
    option.setAttribute('data-end-time', endTime);
    option.setAttribute('data-location', location || '');
    option.setAttribute('data-manual', 'true');
    option.setAttribute('data-manual-index', manualIndex);

    selectElement.appendChild(option);

    // Select the newly added option
    option.selected = true;
}

// Initialize assessment add/remove functionality
function initAssessmentAddRemove() {
    // Add Assessment button
    const addBtn = document.getElementById('add-assessment-btn');
    if (addBtn) {
        addBtn.addEventListener('click', function() {
            showAddAssessmentModal();
        });
    }
    
    // Remove Assessment buttons
    const removeButtons = document.querySelectorAll('.btn-remove-assessment');
    removeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const index = parseInt(this.getAttribute('data-assessment-index'));
            removeAssessment(index);
        });
    });
    
    // Modal close handlers
    const modal = document.getElementById('add-assessment-modal');
    if (modal) {
        const closeBtn = modal.querySelector('.close-modal');
        const cancelBtn = modal.querySelector('.cancel-add-assessment');
        
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                closeAddAssessmentModal();
            });
        }
        
        if (cancelBtn) {
            cancelBtn.addEventListener('click', function() {
                closeAddAssessmentModal();
            });
        }
        
        // Close when clicking outside modal
        window.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeAddAssessmentModal();
            }
        });
    }
    
    // Form submission - prevent default and stop propagation
    const form = document.getElementById('add-assessment-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            e.stopPropagation();
            addAssessment();
            return false;
        });
    }
}

let _modalOpener = null;
let _modalKeyHandler = null;

/**
 * Open the "Add assessment" dialog: focus moves in, Escape closes, Tab stays
 * inside, and focus returns to whatever opened it.
 */
function openAddAssessmentModal(modal) {
    _modalOpener = document.activeElement;
    modal.hidden = false;
    const focusables = modal.querySelectorAll('input, select, textarea, button, [href]');
    if (focusables.length) focusables[0].focus();
    _modalKeyHandler = function (e) {
        if (e.key === 'Escape') {
            e.preventDefault();
            closeAddAssessmentModal();
            return;
        }
        if (e.key !== 'Tab' || focusables.length === 0) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
        }
    };
    document.addEventListener('keydown', _modalKeyHandler);
}

function closeAddAssessmentModal() {
    const modal = document.getElementById('add-assessment-modal');
    if (modal) modal.hidden = true;
    if (_modalKeyHandler) {
        document.removeEventListener('keydown', _modalKeyHandler);
        _modalKeyHandler = null;
    }
    if (_modalOpener && typeof _modalOpener.focus === 'function') _modalOpener.focus();
    _modalOpener = null;
}

function showAddAssessmentModal() {
    const modal = document.getElementById('add-assessment-modal');
    if (modal) {
        openAddAssessmentModal(modal);
        // Reset form
        const form = document.getElementById('add-assessment-form');
        if (form) {
            form.reset();
        }
    }
}

function addAssessment() {
    const form = document.getElementById('add-assessment-form');
    if (!form) return;
    
    const formData = new FormData(form);
    const data = {
        title: formData.get('title'),
        type: formData.get('type'),
        weight_percent: formData.get('weight_percent') || null,
        due_datetime: formData.get('due_datetime') || null,
        due_rule: formData.get('due_rule') || null,
        rule_anchor: formData.get('rule_anchor') || null,
        confidence: 0.8,  // Default confidence for manually added assessments
        source_evidence: 'Manual entry',  // Default source for manually added assessments
        needs_review: false  // Default to false for manually added assessments
    };
    
    // Remove null/empty values (but keep confidence and source_evidence)
    Object.keys(data).forEach(key => {
        if (key !== 'confidence' && key !== 'source_evidence' && (data[key] === null || data[key] === '')) {
            delete data[key];
        }
    });
    
    fetch('/api/add-assessment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            // Close modal
            closeAddAssessmentModal();

            // Reload page to show new assessment
            window.location.reload();
        } else {
            showReviewNotice('Could not add the assessment: ' + (result.error || 'unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showReviewNotice('Could not add the assessment: ' + error.message);
    });
}

function removeAssessment(index) {
    if (!confirm('Are you sure you want to remove this assessment?')) {
        return;
    }
    
    fetch('/api/remove-assessment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            assessment_index: index
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            // Reload page to reflect changes
            window.location.reload();
        } else {
            showReviewNotice('Could not remove the assessment: ' + (result.error || 'unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showReviewNotice('Could not remove the assessment: ' + error.message);
    });
}


/* ==========================================================================
   Registrar's ledger — motion, icons, and the download confirmation.

   Motion policy (MengTo `animation-systems`): every beat below exists to
   explain hierarchy, confirm an action, guide attention or keep continuity;
   anything that served none of those was deleted with the old hero. One
   easing family lives in style.css. `prefers-reduced-motion: reduce` lands on
   the complete final state, never a shortened animation, so each gate here
   marks its targets done rather than animating them faster.
   ========================================================================== */

const REDUCED_MOTION = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : { matches: false, addEventListener: function () {} };

/**
 * Lucide draws after the deferred CDN script has run, which is later than this
 * file. Icons are decoration; a failure must never take the page with it.
 */
function drawIcons() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
        try { window.lucide.createIcons(); } catch (e) { /* decoration only */ }
    }
}

/**
 * M1/M2/M3 — the sheet settles top-down so the reading order is obvious, and
 * the drop screen's headline rises word-by-word through a mask.
 *
 * `animation-on-scroll` for the observer, `masked-reveal` for the headline
 * (implemented in CSS rather than GSAP: one headline does not justify a
 * render-blocking animation library on a cold-starting Python function).
 */
function initMotion() {
    const revealTargets = Array.prototype.slice.call(document.querySelectorAll('[data-reveal]'));
    const headlines = Array.prototype.slice.call(document.querySelectorAll('[data-masked-reveal]'));

    // Reduced motion lands on the complete final state, never a faster one.
    if (REDUCED_MOTION.matches || !('IntersectionObserver' in window)) {
        revealTargets.forEach(function (el) { el.classList.add('is-in'); });
        headlines.forEach(function (el) { el.classList.add('is-in'); });
        return;
    }

    document.documentElement.classList.add('motion-ready');
    headlines.forEach(splitMaskedReveal);

    let index = 0;
    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            entry.target.classList.add('is-in');
            observer.unobserve(entry.target);
        });
    }, { threshold: 0.2, rootMargin: '0px 0px -10% 0px' });

    revealTargets.forEach(function (el) {
        // Above the fold the stagger reads as one settle; below it each
        // section arrives on its own, so the delay resets.
        el.style.setProperty('--reveal-i', String(index < 4 ? index : 0));
        index += 1;
        observer.observe(el);
    });
    headlines.forEach(function (el) { observer.observe(el); });

    window.addEventListener('pagehide', function () { observer.disconnect(); }, { once: true });
    window.addEventListener('pageshow', function (e) {
        if (!e.persisted) return;   // bfcache restore: DOMContentLoaded will not fire again
        revealTargets.concat(headlines).forEach(function (el) { el.classList.add('is-in'); });
    });

    // Turning reduce on mid-session must land on the finished state too.
    if (typeof REDUCED_MOTION.addEventListener === 'function') {
        REDUCED_MOTION.addEventListener('change', function (e) {
            if (!e.matches) return;
            observer.disconnect();
            document.documentElement.classList.remove('motion-ready');
            revealTargets.concat(headlines).forEach(function (el) { el.classList.add('is-in'); });
        });
    }
}

/**
 * Wrap each word in an overflow mask so it can rise into place. The un-split
 * text stays available to assistive technology via aria-label.
 */
function splitMaskedReveal(element) {
    if (element.dataset.maskedRevealReady === 'true') return;
    const text = element.textContent.trim();
    element.setAttribute('aria-label', text);
    const words = text.split(/(\s+)/);
    let i = 0;
    element.innerHTML = words.map(function (part) {
        if (!part.trim()) return part;
        const html = '<span class="word-mask" aria-hidden="true">' +
                     '<span class="word" style="--i:' + i + '">' + escapeHtml(part) + '</span></span>';
        i += 1;
        return html;
    }).join('');
    element.dataset.maskedRevealReady = 'true';
    element.classList.add('is-split');
}

/**
 * The header earns its hairline lift only once there is content above it.
 */
function initHeaderShadow() {
    const head = document.querySelector('.sheet-head');
    if (!head) return;
    const update = function () {
        head.classList.toggle('is-scrolled', window.scrollY > 4);
    };
    update();
    window.addEventListener('scroll', update, { passive: true });
}

/**
 * M12 — screen 3. The server still streams text/calendar from POST /review;
 * this only reads the file back through fetch so the page can say what landed
 * (file name, event count, range). Any failure hands the submit straight back
 * to the browser, so the no-JS path is exactly what it was before.
 */
function initDownloadConfirm() {
    const form = document.getElementById('review-form');
    const done = document.getElementById('download-done');
    if (!form || !done || typeof window.fetch !== 'function' || typeof window.FormData !== 'function') return;

    const button = document.getElementById('generate-calendar-btn');
    const label = button ? button.textContent : '';   // captured once, before anything rewrites it
    let passthrough = false;
    let inFlight = false;

    const reset = function () {
        inFlight = false;
        if (button) { button.disabled = false; button.textContent = label; }
    };

    form.addEventListener('submit', function (e) {
        if (passthrough) return;
        if (document.querySelector('.editable-field.editing')) return;  // the save handler owns this click
        e.preventDefault();

        // A disabled button is not a guard: Enter inside a <select> submits the
        // form implicitly, and submitReview() can race a click. Two concurrent
        // POST /review means two 60 s function invocations and two saved files.
        if (inFlight) return;
        inFlight = true;
        if (button) { button.disabled = true; button.textContent = 'Generating…'; }

        let saved = false;
        const fallback = function () {
            if (saved) { reset(); return; }   // the file already landed; never re-POST
            passthrough = true;
            reset();
            form.submit();
        };

        fetch(form.action, { method: 'POST', body: new FormData(form), credentials: 'same-origin' })
            .then(function (response) {
                if (!response.ok) throw new Error('HTTP ' + response.status);
                const type = response.headers.get('Content-Type') || '';
                if (type.indexOf('text/calendar') === -1) throw new Error('not a calendar');
                const filename = filenameFrom(response.headers.get('Content-Disposition'));
                const events = response.headers.get('X-Plato-Events') || '';
                const range = response.headers.get('X-Plato-Range') || '';
                return response.blob().then(function (blob) {
                    saveBlob(blob, filename);
                    saved = true;
                    showDownloadConfirm(done, filename, events, range);
                    reset();
                });
            })
            .catch(fallback);
    });
}

function filenameFrom(disposition) {
    const match = /filename="?([^";]+)"?/.exec(disposition || '');
    return match ? match[1] : 'course-calendar.ics';
}

function saveBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
}

function showDownloadConfirm(done, filename, events, range) {
    const set = function (key, text) {
        const el = done.querySelector('[data-confirm="' + key + '"]');
        if (el) el.textContent = text;
    };
    // Unhide BEFORE filling: a change inside a still-hidden aria-live region is
    // generally not announced, so the confirmation was silent to a screen reader.
    done.hidden = false;
    requestAnimationFrame(function () {
        set('file', filename);
        set('events', events ? (events + (events === '1' ? ' event' : ' events')) : 'unknown');
        set('range', range ? range.replace(' - ', ' \u2013 ') : 'no dated events');
        done.scrollIntoView({ behavior: REDUCED_MOTION.matches ? 'auto' : 'smooth', block: 'nearest' });
    });
}
