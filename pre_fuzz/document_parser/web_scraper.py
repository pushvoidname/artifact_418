import os
import requests
from bs4 import BeautifulSoup
from lxml import html
from urllib.parse import urljoin
import hashlib
import argparse


# Global variable to store the base URL
BASE_URL = None
MODE = None

OUTPUT_DIR = 'output'


def fetch_page(url):
    response = requests.get(url)
    response.raise_for_status()
    content = response.text

    # Create the 'result' directory if it does not exist
    if not os.path.exists("result"):
        os.makedirs("result")

    # Generate a unique filename for the URL using an MD5 hash
    filename = os.path.join("result", hashlib.md5(url.encode('utf-8')).hexdigest() + ".html")

    # Save the fetched content to the file
    with open(filename, "w", encoding="utf-8") as file:
        file.write(content)

    return content


def parse_main_page(html_content):
    """Parse the main page and extract JavaScript API hierarchy."""
    tree = html.fromstring(html_content)
    global MODE
    if MODE == 'A':
        js_api_section = tree.xpath('/html/body/div/nav/div/div[3]/ul/li[3]') # For Other API
    elif MODE == 'D':
        js_api_section = tree.xpath('/html/body/div/nav/div/div[3]/ul/li[4]') # For Doc API
    else:
        # This branch should not be reached due to argparse choices.
        raise ValueError("Invalid mode parameter provided.")
    
    if not js_api_section:
        print("JavaScript API section not found!")
        return []
    
    js_api_section = js_api_section[0]
    print(f"Found JavaScript API section: {js_api_section.text_content().strip()}")
    
    hierarchy = []
    current_object = None
    current_section = None
    
    # First pass: build a map of which sections have children
    sections_with_children = set()
    for item in js_api_section.findall('.//li'):
        parent_li = item.getparent().getparent()  # ul -> li
        if parent_li is not None:
            parent_link = parent_li.find('.//a[@class="reference internal"]')
            if parent_link is not None:
                sections_with_children.add(parent_link.get('href', ''))
    
    # Second pass: process all items
    for item in js_api_section.findall('.//li'):
        classes = item.get('class', '').split()
        level_class = next((c for c in classes if c.startswith('toctree-l')), None)
        if not level_class:
            continue
            
        level = int(level_class[-1])
        link = item.find('.//a[@class="reference internal"]')
        if link is None:
            continue
            
        title = link.text_content().strip()
        href = link.get('href', '')
        
        if level == 2:  # Main object
            current_object = title
            current_section = None
        elif level == 3:
            if title.lower().endswith('methods') or title.lower().endswith('properties'):
                current_section = title
            else:
                current_section = None
                
        hierarchy.append({
            'depth': level,
            'title': title,
            'link': href,
            'object': current_object,
            'section': current_section,
            'has_children': href in sections_with_children
        })
    
    return hierarchy

def clean_text(text):
    """Clean and normalize text."""
    return ' '.join(text.split())

def process_table(table):
    """Process any table, including version info tables."""
    rows = []
    
    # Process headers
    headers = []
    for th in table.find_all('th'):
        header_text = th.get_text().strip()
        # For version tables, remove (Key) but keep the header
        if '(Key)' in header_text:
            header_text = header_text.replace('(Key)', '').strip()
        headers.append(header_text)
    
    if headers:
        rows.append(' | '.join(headers))
        rows.append('-' * len(rows[0]))
    
    # Process rows
    for tr in table.find_all('tr'):
        cells = []
        # Only process td elements to avoid duplicate headers
        for td in tr.find_all('td'):
            cell_text = td.get_text().strip()
            cells.append(cell_text)
        
        if cells:  # Only add non-empty rows
            rows.append(' | '.join(cells))
    
    return '\n'.join(rows) if rows else ""

def process_section_content(section):
    """Process all content in a section."""
    content = []
    current_line = []
    
    def flush_line():
        if current_line:
            line = ' '.join(current_line)
            if line:
                content.append(line)
            current_line.clear()
    
    # Get the title (without ¶)
    title = section.find('h2')
    if title:
        content.append(title.get_text().replace('¶', '').strip())
    
    # Get version table if exists
    version_table = section.find('div', class_='table-wrapper')
    if version_table and version_table.find('table'):
        table_text = process_table(version_table.find('table'))
        if table_text:
            content.append(table_text)
    
    # Process remaining content
    for element in section.children:
        if isinstance(element, str):
            text = element.strip()
            if text and text != '¶':
                current_line.append(text)
        
        elif element.name == 'pre' and element.get('id', '').startswith('codecell'):
            flush_line()
            code_text = element.get_text().strip()
            if code_text:
                content.append(f"```\n{code_text}\n```")
                
        elif element.name == 'div' and 'highlight-default' in element.get('class', []):
            flush_line()
            pre = element.find('pre')
            if pre:
                code_text = pre.get_text().strip()
                if code_text:
                    content.append(f"```\n{code_text}\n```")
                
        elif element.name == 'table':
            flush_line()
            table_text = process_table(element)
            if table_text:
                content.append(table_text)
                
        elif element.name == 'code':
            code_text = element.get_text().strip()
            if code_text:
                current_line.append(f'`{code_text}`')
                
        elif element.name == 'p':
            flush_line()
            for child in element.children:
                if isinstance(child, str):
                    text = child.strip()
                    if text and text != '¶':
                        current_line.append(text)
                elif child.name == 'code':
                    code_text = child.get_text().strip()
                    if code_text:
                        current_line.append(f'`{code_text}`')
                elif child.name == 'strong':
                    text = child.get_text().strip()
                    if text:
                        current_line.append(f'**{text}**')
                # If child is <a> (anchor link), convert to Markdown link
                elif child.name == 'a':
                    link_text = child.get_text(strip=True)
                    if link_text:
                        # href = child.get('href', '').strip()
                        # current_line.append(f'[{link_text}]({href})')
                        current_line.append(f'{link_text}')
            flush_line()
        
        #process ul elements
        elif element.name == 'ul':
            flush_line()
            # each child should be an li element
            for li in element.children:
                line = ['* ']
                if li.name != 'li':
                    continue
                p = li.find('p')
                if p:
                    # Iterate through all the child elements of <p>
                    for child in p.children:
                        if child.name == 'code':  # For <code>, get its text
                            line.append(f'`{child.get_text(strip=True)}`')
                        elif child.name is None:  # For plain text, add it directly
                            line.append(child.strip())
                        else:  # For other tags, add their text
                            line.append(child.get_text(strip=True))
                # Combine the extracted parts into a single line
                content.append(' '.join(line))

        # process elements of class admonition note
        elif element.name == 'div' and 'admonition' in element.get('class', []):
            flush_line()
            # add a special character to indicate a note
            line = ['!!']
            # get its children, each of them is a <p> element
            p_elements = element.find_all('p')
            for p in p_elements:
                for child in p.children:
                    if child.name == 'code':
                        line.append(f'`{child.get_text(strip=True)}`')
                    elif child.name is None:
                        line.append(child.strip())
                    else:
                        line.append(child.get_text(strip=True))
            content.append(' '.join(line))

            
        elif element.name in ['h3', 'h4']:
            flush_line()
            text = element.get_text().strip()
            if text and text != '¶':
                content.append(f"\n{text}")
    
    flush_line()
    return '\n\n'.join(line for line in content if line)


def extract_content_between_sections(soup, current_link, item):
    """Extract content from the specific section ID."""
    if not current_link.startswith('#'):
        return ""
    
    current_id = current_link[1:]
    section = soup.find(id=current_id)
    if not section:
        print(f"Warning: Section {current_id} not found")
        return ""
    
    content = process_section_content(section)
    
    print(f"Extracted content for {item['title']}:")
    print("---START---")
    print(content)
    print("---END---")
    return content

def process_hierarchy(hierarchy, main_page_html):
    """Process the hierarchy and save content."""
    soup = BeautifulSoup(main_page_html, 'html.parser')
    
    for item in hierarchy:
        depth = item['depth']
        title = item['title']
        link = item['link']
        object_name = item['object']
        section = item['section']
        has_children = item['has_children']
        
        if not object_name:
            continue
            
        content = extract_content_between_sections(soup, link, item)
        
        if depth == 2:  # Object
            path = os.path.join(OUTPUT_DIR, object_name, "object.txt")
        elif depth == 3:
            if (title.lower().endswith('methods') or title.lower().endswith('properties')) and not has_children:
                # Only save section content if it has no children
                folder_name = 'methods' if title.lower().endswith('methods') else 'properties'
                path = os.path.join(OUTPUT_DIR, object_name, folder_name, f"{title}.txt")
            elif not (title.lower().endswith('methods') or title.lower().endswith('properties')):
                # Other object-level content
                path = os.path.join(OUTPUT_DIR, object_name, f"{title}.txt")
            else:
                continue
        elif depth == 4:  # Method or property
            if section and section.lower().endswith('methods'):
                path = os.path.join(OUTPUT_DIR, object_name, "methods", f"{title}.txt")
            elif section and section.lower().endswith('properties'):
                path = os.path.join(OUTPUT_DIR, object_name, "properties", f"{title}.txt")
            else:
                continue
        else:
            continue
            
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        # print(f"Saved: {path}")


def parse_arguments():
    """
    Parse command-line arguments.
    -m: Mode selection ('A' for Other API, 'D' for Doc API)
    """
    parser = argparse.ArgumentParser(description="Set BASE_URL based on mode parameter.")
    parser.add_argument(
        '-m', 
        required=True, 
        choices=['A', 'D'], 
        help="Mode selection: 'A' for Other API, 'D' for Doc API"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    
    global MODE
    global BASE_URL

    MODE = args.m
    if MODE == 'A':
        BASE_URL = 'https://opensource.adobe.com/dc-acrobat-sdk-docs/library/jsapiref/JS_API_AcroJS.html'
    elif MODE == 'D':
        BASE_URL = 'https://opensource.adobe.com/dc-acrobat-sdk-docs/library/jsapiref/doc.html'
    else:
        # This branch should not be reached due to argparse choices.
        raise ValueError("Invalid mode parameter provided.")
    print("Fetching main page...")
    main_page_html = fetch_page(BASE_URL)
    
    print("\nParsing hierarchy...")
    hierarchy = parse_main_page(main_page_html)
    
    if not hierarchy:
        print("No items found to process!")
        return
    
    print(f"\nFound {len(hierarchy)} items to process")
    
    print("\nProcessing content...")
    process_hierarchy(hierarchy, main_page_html)
    
    print("\nDone!")

if __name__ == '__main__':
    main()