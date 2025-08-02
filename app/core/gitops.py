import os
import shutil
from git import Repo
from datetime import datetime

CONFIGS_DIR = os.path.join(os.path.dirname(__file__), '../../configs')
REPO_DIR = os.path.abspath(os.path.join(CONFIGS_DIR, '..'))

if not os.path.exists(CONFIGS_DIR):
    os.makedirs(CONFIGS_DIR)

if not os.path.exists(os.path.join(REPO_DIR, '.git')):
    Repo.init(REPO_DIR)


def commit_config(vendor: str, config: str, description: str = "", product: str = None):
    safe_product = (product or "generic").replace(" ", "_").lower()
    filename = f"{vendor}_{safe_product}_config_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
    filepath = os.path.join(CONFIGS_DIR, filename)
    with open(filepath, 'w') as f:
        f.write(config)
    repo = Repo(REPO_DIR)
    repo.git.add(filepath)
    commit_msg = f"[{vendor.upper()} {product}] {description or 'Config update'}"
    repo.index.commit(commit_msg)
    # Post-commit: if Cisco ASR 9000, update 'latest' symlink or copy
    if vendor.lower() == 'cisco' and product and 'asr' in product.lower():
        latest_path = os.path.join(CONFIGS_DIR, 'cisco_asr_9000_config_latest.txt')
        shutil.copyfile(filepath, latest_path)
    return filename

def rollback_config(vendor: str, product: str = None):
    safe_product = (product or "generic").replace(" ", "_").lower()
    repo = Repo(REPO_DIR)
    commits = list(repo.iter_commits('master'))
    for commit in commits[1:]:  # skip latest
        for item in commit.stats.files:
            if vendor in item and (not product or safe_product in item.lower()):
                repo.git.checkout(commit.hexsha, '--', item)
                with open(os.path.join(CONFIGS_DIR, os.path.basename(item)), 'r') as f:
                    return f.read()
    raise Exception("No previous config found for rollback.")
