from pathlib import Path

def load_css(file_path: str) -> str:
    """Load CSS file and return as HTML style tag string."""
    css_path = Path(__file__).parent / file_path
    with open(css_path, 'r', encoding='utf-8') as f:
        css_content = f.read()
    return f'<style>{css_content}</style>'

def import_web_fonts() -> str:
    return '''
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Ubuntu:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400;1,500;1,700&display=swap" rel="stylesheet">    
    '''