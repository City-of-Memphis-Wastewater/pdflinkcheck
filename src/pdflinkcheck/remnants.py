import re
import fitz

# Regular expression pattern for common URLs (http, https, www, mhtml)
URI_PATTERN = re.compile(
    r'(?:https?|mhtml|file|ftp):\/\/\S+|\bwww\.\S+\b', 
    re.IGNORECASE
)

# Regular expression pattern for email addresses
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', 
    re.IGNORECASE
)

def clean_ex_rect(ex_rect_tuple):
    # If the input is a string, attempt to parse it
    if isinstance(ex_rect_tuple, str):
        try:
            # Use re.split to handle commas and spaces robustly.
            # Filter out empty strings that result from multiple delimiters (e.g., "1, 2,,3")
            parts = [c.strip() for c in re.split(r'[,\s]+', ex_rect_tuple.strip()) if c.strip()]
            coords = [float(c) for c in parts]
            
            if len(coords) != 4:
                # print(f"Warning: Rect string parsed to {len(coords)} coords, expected 4: {ex_rect_tuple}")
                return None
            return coords 
        except ValueError:
            # print(f"Warning: Could not parse rect string: {ex_rect_tuple}")
            return None # Use None to signal failure
    
    # If it's already a numeric sequence, check its length and type
    elif isinstance(ex_rect_tuple, (list, tuple)):
        if len(ex_rect_tuple) == 4 and all(isinstance(c, (int, float)) for c in ex_rect_tuple):
            return ex_rect_tuple
        # else: print(f"Warning: Numeric rect has incorrect length/type: {ex_rect_tuple}")
        return None
        
    # Handle the 'N/A: Missing Rect' case where link['rect'] might be None or a weird object
    else: 
        # print(f"Warning: Unexpected rect type/format: {ex_rect_tuple}")
        return None

def find_link_remnants(pdf_path, existing_links):
    """
    Scans the PDF for text that looks like a URI or email but is not a registered link annotation.
    """
    doc = fitz.open(pdf_path)
    remnants_data = []
    
    # 1. Create a set of all bounding boxes (Rects) of EXISTING links for exclusion
    existing_rects = set()
    for link in existing_links:
        rect_obj = link.get("from")

        if rect_obj:
            # NOTE: A fitz.Rect object is returned here. We can use its properties directly.
            
            # ⚠️ We still need to use your cleaning function if it handles rotation/quantization,
            # but we must pass it the coordinates in the expected format (e.g., as a list or tuple).
            
            # Convert the Rect object to a standard coordinate tuple (x0, y0, x1, y1)
            raw_coords = (rect_obj.x0, rect_obj.y0, rect_obj.x1, rect_obj.y1)

            # Assuming clean_ex_rect takes a list/tuple of 4 coordinates and cleans them
            cleaned_coords = clean_ex_rect(raw_coords) 
            print(f"cleaned_coords = {cleaned_coords}")
            
            # print(f"cleaned_coords = {cleaned_coords}") # Keep this for debugging
            
            if cleaned_coords:
                # Store the tuple of clean NUMBERS
                # Note: A list is not hashable, so converting to tuple is correct.
                existing_rects.add(tuple(cleaned_coords))

    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        
        # Extract text blocks with coordinates (MODE_TEXT is faster than 'text')
        text_blocks = page.get_text("blocks") 

        for block in text_blocks:
            x0, y0, x1, y1, text, block_no, block_type = block
            
            # Look for URI remnants
            for match in URI_PATTERN.finditer(text):
                remnant_text = match.group(0)
                
                # Use fitz to get the bounding box of the matched remnant text on the page
                text_instances = page.search_for(remnant_text) 
                
                if text_instances:
                    remnant_rect = tuple(text_instances[0])
                    
                    # Check if this remnant's bounding box overlaps with any existing link's bounding box
                    is_active_link = False
                    for ex_rect_tuple in existing_rects:
                        # ⚠️ CLEANUP: ex_rect_tuple is now GUARANTEED to be a tuple of 4 numbers
                        # We removed the unnecessary clean_ex_rect(ex_rect_tuple) call.
                        
                        # Convert tuple back to fitz.Rect for overlap check
                        ex_rect = fitz.Rect(ex_rect_tuple)
                        if ex_rect.intersects(text_instances[0]):
                            is_active_link = True
                            break
                            
                    if not is_active_link:
                        remnants_data.append({
                            'page': page_num + 1,
                            'type': 'URI Remnant',
                            'text': remnant_text,
                            'rect': remnant_rect
                        })

            # Look for Email remnants
            for match in EMAIL_PATTERN.finditer(text):
                remnant_text = match.group(0)
                
                text_instances = page.search_for(remnant_text)
                
                if text_instances:
                    remnant_rect = tuple(text_instances[0])
                    
                    is_active_link = False
                    for ex_rect_tuple in existing_rects:
                        # ⚠️ CLEANUP: ex_rect_tuple is now GUARANTEED to be a tuple of 4 numbers
                        ex_rect = fitz.Rect(ex_rect_tuple)
                        if ex_rect.intersects(text_instances[0]):
                            is_active_link = True
                            break
                            
                    if not is_active_link:
                        remnants_data.append({
                            'page': page_num + 1,
                            'type': 'Email Remnant',
                            'text': remnant_text,
                            'rect': remnant_rect
                        })

    doc.close()
    return remnants_data