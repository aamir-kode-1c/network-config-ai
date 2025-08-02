import os
from git import Repo
from datetime import datetime

CONFIGS_DIR = os.path.join(os.path.dirname(__file__), '../../configs')
REPO_DIR = os.path.abspath(os.path.join(CONFIGS_DIR, '..'))

def extract_product_from_filename(filename):
    # Example: nokia_7750_sr_config_20250801110611.txt
    parts = filename.split('_')
    if len(parts) >= 3:
        # Join all parts between vendor and 'config'
        product_parts = []
        for p in parts[1:-2]:
            product_parts.append(p)
        return ' '.join(product_parts).replace('-', ' ').title()
    return ""

def get_config_history(vendor: str, product: str = None):
    repo = Repo(REPO_DIR)
    history = []
    safe_product = (product or "").replace(" ", "_").lower()
    for commit in repo.iter_commits('master'):
        for item in commit.stats.files:
            if vendor in item and (not product or safe_product in item.lower()):
                filepath = os.path.join(CONFIGS_DIR, item)
                history.append({
                    'commit': commit.hexsha,
                    'timestamp': datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S'),
                    'message': commit.message,
                    'file': item,
                    'filepath': filepath,
                    'product': extract_product_from_filename(item)
                })
    return history

def get_config_content(filepath: str, commit: str = None):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return f.read()
    # Try to get from git if not present on disk
    if commit:
        from git import Repo
        repo = Repo(REPO_DIR)
        # Always use path relative to repo root (should be configs/filename)
        repo_root = repo.git.rev_parse('--show-toplevel')
        rel_path = os.path.relpath(filepath, repo_root)
        try:
            blob = repo.git.show(f"{commit}:{rel_path.replace(os.sep, '/')}" )
            return blob
        except Exception:
            return None
    return None
