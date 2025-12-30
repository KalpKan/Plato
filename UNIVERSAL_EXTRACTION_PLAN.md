# Universal Assessment Extraction Plan

## Executive Summary

After analyzing 4 reference PDFs (PHYS 3120, PHYS 3140, PP3000E, BIOCHEM 3381A), we identified two distinct assessment formats:
1. **Table-based format** (3 PDFs): Structured tables with columns
2. **Text-based format** (1 PDF): Numbered/bulleted lists in prose

This plan provides a unified extraction strategy that handles both formats robustly.

---

## PDF Format Analysis

### Format 1: Table-Based (PHYS 3120, PHYS 3140, PP3000E)

**Common Characteristics:**
- Assessment section header: "Assessment and Evaluation" or "8. Assessment and Evaluation"
- Table header row contains: "Assessment", "Format"/"Weighting"/"Weight", "Due Date"/"Date", "Flexibility"
- Column structure varies:
  - PHYS 3120/3140: 15 columns (sparse, data in columns 0, 3, 6, 9, 12)
  - PP3000E: 5 columns (dense, all columns used)
- Multi-line cell content (newlines within cells)
- Multi-row assessments (assessment name split across rows)
- Some assessments have "Completion#" instead of percentage

**Table Structure:**
```
Assessment | Format | Weighting | Due Date | Flexibility
-----------|--------|-----------|----------|------------
Quiz 1     | MCQ    | 5%        | Oct 1    | ...
```

### Format 2: Text-Based (BIOCHEM 3381A)

**Characteristics:**
- Section header: "7. Evaluation" or "Evaluation"
- Numbered/bulleted list format:
  - "I. Quizzes (15%) ..."
  - "II. Assignment 1 (5%) Due Monday September 29"
  - "III. Assignment 2 (20%) Due Wednesday October 13"
- Weights and dates embedded in prose
- Sub-items with nested weights (e.g., "Inquiry (40%)" with sub-items)
- No structured table

**Text Structure:**
```
I. Quizzes (15%) Each Friday...
II. Assignment 1 (5%) Due Monday September 29
III. Assignment 2 (20%) Due Wednesday October 13
```

---

## Universal Extraction Strategy

### Phase 1: Section Detection (Universal)

**Goal:** Find the assessment/evaluation section regardless of format.

**Approach:**
1. Search for section headers using multiple patterns:
   - `\d+\.\s*Assessment\s+(?:and\s+)?Evaluation`
   - `\d+\.\s*Evaluation`
   - `Assessment\s+(?:and\s+)?Evaluation`
   - `Evaluation\s+(?:Breakdown|Policy)?`
   - `Grading\s+(?:Scheme|Breakdown)?`
2. Extract section boundaries:
   - Find next numbered section (e.g., "8.", "9.")
   - Or find major headings (e.g., "Course", "Instructor", "Policies")
   - Extract 5000-10000 characters after header

**Implementation:**
```python
def find_assessment_section(text: str) -> Optional[str]:
    patterns = [
        r'\d+\.\s*Assessment\s+(?:and\s+)?Evaluation[^\n]*(?:\n[^\n]*){0,1000}',
        r'\d+\.\s*Evaluation[^\n]*(?:\n[^\n]*){0,1000}',
        r'Assessment\s+(?:and\s+)?Evaluation[^\n]*(?:\n[^\n]*){0,1000}',
    ]
    # Try each pattern, return first match
    # Find section end boundary
    # Return section text
```

---

### Phase 2: Format Detection (Universal)

**Goal:** Determine if section uses table-based or text-based format.

**Approach:**
1. Try table extraction first (using pdfplumber):
   - Extract all tables from pages containing assessment section
   - Look for table with header row containing: "Assessment", "Weight"/"Weighting", "Due"/"Date"
2. If table found → **Table-based extraction**
3. If no table found → **Text-based extraction**

**Implementation:**
```python
def detect_format(pdf_path: Path, section_pages: List[int]) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in section_pages:
            tables = pdf.pages[page_num-1].extract_tables()
            for table in tables:
                if is_assessment_table(table):
                    return "table"
    return "text"
```

---

### Phase 3A: Table-Based Extraction

**Goal:** Extract assessments from structured tables.

#### Step 1: Identify Assessment Table

**Criteria:**
- Header row contains "Assessment" (or similar)
- Header row contains "Weight"/"Weighting" (or percentage symbol)
- Header row contains "Due"/"Date" (or date-related keywords)
- Table has at least 2 data rows

**Implementation:**
```python
def is_assessment_table(table: List[List]) -> bool:
    if not table or len(table) < 2:
        return False
    
    header = ' '.join([str(cell) for cell in table[0] if cell])
    has_assessment = 'assessment' in header.lower()
    has_weight = any(w in header.lower() for w in ['weight', 'weighting', '%'])
    has_date = any(d in header.lower() for d in ['due', 'date', 'deadline'])
    
    return has_assessment and (has_weight or has_date)
```

#### Step 2: Map Columns

**Goal:** Identify which columns contain assessment name, weight, date, format.

**Approach:**
- Parse header row to find column indices
- Handle variations:
  - "Assessment" → name column
  - "Format" → format column (optional)
  - "Weight"/"Weighting" → weight column
  - "Due Date"/"Date" → date column
  - "Flexibility" → flexibility column (optional)

**Implementation:**
```python
def map_table_columns(header_row: List[str]) -> Dict[str, int]:
    mapping = {}
    for idx, cell in enumerate(header_row):
        cell_lower = str(cell).lower() if cell else ""
        if 'assessment' in cell_lower:
            mapping['name'] = idx
        elif 'weight' in cell_lower or '%' in cell_lower:
            mapping['weight'] = idx
        elif 'due' in cell_lower or 'date' in cell_lower:
            mapping['date'] = idx
        elif 'format' in cell_lower:
            mapping['format'] = idx
    return mapping
```

#### Step 3: Extract Rows

**Goal:** Process each data row and extract assessment information.

**Challenges:**
1. **Multi-row assessments**: Some assessments span multiple rows
   - Detection: If row has empty/None in name column but has weight/date → continuation
   - Solution: Merge with previous row
   
2. **Multi-line cell content**: Cells contain newlines
   - Solution: Join with spaces, preserve structure
   
3. **Completion-based assessments**: "Completion#" instead of percentage
   - Solution: Mark as completion-based, weight = 0 or None, flag for review

4. **Summary rows**: "Total Rotation 1", "COURSE TOTAL"
   - Detection: Name contains "Total"/"TOTAL", or weight is sum-like
   - Solution: Skip these rows

**Implementation:**
```python
def extract_from_table(table: List[List], column_map: Dict[str, int]) -> List[AssessmentTask]:
    assessments = []
    current_assessment = None
    
    for row_idx, row in enumerate(table[1:], 1):  # Skip header
        # Check if summary row
        name_cell = row[column_map.get('name', 0)] if column_map.get('name') else None
        if name_cell and ('total' in str(name_cell).lower() or 'course total' in str(name_cell).lower()):
            continue
        
        # Extract name
        name = extract_name(row, column_map)
        if not name:
            # Might be continuation row - merge with previous
            if current_assessment:
                current_assessment = merge_row(current_assessment, row, column_map)
            continue
        
        # Extract weight
        weight = extract_weight(row, column_map)
        if weight is None and 'completion' in str(row[column_map.get('weight', 0)]).lower():
            # Completion-based assessment
            weight = None  # Mark for review
        
        # Extract date
        due_date = extract_date(row, column_map)
        
        # Create assessment
        assessment = AssessmentTask(
            title=name,
            weight_percent=weight,
            due_datetime=due_date,
            # ... other fields
        )
        assessments.append(assessment)
        current_assessment = assessment
    
    return assessments
```

#### Step 4: Handle Special Cases

**Multi-row merging:**
```python
def merge_row(assessment: AssessmentTask, row: List, column_map: Dict) -> AssessmentTask:
    # Append continuation text to name
    name_cell = row[column_map.get('name', 0)]
    if name_cell:
        assessment.title += " " + str(name_cell)
    
    # Update date if found in continuation
    date_cell = row[column_map.get('date', 0)]
    if date_cell and not assessment.due_datetime:
        assessment.due_datetime = parse_date(date_cell)
    
    return assessment
```

**Completion-based detection:**
```python
def extract_weight(row: List, column_map: Dict) -> Optional[float]:
    weight_cell = row[column_map.get('weight', 0)]
    if not weight_cell:
        return None
    
    weight_str = str(weight_cell).strip()
    
    # Check for completion-based
    if 'completion' in weight_str.lower() or weight_str.endswith('#'):
        return None  # Mark for review
    
    # Extract percentage
    match = re.search(r'(\d+\.?\d*)%', weight_str)
    if match:
        return float(match.group(1))
    
    return None
```

---

### Phase 3B: Text-Based Extraction

**Goal:** Extract assessments from prose/numbered lists.

#### Step 1: Identify Assessment Items

**Patterns:**
- Roman numerals: `I\.`, `II\.`, `III\.`, etc.
- Arabic numerals: `\d+\.`
- Bullets: `•`, `-`, `*`
- Followed by assessment name and weight: `(15%)`, `(5%)`

**Implementation:**
```python
def find_assessment_items(text: str) -> List[Dict]:
    items = []
    
    # Pattern: Roman/Arabic numeral, name, weight in parentheses, optional date
    pattern = r'(?:^|\n)([IVX]+\.|\d+\.|•|-|\*)\s*([^(]+?)\s*\((\d+\.?\d*)%\)(?:.*?Due\s+([^.\n]+))?'
    
    for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
        items.append({
            'marker': match.group(1),
            'name': match.group(2).strip(),
            'weight': float(match.group(3)),
            'due_date': match.group(4).strip() if match.group(4) else None
        })
    
    return items
```

#### Step 2: Handle Nested Items

**Challenge:** Some assessments have sub-items (e.g., "Inquiry (40%)" with sub-items worth 3%, 5%, 25%, 7%).

**Approach:**
- Detect parent items (main assessment)
- Detect sub-items (indented, bulleted, or numbered sub-items)
- Calculate if sub-items sum to parent weight
- Create separate assessments for sub-items OR create parent with note

**Implementation:**
```python
def extract_nested_assessments(text: str) -> List[AssessmentTask]:
    assessments = []
    
    # Find main items
    main_items = find_main_items(text)
    
    for item in main_items:
        # Check for sub-items
        sub_items = find_sub_items(text, item)
        
        if sub_items:
            # Create assessments for each sub-item
            for sub in sub_items:
                assessments.append(create_assessment(sub))
        else:
            # Create assessment for main item
            assessments.append(create_assessment(item))
    
    return assessments
```

#### Step 3: Extract Dates from Prose

**Patterns:**
- "Due Monday September 29"
- "Due Wednesday October 13"
- "Wed. December 8th"
- "Each Friday starting Sept 12"

**Implementation:**
```python
def extract_date_from_text(text: str) -> Optional[datetime]:
    # Pattern: Due [Day] [Month] [Day]
    patterns = [
        r'Due\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(\w+)\s+(\d{1,2})',
        r'Due\s+(\w+)\s+(\d{1,2})',
        r'(\w+\.?)\s+(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return parse_date_match(match)
    
    return None
```

---

## Universal Weight Extraction

**Goal:** Extract weight percentages consistently across both formats.

**Patterns:**
- `5%`, `15%`, `25.5%`
- `(15%)`, `(5%)` in parentheses
- `Completion#`, `Completion` (mark as completion-based)
- `Weighted` (needs manual review)

**Implementation:**
```python
def extract_weight_universal(text: str) -> Optional[float]:
    # Try percentage pattern
    match = re.search(r'(\d+\.?\d*)%', text)
    if match:
        return float(match.group(1))
    
    # Check for completion-based
    if 'completion' in text.lower():
        return None  # Mark for review
    
    return None
```

---

## Universal Date Extraction

**Goal:** Extract due dates consistently across both formats.

**Patterns:**
- `October 1`, `Oct 1`, `Oct 1st`
- `Sunday, Oct 19`, `Monday September 29`
- `Dec 2nd/3rd` (date range - use later date)
- `November 14th 6 – 8 PM` (with time)
- `Opens Nov 14th... Due Nov 21st` (multi-part - use due date)
- `December exam period` (needs term end date)
- `End of lab session on R3-W3` (relative - needs resolution)

**Implementation:**
```python
def extract_date_universal(text: str, term_end: date) -> Optional[datetime]:
    # Try various date patterns
    patterns = [
        r'(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday),?\s+(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?',
        r'(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?',
        r'Due\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(\w+)\s+(\d{1,2})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            month = match.group(1)
            day = int(match.group(2))
            year = determine_year(month, term_end)
            
            # Extract time if present
            time_match = re.search(r'(\d{1,2})(?:[:–-](\d{2}))?\s*(AM|PM)', text, re.IGNORECASE)
            hour, minute = extract_time(time_match) if time_match else (23, 59)
            
            return datetime(year, month_to_num(month), day, hour, minute)
    
    # Handle special cases
    if 'exam period' in text.lower():
        return datetime.combine(term_end, time(23, 59))
    
    return None
```

---

## Implementation Priority

### Phase 1: Table-Based Extraction (High Priority)
- **Why:** 3 out of 4 PDFs use this format
- **Impact:** Will fix PP3000E extraction immediately
- **Effort:** Medium (2-3 hours)

### Phase 2: Text-Based Extraction (Medium Priority)
- **Why:** 1 PDF uses this format (BIOCHEM 3381A)
- **Impact:** Completes universal coverage
- **Effort:** Medium (2-3 hours)

### Phase 3: Enhanced Date Parsing (Low Priority)
- **Why:** Handles edge cases
- **Impact:** Improves accuracy
- **Effort:** Low (1 hour)

### Phase 4: Completion-Based Handling (Low Priority)
- **Why:** Some assessments use "Completion#" instead of percentage
- **Impact:** Flags items for review
- **Effort:** Low (30 minutes)

---

## Testing Strategy

1. **Unit Tests:** Test each extraction function with sample data
2. **Integration Tests:** Test full extraction on all 4 reference PDFs
3. **Validation:** Ensure total weight ≈ 100% (or >100% with extra credit)
4. **Edge Cases:** Test with:
   - Multi-row assessments
   - Completion-based assessments
   - Date ranges
   - Relative dates
   - Summary rows

---

## Success Criteria

✅ **Table-based extraction:**
- Extracts all assessments from PHYS 3120, PHYS 3140, PP3000E
- Total weight ≈ 100%
- Handles multi-row assessments
- Handles completion-based assessments

✅ **Text-based extraction:**
- Extracts all assessments from BIOCHEM 3381A
- Total weight ≈ 100%
- Handles nested items

✅ **Universal:**
- Works with both formats automatically
- Graceful fallback if format detection fails
- Clear error messages for manual review

---

## Next Steps

1. Implement Phase 1 (Table-based extraction)
2. Test on PP3000E (currently broken)
3. Implement Phase 2 (Text-based extraction)
4. Test on BIOCHEM 3381A
5. Validate on all 4 PDFs
6. Deploy and monitor

