import streamlit as st
import requests
import os
import re
from PIL import Image
import tempfile

# List of allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def main():
    st.set_page_config(page_title="Species Information Finder", layout="wide")
    
    st.title("Species Information Finder")
    st.write("Discover information about any species by name or by uploading an image.")
    
    # Create tabs for different functionality
    tab1, tab2 = st.tabs(["Search by Name", "Search by Image"])
    
    with tab1:
        st.header("Search by Species Name")
        species_name = st.text_input("Enter a species name (common or scientific):")
        
        if st.button("Search"):
            if not species_name:
                st.error("Please enter a species name")
            else:
                with st.spinner("Searching for species information..."):
                    # Get species info from Wikispecies API
                    species_data = get_species_info(species_name)
                    
                    # Get images from Wikimedia Commons API
                    images = get_species_images(species_name)
                    
                    display_results(species_data, images)
    
    with tab2:
        st.header("Search by Image Upload")
        uploaded_file = st.file_uploader("Upload an image of a species", type=ALLOWED_EXTENSIONS)
        
        if uploaded_file is not None:
            if allowed_file(uploaded_file.name):
                # Display the uploaded image
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Image", use_column_width=True)
                
                if st.button("Identify Species"):
                    with st.spinner("Identifying species from image..."):
                        # In a real app, you would call an image recognition API here
                        # For demo purposes, we'll use our mock function
                        species_name = get_mock_species_from_filename(uploaded_file.name)
                        
                        # Get species info from Wikispecies API
                        species_data = get_species_info(species_name)
                        
                        # Get images from Wikimedia Commons API
                        images = get_species_images(species_name)
                        
                        display_results(species_data, images)
            else:
                st.error("File type not allowed. Please upload an image file (PNG, JPG, JPEG, GIF).")

def display_results(species_data, images):
    """Display the results in a formatted way."""
    if "error" in species_data:
        st.error(species_data["error"])
        return
    
    st.success(f"Found information for: {species_data['title']}")
    
    # Create columns for layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Display classification information
        st.subheader("Classification")
        classification = species_data.get("classification", {})
        for rank, value in classification.items():
            if value != "Unknown":
                st.write(f"**{rank.capitalize()}:** {value}")
        
        # Display habitat information
        if species_data.get("habitat", "Unknown") != "Unknown":
            st.subheader("Habitat")
            st.write(species_data["habitat"])
    
    with col2:
        # Display description
        st.subheader("Description")
        st.write(species_data.get("description", "No description available."))
        
        # Display fun facts if available
        if species_data.get("fun_facts"):
            st.subheader("Interesting Facts")
            for i, fact in enumerate(species_data["fun_facts"], 1):
                st.write(f"{i}. {fact}")
    
    # Display images if available
    if images:
        st.subheader("Related Images")
        
        # Display up to 4 images in a grid
        cols = st.columns(min(4, len(images)))
        for idx, img in enumerate(images[:4]):
            with cols[idx]:
                if "thumb_url" in img:
                    st.image(img["thumb_url"], caption=img.get("description", ""), use_column_width=True)
                else:
                    st.image(img["url"], caption=img.get("description", ""), use_column_width=True)
                st.caption(f"Credit: {img.get('author', 'Unknown')} | License: {img.get('license', 'Unknown')}")
    else:
        st.warning("No images found for this species.")

# All the existing functions from your Flask app can remain exactly the same
# (get_species_info, get_wikispecies_data, get_wikipedia_data, etc.)
# I'll include them below for completeness, but they don't need to change

def get_species_info(species_name):
    """
    Get species information from both Wikispecies and Wikipedia APIs
    with improved extraction and fallback strategies for better results.
    """
    # Create the base species info structure
    species_info = {
        "title": species_name,  # Default to the search query
        "description": "No description available.",
        "categories": [],
        "links": [],
        "last_modified": "Unknown",
        "classification": {
            "kingdom": "Unknown", 
            "phylum": "Unknown", 
            "class": "Unknown", 
            "order": "Unknown", 
            "family": "Unknown", 
            "genus": "Unknown", 
            "species": "Unknown"
        },
        "habitat": "Unknown",
        "fun_facts": [],
        "data_sources": []  # Track where we got data from
    }
    
    # Try to get data from Wikispecies first
    wikispecies_info = get_wikispecies_data(species_name)
    
    # If we got a valid response, update our species_info
    if not wikispecies_info.get("error"):
        species_info.update(wikispecies_info)
        species_info["data_sources"].append("Wikispecies")
    
    # Now try to get complementary data from Wikipedia
    wikipedia_info = get_wikipedia_data(species_name)
    
    # If Wikipedia returned valid data, supplement our existing info
    if not wikipedia_info.get("error"):
        # Use Wikipedia description if Wikispecies didn't have one
        if species_info["description"] == "No description available." or len(species_info["description"]) < 50:
            species_info["description"] = wikipedia_info.get("description", species_info["description"])
        
        # Always prefer Wikipedia habitat info as it's likely more detailed
        species_info["habitat"] = wikipedia_info.get("habitat", species_info["habitat"])
        
        # Merge classification info from Wikipedia, preferring Wikipedia data
        if "classification" in wikipedia_info:
            for rank, value in wikipedia_info["classification"].items():
                if value != "Unknown":
                    species_info["classification"][rank] = value
        
        # Add Wikipedia fun facts to our collection, avoiding duplicates
        if wikipedia_info.get("fun_facts"):
            existing_facts = species_info.get("fun_facts", [])
            for fact in wikipedia_info["fun_facts"]:
                if not any(similarity_score(fact, existing) > 0.7 for existing in existing_facts):
                    existing_facts.append(fact)
            species_info["fun_facts"] = existing_facts[:4]  # Limit to 4 facts
        
        species_info["data_sources"].append("Wikipedia")
    
    # If we didn't get any data from either source, return an error
    if not species_info["data_sources"]:
        species_info["error"] = "Species information not found in either Wikispecies or Wikipedia."
    
    return species_info

def get_wikispecies_data(species_name):
    """
    Get species information from Wikispecies API
    """
    # Wikispecies API endpoint
    url = "https://species.wikimedia.org/w/api.php"
    
    # Parameters for the API request - get more info to work with
    params = {
        "action": "query",
        "format": "json",
        "titles": species_name,
        "prop": "extracts|categories|info|links",
        "exintro": True,  # Get only the intro section
        "explaintext": True,  # Get plain text, not HTML
        "cllimit": 50,  # Get more categories
        "pllimit": 50,  # Get more links
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        # Extract page data
        pages = data.get("query", {}).get("pages", {})
        
        if not pages:
            return {"error": "No data found in Wikispecies"}
        
        # Get the first page (there should only be one)
        page_id = next(iter(pages))
        page = pages[page_id]
        
        # Default information structure with placeholders
        species_info = {
            "title": species_name,  # Default to the search query
            "description": "No description available.",
            "categories": [],
            "links": [],
            "last_modified": "Unknown",
            "classification": {
                "kingdom": "Unknown", 
                "phylum": "Unknown", 
                "class": "Unknown", 
                "order": "Unknown", 
                "family": "Unknown", 
                "genus": "Unknown", 
                "species": "Unknown"
            },
            "habitat": "Unknown",
            "fun_facts": []
        }
        
        # Check if the page exists
        if int(page_id) < 0:
            species_info["error"] = "Species not found in Wikispecies. Try a different spelling or check for the scientific name."
            return species_info
        
        # Extract the relevant information
        species_info["title"] = page.get("title", species_name)
        species_info["description"] = page.get("extract", "No description available.")
        
        # Get all categories
        if "categories" in page:
            species_info["categories"] = [cat.get("title") for cat in page.get("categories", [])]
        
        # Get all links (can be useful for finding related info)
        if "links" in page:
            species_info["links"] = [link.get("title") for link in page.get("links", [])]
            
        species_info["last_modified"] = page.get("touched", "Unknown")
        
        # Clean up the description (remove unnecessary line breaks, etc.)
        if species_info["description"]:
            species_info["description"] = species_info["description"].replace("\n", " ").strip()
            # Remove multiple spaces
            import re
            species_info["description"] = re.sub(r' +', ' ', species_info["description"])
        
        # Try different strategies to extract classification
        # Strategy 1: Extract from categories
        species_info["classification"] = extract_classification(species_info["categories"])
        
        # Strategy 2: Try to extract genus and species from the title if available
        title = species_info.get("title", "")
        title_parts = title.split()
        
        # If the title consists of two words, it might be a binomial name (genus + species)
        if len(title_parts) == 2:
            genus = title_parts[0]
            species = title_parts[1]
            
            # Update classification with this information
            classification = species_info.get("classification", {})
            if classification.get("genus") == "Unknown":
                classification["genus"] = genus
            if classification.get("species") == "Unknown":
                classification["species"] = species
            species_info["classification"] = classification
        
        # Strategy 3: Look for classification information in links
        if species_info.get("links"):
            for link in species_info["links"]:
                # Check if link might be a taxonomic rank
                link_parts = link.split()
                if len(link_parts) == 1:
                    # Check common taxonomic suffixes for families, orders, etc.
                    if link.endswith("idae"):  # Family suffix
                        species_info["classification"]["family"] = link
                    elif link.endswith("inae"):  # Subfamily suffix
                        # Store subfamily info in a separate key
                        species_info["classification"]["subfamily"] = link
                    elif link.endswith("ales"):  # Order suffix for plants
                        species_info["classification"]["order"] = link
                    elif link.endswith("aceae"):  # Family suffix for plants
                        species_info["classification"]["family"] = link
        
        # Extract habitat info 
        species_info["habitat"] = extract_habitat(species_info["description"])
        
        # Extract fun facts
        species_info["fun_facts"] = extract_fun_facts(species_info["description"])
        
        # If the description is too short or missing, try to create a basic description
        if not species_info["description"] or len(species_info["description"]) < 20:
            # Create a basic description from available information
            classification = species_info["classification"]
            parts = []
            
            if classification["genus"] != "Unknown" and classification["species"] != "Unknown":
                parts.append(f"{species_info['title']} is a species in the genus {classification['genus']}.")
            
            if classification["family"] != "Unknown":
                parts.append(f"It belongs to the family {classification['family']}.")
                
            if classification["order"] != "Unknown":
                parts.append(f"It is classified under the order {classification['order']}.")
                
            if parts:
                species_info["description"] = " ".join(parts)
            else:
                species_info["description"] = f"{species_info['title']} is a species documented in Wikispecies, the free species directory."
        
        return species_info
    
    except Exception as e:
        error_msg = str(e)
        return {
            "error": f"Error retrieving species information from Wikispecies: {error_msg}",
            "title": species_name,
            "description": "No information available due to an error. Please try a different species name.",
            "classification": {"kingdom": "Unknown", "phylum": "Unknown", "class": "Unknown", "order": "Unknown", "family": "Unknown", "genus": "Unknown", "species": "Unknown"},
            "habitat": "Unknown",
            "fun_facts": []
        }

def get_wikipedia_data(species_name):
    """
    Get species information from Wikipedia API, focusing on description,
    habitat, and fun facts.
    """
    # Wikipedia API endpoint
    url = "https://en.wikipedia.org/w/api.php"
    
    # First, try to search for the page to get the correct title
    search_params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": species_name,
        "srlimit": 1,  # Get just the best match
    }
    
    try:
        # Search for the page first to get the exact title
        search_response = requests.get(url, params=search_params)
        search_data = search_response.json()
        
        # Check if we found any search results
        search_results = search_data.get("query", {}).get("search", [])
        if not search_results:
            return {"error": "No matching Wikipedia page found for this species."}
        
        # Get the page title from the search result
        page_title = search_results[0].get("title")
        
        # Now get the full page content
        content_params = {
            "action": "query",
            "format": "json",
            "titles": page_title,
            "prop": "extracts|categories|sections",
            "exintro": False,  # Get the full content, not just the intro
            "explaintext": True,  # Get plain text, not HTML
            "cllimit": 50,  # Get more categories
        }
        
        content_response = requests.get(url, params=content_params)
        content_data = content_response.json()
        
        # Extract page data
        pages = content_data.get("query", {}).get("pages", {})
        
        if not pages:
            return {"error": "Failed to retrieve Wikipedia page content."}
        
        # Get the first page (there should only be one)
        page_id = next(iter(pages))
        page = pages[page_id]
        
        # Check if the page exists
        if int(page_id) < 0:
            return {"error": "Wikipedia page not found."}
        
        # Get basic information
        species_info = {
            "title": page.get("title", species_name),
            "description": "",
            "habitat": "Unknown",
            "fun_facts": [],
            "classification": {
                "kingdom": "Unknown", 
                "phylum": "Unknown", 
                "class": "Unknown", 
                "order": "Unknown", 
                "family": "Unknown", 
                "genus": "Unknown", 
                "species": "Unknown"
            }
        }
        
        # Extract the content
        full_text = page.get("extract", "")
        
        # Clean up the text
        if full_text:
            full_text = full_text.replace("\n\n", "||").replace("\n", " ").replace("||", "\n\n")
            
            # Get sections from the content
            sections = full_text.split("\n\n")
            
            # The first section is usually a good description
            if sections:
                species_info["description"] = sections[0].strip()
            
            # Look for habitat information in the full text
            habitat_section = extract_wikipedia_section(full_text, ["Habitat", "Distribution", "Range", "Ecology", "Environment"])
            if habitat_section:
                species_info["habitat"] = habitat_section
            else:
                # If no specific habitat section, use our habitat extraction on the full text
                habitat = extract_habitat(full_text)
                if habitat != "Unknown":
                    species_info["habitat"] = habitat
            
            # Extract fun facts from various interesting sections
            behavior_section = extract_wikipedia_section(full_text, ["Behavior", "Behaviour", "Life cycle", "Diet", "Feeding", "Reproduction", "Biology"])
            if behavior_section:
                facts = extract_fun_facts(behavior_section)
                if facts:
                    species_info["fun_facts"].extend(facts)
            
            # If we don't have enough facts, try conservation status or other sections
            if len(species_info["fun_facts"]) < 2:
                conservation_section = extract_wikipedia_section(full_text, ["Conservation", "Status", "Threats", "Population"])
                if conservation_section:
                    facts = extract_fun_facts(conservation_section)
                    if facts:
                        for fact in facts:
                            if fact not in species_info["fun_facts"]:
                                species_info["fun_facts"].append(fact)
            
            # If we still don't have enough facts, use our fun facts extraction on the full text
            if len(species_info["fun_facts"]) < 2:
                general_facts = extract_fun_facts(full_text)
                if general_facts:
                    for fact in general_facts:
                        if fact not in species_info["fun_facts"]:
                            species_info["fun_facts"].append(fact)
            
            # Limit to 4 facts
            species_info["fun_facts"] = species_info["fun_facts"][:4]
            
            # Extract classification from Wikipedia content
            wiki_classification = extract_wikipedia_classification(full_text, page.get("title", ""), search_data)
            if wiki_classification:
                species_info["classification"] = wiki_classification
        
        return species_info
    
    except Exception as e:
        error_msg = str(e)
        return {
            "error": f"Error retrieving information from Wikipedia: {error_msg}",
            "title": species_name,
            "description": "No information available from Wikipedia due to an error.",
            "habitat": "Unknown",
            "fun_facts": []
        }

def extract_wikipedia_section(text, section_keywords):
    """
    Try to extract a specific section from Wikipedia text content.
    Returns the first matching section or None if no match is found.
    """
    if not text:
        return None
    
    # Try to find section headings in the text
    section_pattern = r"==\s*([^=]+)\s*=="
    sections = re.findall(section_pattern, text)
    
    # Check if any of our target sections exist
    matching_sections = []
    for keyword in section_keywords:
        for section in sections:
            if keyword.lower() in section.lower():
                # Found a matching section, now extract its content
                section_regex = re.escape(f"== {section} ==")
                try:
                    # Find where this section starts
                    start_match = re.search(section_regex, text)
                    if start_match:
                        start_pos = start_match.end()
                        
                        # Find where the next section starts
                        next_section = re.search(r"==\s*[^=]+\s*==", text[start_pos:])
                        if next_section:
                            end_pos = start_pos + next_section.start()
                            section_text = text[start_pos:end_pos].strip()
                        else:
                            # This is the last section
                            section_text = text[start_pos:].strip()
                        
                        matching_sections.append(section_text)
                except Exception:
                    # Skip this section if there's any error processing it
                    continue
    
    # If we found any matching sections, join them (limit to 2 for conciseness)
    if matching_sections:
        return " ".join(matching_sections[:2])
    
    # Alternative approach: look for paragraphs containing the keywords
    paragraphs = text.split("\n\n")
    for keyword in section_keywords:
        for paragraph in paragraphs:
            if keyword.lower() in paragraph.lower():
                return paragraph
    
    return None

def get_species_images(species_name):
    """
    Get species images from Wikimedia Commons API with improved search
    strategies for better results.
    """
    # Wikimedia Commons API endpoint
    url = "https://commons.wikimedia.org/w/api.php"
    
    # Function to perform a search with given parameters
    def search_images(search_term, limit=10):
        # Parameters for the API request
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": 6,  # File namespace
            "gsrsearch": search_term,
            "gsrlimit": limit,  # Limit results
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 800,  # Thumbnail width
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            # Extract image data
            pages = data.get("query", {}).get("pages", {})
            
            if not pages:
                return []
            
            images = []
            for page_id, page in pages.items():
                image_info = page.get("imageinfo", [{}])[0]
                
                # Extract metadata
                metadata = image_info.get("extmetadata", {})
                description = metadata.get("ImageDescription", {}).get("value", "No description")
                author = metadata.get("Artist", {}).get("value", "Unknown")
                license = metadata.get("License", {}).get("value", "Unknown")
                
                # Skip non-image files (like pdfs, audio, etc.)
                title = page.get("title", "").lower()
                if any(ext in title for ext in ['.pdf', '.svg', '.mp3', '.mp4', '.ogg', '.wav', '.webm']):
                    continue
                
                image = {
                    "title": page.get("title", "Unknown"),
                    "url": image_info.get("url", ""),
                    "thumb_url": image_info.get("thumburl", ""),
                    "description": description,
                    "author": author,
                    "license": license,
                }
                
                images.append(image)
            
            return images
        
        except Exception as e:
            return [{"error": str(e)}]
    
    # STRATEGY 1: Try exact file name search first
    images = search_images(f"file:{species_name}")
    
    # If no results, try a broader search
    if not images:
        # STRATEGY 2: Try removing the file: prefix for broader results
        images = search_images(species_name)
    
    # If still no results or very few, try some variations
    if len(images) < 3:
        # Split the species name and try different combinations
        name_parts = species_name.split()
        
        # STRATEGY 3: If it's a binomial name, try with just the genus or species part
        if len(name_parts) == 2:
            # Try with just the genus (first part)
            genus_images = search_images(f"{name_parts[0]}")
            
            # Add unique images from genus search
            existing_urls = [img.get("url") for img in images]
            for img in genus_images:
                if img.get("url") not in existing_urls:
                    images.append(img)
                    existing_urls.append(img.get("url"))
                    
                    # Stop if we now have enough images
                    if len(images) >= 5:
                        break
    
    # If we found at least some images, return them
    if images:
        return images
    
    # STRATEGY 4: Last resort - try a very general search
    # This could be improved by using the taxonomy info
    return search_images("species taxonomy nature")

def extract_classification(categories):
    """
    Extract classification information from categories and additional WikiData
    with improved pattern matching and detection.
    """
    # Initialize with default "Unknown" values
    classification = {
        "kingdom": "Unknown",
        "phylum": "Unknown",
        "class": "Unknown",
        "order": "Unknown",
        "family": "Unknown",
        "genus": "Unknown",
        "species": "Unknown",
    }
    
    # Skip empty categories
    if not categories:
        return classification
    
    # Common taxonomy patterns in category names with more variations
    taxonomy_patterns = {
        "kingdom": ["kingdom:", "regnum:", "reino:", "regno:", "kingdom ", "regnum ", "reino ", "reino "],
        "phylum": ["phylum:", "division:", "división:", "divisio:", "phylum ", "division ", "división ", "divisio "],
        "class": ["class:", "clase:", "classis:", "class ", "clase ", "classis "],
        "order": ["order:", "orden:", "ordo:", "order ", "orden ", "ordo "],
        "family": ["family:", "familia:", "family ", "familia "],
        "genus": ["genus:", "género:", "genero:", "genus ", "género ", "genero "],
        "species": ["species:", "especie:", "specie:", "species ", "especie ", "specie "]
    }
    
    # STRATEGY 1: Direct matching from category names
    for category in categories:
        # Skip Categories: prefix if present
        if category.startswith("Category:"):
            category = category[9:]
            
        category_lower = category.lower()
        
        # Check for direct taxonomy mentions
        for rank, patterns in taxonomy_patterns.items():
            for pattern in patterns:
                if pattern in category_lower:
                    # Extract the value after the pattern
                    parts = category_lower.split(pattern)
                    if len(parts) > 1:
                        # Clean up the value (capitalize first letter, remove trailing spaces and special chars)
                        value = parts[1].strip().split()[0].capitalize()
                        classification[rank] = value
                        break
    
    # STRATEGY 2: Look for categories that directly match taxonomic naming conventions
    for category in categories:
        # Skip Categories: prefix if present
        if category.startswith("Category:"):
            category = category[9:]
            
        category_parts = category.split()
        
        # Check for single-word categories that might be taxonomic names
        if len(category_parts) == 1:
            name = category_parts[0]
            
            # Check for common taxonomic suffixes
            if name.endswith("idae"):  # Family suffix for animals
                classification["family"] = name
            elif name.endswith("inae"):  # Subfamily suffix
                # Store subfamily info in a separate key
                classification["subfamily"] = name
            elif name.endswith("ales"):  # Order suffix for plants
                classification["order"] = name
            elif name.endswith("aceae"):  # Family suffix for plants
                classification["family"] = name
            elif name.endswith("ineae"):  # Suborder suffix for plants
                # Store suborder info in a separate key
                classification["suborder"] = name
            elif name.endswith("oideae"):  # Subfamily suffix for plants
                # Store subfamily info in a separate key
                classification["subfamily"] = name
    
    # STRATEGY 3: Check for categories that contain common taxonomic rank names
    taxonomic_rank_names = ["kingdom", "phylum", "division", "class", "order", "family", "genus", "species"]
    for category in categories:
        # Skip Categories: prefix if present
        if category.startswith("Category:"):
            category = category[9:]
            
        category_lower = category.lower()
        
        for rank in taxonomic_rank_names:
            if rank in category_lower:
                # Look for words after the rank name
                parts = category_lower.split(rank)
                if len(parts) > 1 and parts[1].strip():
                    # Get the first word after the rank
                    value = parts[1].strip().split()[0].capitalize()
                    if classification[rank] == "Unknown":
                        classification[rank] = value
    
    # Final cleanup: ensure proper capitalization and formatting
    for rank, value in classification.items():
        if value != "Unknown":
            # Capitalize first letter for taxonomic ranks
            classification[rank] = value[0].upper() + value[1:]
    
    return classification

def extract_habitat(description):
    """
    Extract habitat information from description using a more comprehensive approach
    with multiple fallback strategies and pattern recognition.
    """
    if not description or description == "No description available":
        return "Unknown"
    
    # Split the description into sentences
    sentences = description.replace(". ", ".|").replace("! ", "!|").replace("? ", "?|").split("|")
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # STRATEGY 1: Direct habitat statements
    # Expanded list of habitat-related keywords and phrases
    habitat_keywords = [
        "habitat", "lives in", "found in", "native to", "occurs in", "distribution", 
        "range includes", "ecosystem", "biome", "environment", "inhabits", "dwelling in",
        "endemic to", "natural range", "geographical range", "distributed across",
        "prefers", "thrives in", "flourishes in", "resides in", "habitat type",
        "commonly found", "typically found", "often found", "usually found", "primarily found"
    ]
    
    # STRATEGY 2: Geography and climate context
    # Climate and geography keywords to catch broader context
    climate_keywords = [
        "tropical", "temperate", "polar", "arctic", "antarctic", "desert", 
        "rainforest", "forest", "jungle", "grassland", "savanna", "wetland", 
        "marsh", "swamp", "mountain", "alpine", "coastal", "marine", "freshwater",
        "ocean", "sea", "river", "lake", "stream", "pond", "terrestrial", "aquatic",
        "woodland", "meadow", "tundra", "taiga", "steppe", "continent", "island",
        "shore", "beach", "reef", "cave", "burrow", "nest", "canopy", "undergrowth"
    ]
    
    # STRATEGY 3: Regional indicators (continents, regions, countries)
    region_keywords = [
        "africa", "asia", "europe", "north america", "south america", "australia", 
        "antarctica", "oceania", "mediterranean", "pacific", "atlantic", "indian ocean",
        "arctic ocean", "southern ocean", "northern", "southern", "eastern", "western",
        "central", "worldwide", "global", "cosmopolitan", "international"
    ]
    
    # STRATEGY 4: Verbs that might indicate location or movement patterns
    action_keywords = [
        "migrate", "roam", "travel", "swim", "fly", "climb", "burrow", "dig", "nest", 
        "breed", "forage", "hunt", "territory", "range"
    ]
    
    # Sentences that might contain habitat information
    habitat_sentences = []
    
    # Apply Strategy 1: Direct habitat statements
    for sentence in sentences:
        for keyword in habitat_keywords:
            if keyword.lower() in sentence.lower():
                habitat_sentences.append(sentence)
                break
    
    # Apply Strategy 2: Geography and climate context (if strategy 1 didn't yield results)
    if not habitat_sentences:
        for sentence in sentences:
            for keyword in climate_keywords:
                if keyword.lower() in sentence.lower():
                    habitat_sentences.append(sentence)
                    break
    
    # Apply Strategy 3: Regional indicators (if strategies 1-2 didn't yield results)
    if not habitat_sentences:
        for sentence in sentences:
            for keyword in region_keywords:
                if keyword.lower() in sentence.lower():
                    habitat_sentences.append(sentence)
                    break
    
    # Apply Strategy 4: Action verbs related to habitat (if strategies 1-3 didn't yield results)
    if not habitat_sentences:
        for sentence in sentences:
            for keyword in action_keywords:
                if keyword.lower() in sentence.lower():
                    habitat_sentences.append(sentence)
                    break
    
    # Fallback Strategy: If no habitat information was found, try to use the first or second sentence
    # as they often contain general information about where the species lives
    if not habitat_sentences and len(sentences) >= 2:
        # Skip the first sentence if it's just a definition and take the second
        if len(sentences) > 2:
            second_sentence = sentences[1]
            # Check if the second sentence has reasonable length to be informative
            if len(second_sentence.split()) > 5:
                habitat_sentences.append(second_sentence)
        
        # If second sentence wasn't suitable or not available, use the first
        if not habitat_sentences:
            first_sentence = sentences[0]
            if len(first_sentence.split()) > 5:
                habitat_sentences.append(first_sentence)
    
    # Format the habitat information
    if habitat_sentences:
        # If we have multiple sentences, join them (but limit to 2 for conciseness)
        if len(habitat_sentences) > 1:
            combined = ". ".join(habitat_sentences[:2]).strip()
            # Make sure it ends with proper punctuation
            if not combined.endswith(('.', '!', '?')):
                combined += '.'
            return combined
        
        single = habitat_sentences[0].strip()
        # Make sure it ends with proper punctuation
        if not single.endswith(('.', '!', '?')):
            single += '.'
        return single
    
    # Last resort: construct a generic message if we couldn't find specific habitat info
    return "Specific habitat information not available from Wikispecies. Try searching online for more details about this species' natural environment."

def extract_fun_facts(description):
    """
    Extract interesting fun facts from the description using keyword-based identification,
    with improved pattern recognition and a structured approach to generate fun facts
    even with limited information.
    """
    if not description or description == "No description available":
        return ["No specific information available for this species in Wikispecies."]
    
    # Split the description into sentences
    sentences = description.replace(". ", ".|").replace("! ", "!|").replace("? ", "?|").split("|")
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # If the description is too short, include it as a single fact
    if len(sentences) == 1 and len(description) < 100:
        if not sentences[0].endswith(('.', '!', '?')):
            sentences[0] += '.'
        return [sentences[0]]
    
    # STRATEGY 1: Identify sentences with interesting keywords
    interesting_keywords = [
        "interesting", "unique", "unusual", "remarkable", "notable", "surprising",
        "fascinating", "amazing", "extraordinary", "distinctive", "special", "rare",
        "strange", "curious", "unlike", "peculiar", "odd", "bizarre", "striking",
        "colorful", "beautiful", "impressive", "popular", "famous", "well-known",
        "largest", "smallest", "fastest", "slowest", "oldest", "youngest", "only",
        "record", "discovery", "first", "last", "origin", "discovered", "introduced",
        "revered", "sacred", "symbol", "iconic", "emblem", "represented", "mythology",
        "legend", "folklore", "traditional", "cultural", "significance", "historical"
    ]
    
    # STRATEGY 2: Physical characteristics and biology often make good facts
    biology_keywords = [
        "lifespan", "longevity", "size", "weight", "height", "length", "wingspan",
        "color", "pattern", "marking", "appearance", "physical", "morphology", "anatomy",
        "feature", "characteristic", "distinctive", "body", "shape", "structure",
        "adaptation", "evolved", "evolution", "mutation", "gene", "genetic", "chromosome",
        "hybrid", "species", "subspecies", "variety", "breed", "strain", "extinct",
        "endangered", "threatened", "vulnerable", "conservation", "protected"
    ]
    
    # STRATEGY 3: Behavior and lifestyle information
    behavior_keywords = [
        "diet", "eat", "feeding", "food", "prey", "predator", "hunt", "scavenge",
        "forage", "graze", "browse", "omnivore", "carnivore", "herbivore", "insectivore",
        "behavior", "behaviour", "habit", "activity", "social", "solitary", "group",
        "herd", "flock", "pack", "colony", "community", "family", "nocturnal", "diurnal",
        "crepuscular", "migrate", "migration", "hibernate", "hibernation", "estivate",
        "dormant", "sleep", "rest", "active", "territory", "defend", "aggressive",
        "docile", "tame", "wild", "domestic", "domesticated", "trained", "human"
    ]
    
    # STRATEGY 4: Reproduction is always interesting
    reproduction_keywords = [
        "reproduce", "reproduction", "breeding", "mate", "mating", "courtship", "display",
        "attract", "offspring", "young", "juvenile", "infant", "baby", "child", "adult",
        "egg", "spawn", "birth", "pregnant", "gestation", "incubation", "hatch", "nestling",
        "fledgling", "litter", "clutch", "brood", "parent", "care", "raise", "nurse", "wean"
    ]
    
    # Comparative patterns that often indicate interesting facts
    comparative_patterns = [
        "more than", "less than", "bigger than", "smaller than", "larger than",
        "faster than", "slower than", "better than", "worse than", "greater than",
        "unlike", "similar to", "compared to", "in contrast to", "differs from",
        "up to", "as many as", "can reach", "can grow", "can live", "known to",
        "capable of", "able to", "estimated", "approximately", "about", "around"
    ]
    
    # Measurement patterns that often indicate interesting statistics
    measurement_patterns = [
        "cm", "meter", "metre", "kilometer", "kilometre", "feet", "foot", "inch",
        "kg", "gram", "pound", "ton", "tonne", "year", "month", "week", "day", "hour",
        "percent", "°C", "°F", "degree", "celsius", "fahrenheit", "temperature", 
        "speed", "mph", "kph", "knot", "altitude", "depth", "width", "height"
    ]
    
    # Collect potential facts using different strategies
    fact_candidates = {
        "interesting": [],
        "biological": [],
        "behavioral": [],
        "reproductive": [],
        "comparative": [],
        "measurements": [],
        "general": []
    }
    
    # Apply strategies to collect potential facts
    for sentence in sentences:
        # Skip very short sentences
        if len(sentence.split()) < 4:
            continue
            
        # Flag to track if the sentence has been categorized
        categorized = False
        
        # Strategy 1: Interesting keywords
        for keyword in interesting_keywords:
            if keyword.lower() in sentence.lower():
                fact_candidates["interesting"].append(sentence)
                categorized = True
                break
                
        if not categorized:
            # Strategy 2: Biological characteristics
            for keyword in biology_keywords:
                if keyword.lower() in sentence.lower():
                    fact_candidates["biological"].append(sentence)
                    categorized = True
                    break
        
        if not categorized:
            # Strategy 3: Behavior keywords
            for keyword in behavior_keywords:
                if keyword.lower() in sentence.lower():
                    fact_candidates["behavioral"].append(sentence)
                    categorized = True
                    break
                    
        if not categorized:
            # Strategy 4: Reproduction keywords
            for keyword in reproduction_keywords:
                if keyword.lower() in sentence.lower():
                    fact_candidates["reproductive"].append(sentence)
                    categorized = True
                    break
        
        if not categorized:
            # Check for comparative patterns
            for pattern in comparative_patterns:
                if pattern.lower() in sentence.lower():
                    fact_candidates["comparative"].append(sentence)
                    categorized = True
                    break
                    
        if not categorized:
            # Check for measurement patterns
            has_number = any(c.isdigit() for c in sentence)
            if has_number:
                for pattern in measurement_patterns:
                    if pattern.lower() in sentence.lower():
                        fact_candidates["measurements"].append(sentence)
                        categorized = True
                        break
                        fact_candidates["measurements"].append(sentence)
                        categorized = True
                        break
        
        # If sentence wasn't categorized by any specific strategy, add to general
        if not categorized and len(sentence.split()) > 5:
            fact_candidates["general"].append(sentence)
    
    # Select facts from each category to ensure diversity (prioritizing the most interesting ones)
    selected_facts = []
    
    # Priority order for fact selection
    categories = ["interesting", "measurements", "biological", "reproductive", "behavioral", "comparative", "general"]
    
    # First, try to get at least one fact from high-priority categories
    for category in categories[:3]:  # First 3 are highest priority
        if fact_candidates[category]:
            selected_facts.append(fact_candidates[category][0])
            fact_candidates[category].pop(0)  # Remove the used fact
    
    # Now fill remaining slots with a mix of all categories
    remaining_slots = 4 - len(selected_facts)  # Maximum 4 facts total
    
    if remaining_slots > 0:
        for category in categories:
            if fact_candidates[category] and remaining_slots > 0:
                next_fact = fact_candidates[category][0]
                # Only add if not too similar to already selected facts
                if not any(similarity_score(next_fact, fact) > 0.7 for fact in selected_facts):
                    selected_facts.append(next_fact)
                    remaining_slots -= 1
                fact_candidates[category].pop(0)  # Remove the used fact
    
    # If we still don't have enough facts, add more from general pool
    if len(selected_facts) < 2 and sentences:
        # Add the first sentence if it's not already included
        if sentences[0] not in selected_facts and len(sentences[0].split()) > 5:
            selected_facts.append(sentences[0])
            
        # Add another sentence from middle of the text if available
        middle_idx = len(sentences) // 2
        if len(sentences) > middle_idx and sentences[middle_idx] not in selected_facts and len(sentences[middle_idx].split()) > 5:
            selected_facts.append(sentences[middle_idx])
    
    # Last resort: if still no facts, create a generic fact
    if not selected_facts:
        selected_facts = ["This species is documented in Wikispecies, the free species directory."]
    
    # Ensure all facts end with proper punctuation
    for i in range(len(selected_facts)):
        if not selected_facts[i].endswith(('.', '!', '?')):
            selected_facts[i] += '.'
    
    # Remove duplicates while preserving order
    unique_facts = []
    for fact in selected_facts:
        if fact not in unique_facts:
            unique_facts.append(fact)
    
    return unique_facts[:4]  # Limit to max 4 facts

def similarity_score(str1, str2):
    """
    Calculate a simple similarity score between two strings
    based on word overlap. Used to avoid selecting too similar facts.
    Returns a value between 0 (completely different) and 1 (identical).
    """
    if not str1 or not str2:
        return 0
        
    # Convert to lowercase and split into words
    words1 = set(str1.lower().split())
    words2 = set(str2.lower().split())
    
    # Calculate Jaccard similarity
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    if not union:
        return 0
        
    return len(intersection) / len(union)

def get_mock_species_from_filename(filename):
    """
    A mock function that simulates image recognition by looking at the filename.
    In a real application, this would be replaced with an actual image recognition API.
    """
    filename_lower = filename.lower()
    
    # List of common animals and their possible filenames
    animal_keywords = {
        "cat": "Felis catus",
        "dog": "Canis familiaris",
        "bird": "Aves",
        "eagle": "Aquila chrysaetos",
        "lion": "Panthera leo",
        "tiger": "Panthera tigris",
        "bear": "Ursus arctos",
        "wolf": "Canis lupus",
        "fox": "Vulpes vulpes",
        "deer": "Cervidae",
        "elephant": "Loxodonta africana",
        "giraffe": "Giraffa camelopardalis",
        "zebra": "Equus quagga",
        "monkey": "Primates",
        "gorilla": "Gorilla gorilla",
        "fish": "Actinopterygii",
        "shark": "Selachimorpha",
        "dolphin": "Tursiops truncatus",
        "whale": "Cetacea",
        "snake": "Serpentes",
        "lizard": "Lacertilia",
        "turtle": "Testudines",
        "frog": "Anura",
        "butterfly": "Lepidoptera",
        "bee": "Apis mellifera",
    }
    
    # List of common plants and their possible filenames
    plant_keywords = {
        "tree": "Arbor",
        "flower": "Anthophyta",
        "rose": "Rosa",
        "tulip": "Tulipa",
        "daisy": "Bellis perennis",
        "sunflower": "Helianthus annuus",
        "oak": "Quercus",
        "pine": "Pinus",
        "maple": "Acer",
        "fern": "Polypodiopsida",
        "moss": "Bryophyta",
        "grass": "Poaceae",
        "cactus": "Cactaceae",
        "palm": "Arecaceae",
        "orchid": "Orchidaceae",
    }
    
    # Check animal keywords
    for keyword, species in animal_keywords.items():
        if keyword in filename_lower:
            return species
    
    # Check plant keywords
    for keyword, species in plant_keywords.items():
        if keyword in filename_lower:
            return species
    
    # If no match is found, return a default species
    return "Homo sapiens"

def extract_wikipedia_classification(full_text, title, search_data=None):
    """
    Extract classification/taxonomy information from Wikipedia content.
    Uses various strategies including infobox parsing, section analysis, and text pattern matching.
    
    Args:
        full_text: The full text content of the Wikipedia page
        title: The title of the Wikipedia page
        search_data: Optional search data that might contain additional info
        
    Returns:
        A dictionary with taxonomic ranks and their values
    """
    # Initialize with default "Unknown" values
    classification = {
        "kingdom": "Unknown",
        "phylum": "Unknown",
        "class": "Unknown",
        "order": "Unknown",
        "family": "Unknown",
        "genus": "Unknown",
        "species": "Unknown"
    }
    
    if not full_text:
        return classification
    
    try:
        # STRATEGY 1: Look for taxonomic information in specific sections
        taxonomy_section = extract_wikipedia_section(full_text, ["Taxonomy", "Classification", "Taxonomic", "Scientific classification"])
        if taxonomy_section:
            # Extract taxonomic information from the section
            classification = extract_taxonomy_from_text(taxonomy_section, classification)
        
        # STRATEGY 2: Look for taxonomic information in infobox-like structures
        # Wikipedia infoboxes often appear at the beginning of the text with structured format
        infobox_patterns = [
            r"Kingdom:\s*([A-Za-z]+)",
            r"Phylum:\s*([A-Za-z]+)",
            r"Class:\s*([A-Za-z]+)",
            r"Order:\s*([A-Za-z]+)",
            r"Family:\s*([A-Za-z]+)",
            r"Genus:\s*([A-Za-z]+)",
            r"Species:\s*([A-Za-z]+)"
        ]
        
        # Apply each pattern to extract taxonomic information
        for i, pattern in enumerate(infobox_patterns):
            rank = list(classification.keys())[i]
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            if matches:
                classification[rank] = matches[0].strip()
        
        # STRATEGY 3: Parse the first paragraph for taxonomic information
        # First paragraphs in Wikipedia often contain taxonomic statements
        first_para = full_text.split('\n\n')[0] if '\n\n' in full_text else full_text
        classification = extract_taxonomy_from_text(first_para, classification)
        
        # STRATEGY 4: Try to extract genus and species from the title
        title_parts = title.split()
        if len(title_parts) >= 2 and classification["genus"] == "Unknown":
            # If title looks like a binomial name (e.g., "Panthera leo")
            if title_parts[0][0].isupper() and title_parts[0][1:].islower() and title_parts[1].islower():
                classification["genus"] = title_parts[0]
                if classification["species"] == "Unknown":
                    classification["species"] = title_parts[1]
        
        # STRATEGY 5: Look for taxonomic statements throughout the text
        # These patterns match statements like "belongs to the family Felidae"
        taxonomy_statement_patterns = [
            r"(?:belongs|belonging)\s+to\s+(?:the)?\s+kingdom\s+([A-Za-z]+)",
            r"(?:belongs|belonging)\s+to\s+(?:the)?\s+phylum\s+([A-Za-z]+)",
            r"(?:belongs|belonging)\s+to\s+(?:the)?\s+class\s+([A-Za-z]+)",
            r"(?:belongs|belonging)\s+to\s+(?:the)?\s+order\s+([A-Za-z]+)",
            r"(?:belongs|belonging)\s+to\s+(?:the)?\s+family\s+([A-Za-z]+)",
            r"(?:is|as)\s+a\s+(?:member|species)\s+of\s+(?:the)?\s+kingdom\s+([A-Za-z]+)",
            r"(?:is|as)\s+a\s+(?:member|species)\s+of\s+(?:the)?\s+phylum\s+([A-Za-z]+)",
            r"(?:is|as)\s+a\s+(?:member|species)\s+of\s+(?:the)?\s+class\s+([A-Za-z]+)",
            r"(?:is|as)\s+a\s+(?:member|species)\s+of\s+(?:the)?\s+order\s+([A-Za-z]+)",
            r"(?:is|as)\s+a\s+(?:member|species)\s+of\s+(?:the)?\s+family\s+([A-Za-z]+)",
            r"(?:is|as)\s+a\s+(?:member|species)\s+of\s+(?:the)?\s+genus\s+([A-Za-z]+)"
        ]
        
        # Map patterns to taxonomic ranks
        rank_map = {
            0: "kingdom", 1: "phylum", 2: "class", 3: "order", 4: "family",
            5: "kingdom", 6: "phylum", 7: "class", 8: "order", 9: "family", 10: "genus"
        }
        
        # Apply statement patterns to extract taxonomic information
        for i, pattern in enumerate(taxonomy_statement_patterns):
            rank = rank_map.get(i)
            if not rank:
                continue
                
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            if matches and classification[rank] == "Unknown":
                classification[rank] = matches[0].strip()
        
        # Final cleanup: ensure proper capitalization and formatting
        for rank, value in classification.items():
            if value != "Unknown":
                # Capitalize first letter for taxonomic ranks
                classification[rank] = value[0].upper() + value[1:]
    
    except Exception as e:
        print(f"Error extracting classification from Wikipedia: {str(e)}")
        # If an error occurs, we'll return the classification with whatever data we managed to extract
    
    return classification

def extract_taxonomy_from_text(text, classification):
    """
    Extract taxonomic information from text using pattern matching
    and natural language processing techniques.
    
    Args:
        text: The text to analyze
        classification: The current classification dictionary to update
        
    Returns:
        Updated classification dictionary
    """
    if not text:
        return classification
    
    try:
        # Common patterns for taxonomic ranks in text
        taxonomy_patterns = {
            "kingdom": [r"Kingdom:?\s*([A-Za-z]+)", r"Kingdom\s+([A-Za-z]+)", r"a member of the kingdom\s+([A-Za-z]+)"],
            "phylum": [r"Phylum:?\s*([A-Za-z]+)", r"Phylum\s+([A-Za-z]+)", r"a member of the phylum\s+([A-Za-z]+)"],
            "class": [r"Class:?\s*([A-Za-z]+)", r"Class\s+([A-Za-z]+)", r"a member of the class\s+([A-Za-z]+)"],
            "order": [r"Order:?\s*([A-Za-z]+)", r"Order\s+([A-Za-z]+)", r"a member of the order\s+([A-Za-z]+)"],
        }
        
        # For each taxonomic rank, try to find matches using the patterns
        for rank, patterns in taxonomy_patterns.items():
            if classification[rank] != "Unknown":
                continue  # Skip if we already have a value
                
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # Take the first match and clean it up
                    match = matches[0].strip()
                    # Handle Latin taxonomic names with proper capitalization
                    if rank in ["genus", "species"]:
                        match = match[0].upper() + match[1:].lower()
                    elif rank != "species":  # For non-species ranks
                        match = match.capitalize()
                    
                    classification[rank] = match
                    break  # Stop after finding a match for this rank
        
        # Look for taxonomic information with specific taxonomic suffixes
        suffix_patterns = {
            "family": [r"\b([A-Za-z]+idae)\b", r"\b([A-Za-z]+aceae)\b"],  # Animal and plant families
            "order": [r"\b([A-Za-z]+ales)\b", r"\b([A-Za-z]+ida)\b"],  # Plant orders and animal orders
            "class": [r"\b([A-Za-z]+ia)\b", r"\b([A-Za-z]+phyceae)\b"],  # Classes
            "phylum": [r"\b([A-Za-z]+phyta)\b", r"\b([A-Za-z]+zoa)\b"]  # Plant and animal phyla
        }
        
        # Apply suffix patterns to extract taxonomic information
        for rank, patterns in suffix_patterns.items():
            if classification[rank] != "Unknown":
                continue  # Skip if we already have a value
                
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    # Take the first match and clean it up
                    match = matches[0].strip()
                    classification[rank] = match
                    break
                
    except Exception as e:
        print(f"Error in extract_taxonomy_from_text: {str(e)}")
        # If an error occurs, return the classification as is
    
    return classification

if __name__ == "__main__":
    main()
