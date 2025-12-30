/**
 * Client-side JavaScript for Course Outline to iCalendar Converter
 * 
 * This file contains JavaScript functions for enhancing the user experience
 * in the web interface. It handles form interactions, validation, and
 * dynamic content updates.
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize form enhancements
    initFileUpload();
    initFormValidation();
    initDynamicForms();
    initEditableFields();
    
    // Re-enable form submission for the generate calendar button
    const generateBtn = document.getElementById('generate-calendar-btn');
    const reviewForm = document.getElementById('review-form');
    if (generateBtn && reviewForm) {
        generateBtn.addEventListener('click', function(e) {
            // Allow form submission when clicking generate button
            reviewForm.onsubmit = null;
            reviewForm.submit();
        });
    }
});

/**
 * Initialize file upload enhancements
 * Shows file name when file is selected
 */
function initFileUpload() {
    const fileInput = document.getElementById('pdf_file');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const fileName = e.target.files[0]?.name;
            if (fileName) {
                // You could add a label or display element to show the selected file name
                console.log('File selected:', fileName);
            }
        });
    }
}

/**
 * Initialize form validation
 * Provides client-side validation feedback
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
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
                alert('Please fill in all required fields.');
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
        alert('Please upload a PDF file.');
        return false;
    }
    
    // Check file size (16MB max)
    const maxSize = 16 * 1024 * 1024; // 16MB in bytes
    if (file.size > maxSize) {
        alert('File is too large. Maximum size is 16MB.');
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
    console.log('initEditableFields called');
    
    // First, find all editable fields and add direct click listeners
    const editableFields = document.querySelectorAll('.editable-field');
    console.log('Found', editableFields.length, 'editable fields');
    
    editableFields.forEach((field, index) => {
        console.log(`Setting up field ${index}:`, field, 'classes:', field.className);
        
        // Make sure cursor shows it's clickable
        field.style.cursor = 'pointer';
        field.style.userSelect = 'none';
        
        // Add direct click listener - use both capture and bubble phases
        field.addEventListener('click', function(e) {
            console.log('Direct click on field:', this, 'Event:', e);
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            
            if (!this.classList.contains('editing')) {
                console.log('Starting edit for:', this.getAttribute('data-field-type'));
                startEditing(this);
            }
            return false;
        }, false); // Use bubble phase first
        
        // Also add capture phase listener
        field.addEventListener('click', function(e) {
            console.log('Capture phase click on field:', this);
            if (!this.classList.contains('editing')) {
                e.preventDefault();
                e.stopPropagation();
            }
        }, true); // Use capture phase
        
        // Prevent form submission when clicking
        field.addEventListener('mousedown', function(e) {
            e.stopPropagation();
        }, true);
        
        // Also prevent on the field itself
        field.onclick = function(e) {
            console.log('onclick handler triggered');
            e.preventDefault();
            e.stopPropagation();
            if (!this.classList.contains('editing')) {
                startEditing(this);
            }
            return false;
        };
    });
    
    // Also use event delegation as backup
    document.body.addEventListener('click', function(e) {
        const editableField = e.target.closest('.editable-field');
        if (editableField && !editableField.classList.contains('editing')) {
            console.log('Event delegation caught click on:', editableField);
            e.preventDefault();
            e.stopPropagation();
            startEditing(editableField);
            return false;
        }
    }, true);
}

/**
 * Start editing a field
 * Replaces the field display with an input form
 * 
 * @param {HTMLElement} fieldElement - The field element to edit
 */
function startEditing(fieldElement) {
    console.log('startEditing called with:', fieldElement);
    
    if (!fieldElement) {
        console.error('startEditing: fieldElement is null or undefined');
        return;
    }
    
    // Prevent any form submission
    const form = fieldElement.closest('form');
    if (form) {
        const originalSubmit = form.onsubmit;
        form.onsubmit = function(e) {
            e.preventDefault();
            return false;
        };
    }
    
    const fieldType = fieldElement.getAttribute('data-field-type');
    const currentValue = fieldElement.getAttribute('data-current-value') || '';
    const assessmentIndex = fieldElement.getAttribute('data-assessment-index');
    
    console.log('Field details:', { fieldType, currentValue, assessmentIndex });
    
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
    } else {
        placeholder = 'Enter value';
    }
    
    // Create input form
    const form = document.createElement('form');
    form.className = 'inline-edit-form';
    form.innerHTML = `
        <input type="${inputType}" 
               class="inline-edit-input" 
               value="${inputValue}" 
               placeholder="${placeholder}"
               ${inputType === 'number' ? 'min="0" max="100" step="0.1"' : ''}
               autofocus>
        <div class="inline-edit-actions">
            <button type="submit" class="btn-save">Save</button>
            <button type="button" class="btn-cancel">Cancel</button>
        </div>
    `;
    
    // Store original content
    const originalContent = fieldElement.innerHTML;
    const originalDisplay = fieldElement.style.display;
    
    // Replace field with form
    fieldElement.innerHTML = '';
    fieldElement.appendChild(form);
    fieldElement.classList.add('editing');
    
    const input = form.querySelector('.inline-edit-input');
    input.focus();
    input.select();
    
    // Handle form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const newValue = input.value.trim();
        saveField(fieldElement, fieldType, newValue, assessmentIndex, originalContent);
    });
    
    // Handle cancel
    form.querySelector('.btn-cancel').addEventListener('click', function() {
        fieldElement.innerHTML = originalContent;
        fieldElement.classList.remove('editing');
    });
    
    // Handle escape key
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            fieldElement.innerHTML = originalContent;
            fieldElement.classList.remove('editing');
        }
    });
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
            // Update display with new value
            updateFieldDisplay(fieldElement, fieldType, newValue);
            // Show success message briefly
            fieldElement.classList.add('saved');
            setTimeout(() => {
                fieldElement.classList.remove('saved');
            }, 2000);
        } else {
            // Show error and restore original
            alert('Error: ' + (data.error || 'Failed to save'));
            fieldElement.innerHTML = originalContent;
            fieldElement.classList.remove('editing');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error saving field. Please try again.');
        fieldElement.innerHTML = originalContent;
        fieldElement.classList.remove('editing');
    });
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
            // Format datetime for display
            const dt = new Date(newValue);
            displayValue = dt.toLocaleString('en-US', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } else {
            displayValue = 'Due date not found';
        }
    } else if (fieldType === 'assessment_weight') {
        if (newValue) {
            displayValue = newValue + '%';
        } else {
            displayValue = 'Not set';
        }
    }
    
    // Update the field
    const isMissing = !newValue || newValue === '' || displayValue === 'Not found' || displayValue === 'Not set';
    fieldElement.innerHTML = displayValue;
    fieldElement.setAttribute('data-current-value', newValue || '');
    
    if (isMissing) {
        fieldElement.classList.add('missing-field');
    } else {
        fieldElement.classList.remove('missing-field');
    }
    
<｜tool▁sep｜>new_string
    // Update completeness metrics without full page reload
    // The field display has been updated, so we're done
    // User can continue editing other fields
}

